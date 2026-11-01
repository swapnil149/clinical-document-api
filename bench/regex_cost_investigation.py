"""Why was the original patient-ID matching slow? (companion to patient_id_bench.py, see bench/README.md)

Part 1 (no database): time `re.search` over N distinct patterns, repeated, with and without precompiled patterns.
        Shows Python's regex cache cliff at re._MAXCACHE (512) distinct patterns.
Part 2 (local PostgreSQL): split the original implementation's per-request time into
        (a) fetching DISTINCT patient IDs from PostgreSQL,
        (b) the Python regex loop exactly as the original wrote it (patterns built and compiled per call),
        (c) the same loop with patterns compiled once up front (what a cache would give you).

Uses the same safety guard and synthetic data loader as patient_id_bench.py: BENCH_DATABASE_URL must be a LOCAL
PostgreSQL database whose name ends in "_bench". Nothing else is touched; the temporary table is dropped at the end.

    BENCH_DATABASE_URL=postgresql://USER@127.0.0.1:PORT/clinical_bench python bench/regex_cost_investigation.py
"""
import argparse
import json
import os
import platform
import re
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import patient_id_bench as bench  # noqa: E402  (also puts the repo root on sys.path and sets dummy API keys)

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.models import Document  # noqa: E402


def timed_ms(fn, repeats, warmup=2):
    samples = []
    for i in range(warmup + repeats):
        t = time.perf_counter()
        fn()
        dt = (time.perf_counter() - t) * 1000
        if i >= warmup:
            samples.append(dt)
    return statistics.median(samples)


def pattern(patient_id):
    return rf"(?<![\w-]){re.escape(patient_id)}(?![\w-])"  # same pattern as the original implementation


def cache_cliff(sizes, repeats):
    question = "What medications is patient P-A999999 taking?"
    rows = []
    for n in sizes:
        ids = [bench.pid(i) for i in range(n)]
        pats = [pattern(p) for p in ids]
        compiled = [re.compile(p, re.IGNORECASE) for p in pats]
        re.purge()
        by_string = timed_ms(lambda: [re.search(p, question, re.IGNORECASE) for p in pats], repeats)
        precompiled = timed_ms(lambda: [c.search(question) for c in compiled], repeats)
        rows.append({"distinct_patterns": n, "re_search_with_pattern_string_ms": by_string,
                     "precompiled_ms": precompiled, "per_pattern_us_by_string": 1000 * by_string / n,
                     "per_pattern_us_precompiled": 1000 * precompiled / n})
        print(f"  {n:>6} patterns: by string {by_string:9.2f} ms ({1000 * by_string / n:7.2f} us/pattern) | "
              f"precompiled {precompiled:8.2f} ms ({1000 * precompiled / n:5.2f} us/pattern)", flush=True)
    return rows


def decompose(engine, scales, repeats):
    out = []
    for n in scales:
        bench.load(engine, n)
        db = sessionmaker(bind=engine)()
        question = bench.build_questions(n)["unknown_id"]  # unknown ID: every pattern must be tried
        fetch_ms = []
        for _ in range(repeats + 2):
            t = time.perf_counter()
            ids = [row[0] for row in db.query(Document.patient_id).distinct()]
            fetch_ms.append((time.perf_counter() - t) * 1000)
            db.rollback()
        fetch = statistics.median(fetch_ms[2:])
        loop = timed_ms(lambda: [p for p in ids if re.search(pattern(p), question, re.IGNORECASE)], repeats)
        compiled = [re.compile(pattern(p), re.IGNORECASE) for p in ids]
        precompiled = timed_ms(lambda: [p for p, c in zip(ids, compiled) if c.search(question)], repeats)
        out.append({"patients": n, "distinct_ids_fetched": len(ids), "sql_fetch_ms": fetch,
                    "regex_loop_original_ms": loop, "regex_loop_precompiled_ms": precompiled})
        print(f"  {n:>6} patients: SQL fetch {fetch:8.1f} ms | regex loop (original) {loop:9.1f} ms | "
              f"same loop, precompiled {precompiled:8.1f} ms", flush=True)
        db.close()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scales", default="1000,10000,100000", help="distinct patient IDs for the database part")
    ap.add_argument("--sizes", default="100,256,400,500,512,520,600,1000,5000,20000", help="pattern counts for part 1")
    ap.add_argument("--repeats", type=int, default=5, help="measured repeats per point (median reported)")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "results"))
    args = ap.parse_args()

    url = os.environ.get("BENCH_DATABASE_URL", "")
    if not re.match(r"^postgresql(\+psycopg2)?://[^@/]*@(127\.0\.0\.1|localhost)(:\d+)?/\w+_bench$", url):
        sys.exit("refusing to run: BENCH_DATABASE_URL must be a local PostgreSQL database whose name ends in _bench")
    engine = create_engine(url.replace("postgresql://", "postgresql+psycopg2://", 1))

    print(f"Python {platform.python_version()}, re._MAXCACHE = {re._MAXCACHE}")
    print("Part 1: regex cache (no database)")
    cliff = cache_cliff([int(x) for x in args.sizes.split(",")], args.repeats)
    print("Part 2: where the original implementation's time goes (local PostgreSQL)")
    try:
        parts = decompose(engine, [int(x) for x in args.scales.split(",")], args.repeats)
    finally:
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS documents CASCADE"))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "regex_cost_investigation.json").write_text(json.dumps(
        {"python": platform.python_version(), "re_MAXCACHE": re._MAXCACHE, "repeats": args.repeats,
         "statistic": "median over repeats", "regex_cache": cliff, "original_time_breakdown": parts}, indent=1))
    print("done; results in", out)


if __name__ == "__main__":
    main()
