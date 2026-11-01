"""Build eval/results/summary.csv and print a Markdown comparison table from the saved run JSON files."""
import csv
import json
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "results"
RUNS = [  # (file stem, label)
    ("baseline-v1", "v1 baseline (k=3)"), ("idmatch_k5-v1", "v1 final (ID match + k=5)"),
    ("baseline-v2", "v2 baseline (k=3), sample 0"), ("baseline-v2-s1", "v2 baseline (k=3), sample 1"),
    ("headers-v2", "v2 + metadata header (k=3)"), ("headers_k5-v2", "v2 + metadata header + k=5"),
    ("k5-v2", "v2 + k=5, sample 0"), ("k5-v2-s1", "v2 + k=5, sample 1"),
    ("idmatch-v2", "v2 + patient-ID match (k=3), sample 0"), ("idmatch-v2-s1", "v2 + patient-ID match (k=3), sample 1"),
    ("idmatch_k5-v2", "v2 final (ID match + k=5), sample 0"), ("idmatch_k5-v2-s1", "v2 final (ID match + k=5), sample 1"),
]
COLS = ["run", "label", "dataset", "k", "questions", "recall_at_3", "recall_at_k", "related_doc_hit_at_3",
        "related_doc_hit_at_k", "answer_correctness", "groundedness", "abstention_accuracy", "overall_correct",
        "api_errors", "judge_errors", "avg_context_chars"]
rows = []
for stem, label in RUNS:
    d = json.loads((RESULTS / f"{stem}.json").read_text())
    a, r, m = d["aggregate"], d["aggregate"]["retrieval"], d["meta"]
    ctx = [sum(len(c) for c in q["retrieved_chunks"]) for q in d["questions"]]
    rows.append([stem, label, m["dataset"], m["retrieval_limit"], a["questions"], r["recall_at_3"], r["recall_at_k"],
                 r["unanswerable_related_doc_hit_at_3"], r["unanswerable_related_doc_hit_at_k"],
                 a["answer_correctness_answerable"], a["groundedness_all"], a["abstention_accuracy"],
                 a["overall_correct"], a["api_errors"], a["judge_errors"], round(sum(ctx) / len(ctx))])
with open(RESULTS / "summary.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(COLS)
    w.writerows(rows)
print("| Run | k | Recall@3 | Recall@k | Related-note hit@3 | Answer correct | Grounded | Abstention acc. | Avg context chars |")
print("|---|---|---|---|---|---|---|---|---|")
for r in rows:
    print(f"| {r[1]} | {r[3]} | {r[5]:.3f} | {r[6]:.3f} | {r[7]:.3f} | {r[9]:.3f} | {r[10]:.3f} | {r[11]:.3f} | {r[15]} |")
