"""Recompute every number in the benchmark summary from the raw samples and check CSV and README against them.

    python bench/check_results.py          # no database needed; exits non-zero on any mismatch
"""
import csv
import json
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
raw = json.loads((HERE / "results/patient_id_matching_raw.json").read_text())
csv_rows = list(csv.DictReader(open(HERE / "results/patient_id_matching_summary.csv")))
readme = (HERE / "README.md").read_text()
errors = []


def nearest_rank(sorted_samples, q):
    return sorted_samples[min(len(sorted_samples) - 1, int(round(q * (len(sorted_samples) - 1))))]


def summarise(samples):
    s = sorted(samples)
    return {"p50": nearest_rank(s, 0.5), "p95": nearest_rank(s, 0.95), "mean": statistics.fmean(s), "n": len(s)}


def table_markdown():
    """The results table exactly as it appears in the README (generated from the raw samples)."""
    ms = lambda v: f"{v:,.3f}" if v < 10 else f"{v:,.1f}"
    lines = ["| Patients | Scenario | Original P50 / P95 / mean (ms) | Optimized P50 / P95 / mean (ms) | Speedup (P50) | Latency reduction (P50) |",
             "|---|---|---|---|---|---|"]
    for (n, scen), r in recomputed.items():
        o, p = r["orig"], r["opt"]
        lines.append(f"| {n:,} | {scen} | {ms(o['p50'])} / {ms(o['p95'])} / {ms(o['mean'])} | "
                     f"{ms(p['p50'])} / {ms(p['p95'])} / {ms(p['mean'])} | {r['speedup_p50']:,.1f}x | {r['reduction_p50']:.2f}% |")
    return "\n".join(lines)


def close(a, b, tol):
    return abs(a - b) <= tol


recomputed = {}
for scale in raw["scales"]:
    for name, sc in scale["scenarios"].items():
        o, p = summarise(sc["raw_ms"]["original"]), summarise(sc["raw_ms"]["optimized"])
        if o["n"] < 100 or p["n"] < 100:
            errors.append(f"{scale['patients']}/{name}: fewer than 100 measured samples")
        recomputed[(scale["patients"], name)] = {
            "orig": o, "opt": p, "speedup_p50": o["p50"] / p["p50"], "speedup_mean": o["mean"] / p["mean"],
            "reduction_p50": 100 * (1 - p["p50"] / o["p50"]), "reduction_mean": 100 * (1 - p["mean"] / o["mean"]),
        }
        # the stats stored in the raw file must match too
        for impl, r in (("original", o), ("optimized", p)):
            st = sc["stats_ms"][impl]
            for k in ("p50", "p95", "mean"):
                if not close(st[k], r[k], 1e-9):
                    errors.append(f"{scale['patients']}/{name}/{impl}/{k}: stored {st[k]} vs recomputed {r[k]}")

for row in csv_rows:  # CSV is rounded to 4 decimals
    r = recomputed[(int(row["patients"]), row["scenario"])]
    pairs = {"orig_p50_ms": r["orig"]["p50"], "orig_p95_ms": r["orig"]["p95"], "orig_mean_ms": r["orig"]["mean"],
             "opt_p50_ms": r["opt"]["p50"], "opt_p95_ms": r["opt"]["p95"], "opt_mean_ms": r["opt"]["mean"],
             "speedup_p50": r["speedup_p50"], "speedup_mean": r["speedup_mean"],
             "reduction_pct_p50": r["reduction_p50"], "reduction_pct_mean": r["reduction_mean"]}
    for k, v in pairs.items():
        if not close(float(row[k]), v, 6e-5 + 1e-9 * abs(v)):
            errors.append(f"CSV {row['patients']}/{row['scenario']}/{k}: {row[k]} vs recomputed {v}")

# README table rows: | 100,000 | valid_id | a / b / c | d / e / f | 3,588.0x | 99.97% |
# Each displayed number must equal the recomputed value rounded to the precision shown.
checked = 0
LABELS = ("orig p50", "orig p95", "orig mean", "opt p50", "opt p95", "opt mean", "speedup", "reduction")
for m in re.finditer(r"^\| ([\d,]+) \| (\w+) \| ([\d.,]+) / ([\d.,]+) / ([\d.,]+) \| ([\d.,]+) / ([\d.,]+) / ([\d.,]+) \| ([\d.,]+)x \| ([\d.]+)% \|$",
                     readme, re.M):
    n, scen = int(m.group(1).replace(",", "")), m.group(2)
    r = recomputed[(n, scen)]
    expect = [r["orig"]["p50"], r["orig"]["p95"], r["orig"]["mean"], r["opt"]["p50"], r["opt"]["p95"], r["opt"]["mean"],
              r["speedup_p50"], r["reduction_p50"]]
    for label, shown, want in zip(LABELS, m.groups()[2:], expect):
        decimals = len(shown.split(".")[1]) if "." in shown else 0
        if abs(float(shown.replace(",", "")) - want) > 0.5 * 10 ** -decimals + 1e-9:
            errors.append(f"README {n}/{scen}/{label}: shown {shown} vs recomputed {want:.5f}")
    checked += 1
if checked != len(csv_rows):
    errors.append(f"README table has {checked} rows, expected {len(csv_rows)}")

if "--print-table" in sys.argv:
    print(table_markdown())
    sys.exit(0)
if errors:
    print("MISMATCHES:\n" + "\n".join(errors))
    sys.exit(1)
print(f"OK: {len(recomputed)} scenarios recomputed from raw samples; CSV and {checked} README rows match")
