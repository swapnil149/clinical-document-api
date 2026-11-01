"""Local benchmark: patient-ID matching, original vs optimized (see bench/README.md).

Original  = app/rag.py at commit f3859d5: load every distinct patient_id, regex-test each against the question.
Optimized = app.rag.find_mentioned_patient_ids: extract ID-shaped candidates from the question, look up only those
            through the expression index on upper(patient_id).

Runs only against a LOCAL PostgreSQL database whose name ends in "_bench" (refuses anything else). No network, AWS,
Voyage or Claude calls. Temporary synthetic tables are dropped at the end unless --keep is given.

    createdb -h 127.0.0.1 -p PORT -U USER clinical_bench   # once, on a local throwaway PostgreSQL
    BENCH_DATABASE_URL=postgresql://USER@127.0.0.1:PORT/clinical_bench \
        .venv312/bin/python bench/patient_id_bench.py
"""
import argparse
import csv
import gc
import json
import os
import platform
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("VOYAGE_API_KEY", "bench-not-used")
os.environ.setdefault("ANTHROPIC_API_KEY", "bench-not-used")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app import models, rag  # noqa: E402
from app.models import Document  # noqa: E402

OUT = Path(__file__).resolve().parent / "results"
DOCS_PER_PATIENT = 3  # several notes per patient, so DISTINCT has real work to do


def original_find_mentioned_patient_ids(db, query: str):
    """Verbatim from app/rag.py at commit f3859d5 (before the optimization)."""
    patient_ids = [row[0] for row in db.query(Document.patient_id).distinct()]
    return [
        patient_id for patient_id in patient_ids
        if re.search(rf"(?<![\w-]){re.escape(patient_id)}(?![\w-])", query, re.IGNORECASE)
    ]


IMPLS = {"original": original_find_mentioned_patient_ids, "optimized": rag.find_mentioned_patient_ids}


def pid(i):
    return f"P-A{i:06d}"


def build_questions(n):
    mid, last = n // 2, n - 1
    return {
        "valid_id": f"What medications is patient {pid(mid)} taking?",
        "unknown_id": f"What medications is patient {pid(n + 500)} taking?",  # well-formed, not in the table
        "no_id": "What is the recommended HbA1c target for adults with type 2 diabetes?",
        # extra, not required: two valid IDs, lower-case
        "two_valid_ids": f"Compare {pid(1)} with {pid(last).lower()} regarding follow-up.",
    }


def load(engine, n):
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS documents CASCADE"))
    models.Document.__table__.create(engine)  # includes ix_documents_patient_id_upper
    rows = [{"patient_id": pid(i), "document_type": "progress_note", "content": f"SYNTHETIC benchmark note {j} for {pid(i)}."}
            for i in range(n) for j in range(DOCS_PER_PATIENT)]
    # a few IDs in formats the optimized version does not extract (documented behavioural difference)
    rows += [{"patient_id": x, "document_type": "progress_note", "content": "SYNTHETIC"} for x in ("MRN12345", "10042")]
    with engine.begin() as conn:
        for i in range(0, len(rows), 10000):
            conn.execute(Document.__table__.insert(), rows[i:i + 10000])
    with engine.begin() as conn:
        conn.execute(text("ANALYZE documents"))
    return len(rows)


def check_equivalence(db, n):
    qs = list(build_questions(n).values()) + [
        f"patient {pid(5).lower()} and {pid(7).upper()}", f"({pid(3)}), then {pid(4)}.", f"{pid(9)}'s labs",
        f"P-A{n - 1:06d}", "P-A00000", f"P-A{1:07d}", f"XP-A{1:06d}", f"{pid(2)}-2", f"{pid(2)}x", "P-1O1",
        "", "no identifier here", "HbA1c 7.2 and COVID-19",
    ]
    mism = []
    for q in qs:
        a, b = sorted(original_find_mentioned_patient_ids(db, q)), sorted(rag.find_mentioned_patient_ids(db, q))
        if a != b:
            mism.append({"question": q, "original": a, "optimized": b})
        db.rollback()
    # known divergence: IDs outside the supported formats
    unsupported = {q: {"original": sorted(original_find_mentioned_patient_ids(db, q)),
                       "optimized": sorted(rag.find_mentioned_patient_ids(db, q))}
                   for q in ("notes for MRN12345", "notes for 10042")}
    db.rollback()
    return {"questions_checked": len(qs), "mismatches": mism, "unsupported_format_divergence": unsupported}


def stats(ms):
    s = sorted(ms)
    p = lambda q: s[min(len(s) - 1, int(round(q * (len(s) - 1))))]  # nearest-rank on sorted samples
    return {"n": len(s), "mean": statistics.fmean(s), "p50": p(0.50), "p95": p(0.95), "min": s[0], "max": s[-1]}


def explain(db, n):
    plans = {}
    for name, sql in (
        ("original: SELECT DISTINCT patient_id", "SELECT DISTINCT patient_id FROM documents"),
        ("optimized: valid id", f"SELECT DISTINCT patient_id FROM documents WHERE upper(patient_id) IN ('{pid(n // 2)}')"),
        ("optimized: unknown id", f"SELECT DISTINCT patient_id FROM documents WHERE upper(patient_id) IN ('{pid(n + 500)}')"),
    ):
        plans[name] = [r[0] for r in db.execute(text("EXPLAIN (ANALYZE, BUFFERS) " + sql))]
        db.rollback()
    return plans


def run_scale(engine, n, warmup, iters):
    t0 = time.perf_counter()
    rows = load(engine, n)
    load_s = time.perf_counter() - t0
    Session = sessionmaker(bind=engine)
    db = Session()
    questions = build_questions(n)
    result = {"patients": n, "rows": rows, "load_seconds": round(load_s, 1), "equivalence": check_equivalence(db, n),
              "explain": explain(db, n), "scenarios": {}}
    for scen, q in questions.items():
        samples = {k: [] for k in IMPLS}
        expected = None
        for it in range(warmup + iters):
            # alternate which implementation goes first so neither systematically benefits from cache state
            order = list(IMPLS) if it % 2 == 0 else list(reversed(IMPLS))
            for name in order:
                gc.collect()
                t = time.perf_counter()
                out = IMPLS[name](db, q)
                dt = (time.perf_counter() - t) * 1000
                db.rollback()  # end the transaction outside the timed region; same for both
                if it >= warmup:
                    samples[name].append(dt)
                if expected is None:
                    expected = sorted(out)
                elif sorted(out) != expected:
                    raise AssertionError(f"implementations disagree on {scen}: {out} vs {expected}")
        s = {k: stats(v) for k, v in samples.items()}
        o, p = s["original"], s["optimized"]
        result["scenarios"][scen] = {
            "matched_ids": expected, "stats_ms": s, "raw_ms": samples,
            "speedup_p50": o["p50"] / p["p50"], "speedup_mean": o["mean"] / p["mean"],
            "reduction_pct_p50": 100 * (1 - p["p50"] / o["p50"]), "reduction_pct_mean": 100 * (1 - p["mean"] / o["mean"]),
        }
        print(f"  n={n:>6} {scen:<14} original p50={o['p50']:9.3f} ms  optimized p50={p['p50']:7.3f} ms  "
              f"speedup x{o['p50'] / p['p50']:.1f}", flush=True)
    db.close()
    return result


def environment(engine):
    def sh(*a):
        try:
            return subprocess.check_output(a, text=True).strip()
        except Exception:
            return "unknown"
    with engine.connect() as c:
        pg = c.execute(text("select version()")).scalar()
        settings = {k: c.execute(text("select current_setting(:k)"), {"k": k}).scalar()
                    for k in ("shared_buffers", "work_mem", "max_parallel_workers_per_gather", "jit")}
    import sqlalchemy
    return {"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"), "platform": platform.platform(),
            "cpu": sh("sysctl", "-n", "machdep.cpu.brand_string"), "cores": os.cpu_count(),
            "memory_gb": round(int(sh("sysctl", "-n", "hw.memsize") or 0) / 2**30, 1) if sh("sysctl", "-n", "hw.memsize").isdigit() else "unknown",
            "python": platform.python_version(), "sqlalchemy": sqlalchemy.__version__, "postgres": pg, "pg_settings": settings,
            "connection": "127.0.0.1 TCP, one SQLAlchemy Session reused for all iterations (same for both implementations)"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scales", default="100,1000,10000,100000")
    ap.add_argument("--warmup", type=int, default=10)
    ap.add_argument("--iters", type=int, default=100)
    ap.add_argument("--keep", action="store_true", help="keep the temporary table after the run")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    url = os.environ.get("BENCH_DATABASE_URL", "")
    if not re.match(r"^postgresql(\+psycopg2)?://[^@/]*@(127\.0\.0\.1|localhost)(:\d+)?/\w+_bench$", url):
        sys.exit("refusing to run: BENCH_DATABASE_URL must be a local PostgreSQL database whose name ends in _bench")
    engine = create_engine(url.replace("postgresql://", "postgresql+psycopg2://", 1))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    env = environment(engine)
    print(json.dumps({k: env[k] for k in ("cpu", "postgres")}), flush=True)
    results = {"environment": env, "config": {"warmup": args.warmup, "iterations": args.iters, "docs_per_patient": DOCS_PER_PATIENT},
               "scales": []}
    try:
        for n in [int(x) for x in args.scales.split(",")]:
            print(f"scale {n}: loading synthetic data...", flush=True)
            results["scales"].append(run_scale(engine, n, args.warmup, args.iters))
            (out / "patient_id_matching_raw.json").write_text(json.dumps(results, indent=1))
    finally:
        if not args.keep:
            with engine.begin() as conn:
                conn.execute(text("DROP TABLE IF EXISTS documents CASCADE"))

    rows = []
    for sc in results["scales"]:
        for scen, d in sc["scenarios"].items():
            o, p = d["stats_ms"]["original"], d["stats_ms"]["optimized"]
            rows.append({"patients": sc["patients"], "rows": sc["rows"], "scenario": scen,
                         "orig_p50_ms": o["p50"], "orig_p95_ms": o["p95"], "orig_mean_ms": o["mean"],
                         "opt_p50_ms": p["p50"], "opt_p95_ms": p["p95"], "opt_mean_ms": p["mean"],
                         "speedup_p50": d["speedup_p50"], "speedup_mean": d["speedup_mean"],
                         "reduction_pct_p50": d["reduction_pct_p50"], "reduction_pct_mean": d["reduction_pct_mean"]})
    with open(out / "patient_id_matching_summary.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()} for r in rows)
    print("done; results in", out, flush=True)


if __name__ == "__main__":
    main()
