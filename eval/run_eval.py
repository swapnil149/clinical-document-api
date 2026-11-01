"""Local RAG evaluation for the Clinical Document API.

Runs the real FastAPI app in-process (TestClient) against a LOCAL PostgreSQL/pgvector database,
indexes a synthetic corpus through POST /documents, asks the questions through POST /rag/ask, and scores
retrieval (Recall@3), correctness, groundedness and abstention. Voyage and Claude responses are cached on
disk (eval/.cache) so reruns are cheap and reproducible. Nothing here touches AWS.

Usage (see README for setup):
    export DATABASE_URL=postgresql://evaluser@127.0.0.1:5548/eval_db
    python eval/run_eval.py --name baseline
"""
import argparse
import csv
import hashlib
import inspect
import json
import os
import re
import statistics
import subprocess
import sys
import time
import types
from datetime import datetime, timezone
from pathlib import Path

EVAL = Path(__file__).resolve().parent
ROOT = EVAL.parent
sys.path.insert(0, str(ROOT))

# Safety guard: only ever run against the local evaluation database.
if not re.match(r"^postgresql(\+psycopg2)?://[^@/]*@(127\.0\.0\.1|localhost)(:\d+)?/eval_db$",
                os.environ.get("DATABASE_URL", "")):
    sys.exit("Refusing to run: DATABASE_URL must point to the local eval_db (127.0.0.1/localhost).")

import anthropic  # noqa: E402
import voyageai.error as ve  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app import embeddings, rag  # noqa: E402
from app import main as app_main  # noqa: E402
from app.database import SessionLocal, engine  # noqa: E402

CACHE = EVAL / ".cache"
JUDGE_MODEL = "claude-haiku-4-5"
EMBED_MODEL = re.search(r'model="([^"]+)"', (ROOT / "app/embeddings.py").read_text()).group(1)
ENDPOINT_MODEL = re.search(r'model="([^"]+)"', (ROOT / "app/main.py").read_text()).group(1)
STATS = {"voyage_live": 0, "voyage_cached": 0, "claude_live": 0, "claude_cached": 0}

# An answer "abstains" when it says the requested information is unavailable. Deliberately excludes bare
# negations such as "does not have diabetes", which are valid answers (fixed after reviewing baseline-v2).
ABSTAIN_RE = re.compile(
    r"(does not|do not|doesn't|cannot|can't|unable to)\s+(provide|contain|include|specify|determine|answer)|"
    r"not (enough|sufficient)|insufficient|no information|no (such )?(patient|record)|"
    r"not (documented|mentioned|stated|specified|available|included|provided|recorded)",
    re.I)


# ---------------------------------------------------------------- caching
def _key(*parts):
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()


def cache_get(kind, key):
    p = CACHE / kind / f"{key}.json"
    return json.loads(p.read_text()) if p.exists() else None


def cache_put(kind, key, value):
    p = CACHE / kind / f"{key}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value))


OFFLINE = False  # --offline: any cache miss raises instead of calling Voyage/Claude (guarantees no paid calls)


class CacheMiss(RuntimeError):
    pass


def embed_live(texts, input_type):
    if OFFLINE:
        raise CacheMiss(f"--offline: {len(texts)} uncached {input_type} embedding(s) would need a live Voyage call")
    for _ in range(12):
        try:
            STATS["voyage_live"] += len(texts)
            return embeddings.voyage_client.embed(texts, model=EMBED_MODEL, input_type=input_type).embeddings
        except ve.RateLimitError:
            STATS["voyage_live"] -= len(texts)
            print("  Voyage rate limited; waiting 25s", flush=True)
            time.sleep(25)
    raise RuntimeError("Voyage rate limit persisted")


def cached_embed(input_type):
    def fn(text_):
        key = _key("voyage", EMBED_MODEL, input_type, text_)
        hit = cache_get("voyage", key)
        if hit is not None:
            STATS["voyage_cached"] += 1
            return hit
        vec = embed_live([text_], input_type)[0]
        cache_put("voyage", key, vec)
        return vec
    return fn


def prewarm(doc_texts, query_texts):
    """Embed all uncached texts in a few batched Voyage calls (avoids per-call rate limits)."""
    for input_type, texts in (("document", doc_texts), ("query", query_texts)):
        todo = [t for t in dict.fromkeys(texts) if cache_get("voyage", _key("voyage", EMBED_MODEL, input_type, t)) is None]
        for i in range(0, len(todo), 64):
            batch = todo[i:i + 64]
            for t, v in zip(batch, embed_live(batch, input_type)):
                cache_put("voyage", _key("voyage", EMBED_MODEL, input_type, t), v)
        print(f"  prewarm {input_type}: {len(todo)} new embeddings of {len(set(texts))}", flush=True)


def cached_create(real_create, namespace, sample):
    def create(**kwargs):
        key = _key("claude", namespace, str(sample), json.dumps(kwargs, sort_keys=True, default=str))
        hit = cache_get("claude", key)
        if hit is not None:
            STATS["claude_cached"] += 1
            return anthropic.types.Message.model_validate(hit)
        if OFFLINE:
            raise CacheMiss(f"--offline: uncached Claude call ({namespace}) would need a live API call")
        STATS["claude_live"] += 1
        msg = real_create(**kwargs)
        cache_put("claude", key, msg.model_dump(mode="json"))
        return msg
    return create


# ---------------------------------------------------------------- judging
JUDGE_PROMPT = """You are grading a retrieval-augmented question answering system on synthetic clinical notes.

CONTEXT (the only information the system was given):
{context}

QUESTION: {question}

REFERENCE ANSWER: {reference}

SYSTEM ANSWER: {answer}

Return ONLY a JSON object with these keys:
- "grounded": true if every factual claim in the system answer is supported by the CONTEXT, false if it states any fact that is not in the CONTEXT (an answer that only says the information is unavailable is grounded unless it asserts unsupported facts).
- "unsupported_claims": list of short strings naming any unsupported claims (empty list if none).
- "matches_reference": true if the system answer agrees with the REFERENCE ANSWER in substance (for a reference saying the information is not available, true only if the system answer says the information is not available), otherwise false."""


def judge(judge_create, question, reference, answer, context):
    prompt = JUDGE_PROMPT.format(context=context, question=question, reference=reference, answer=answer)
    try:
        msg = judge_create(model=JUDGE_MODEL, max_tokens=400,
                           messages=[{"role": "user", "content": prompt}])
        raw = msg.content[0].text
        data = json.loads(re.search(r"\{.*\}", raw, re.S).group(0))
        return {"grounded": bool(data["grounded"]), "unsupported_claims": data.get("unsupported_claims", []),
                "matches_reference": bool(data["matches_reference"]), "error": None}
    except Exception as exc:  # recorded, never hidden
        return {"grounded": None, "unsupported_claims": [], "matches_reference": None,
                "error": f"{type(exc).__name__}"}


# ---------------------------------------------------------------- run
def git_info():
    def run(*a):
        return subprocess.run(a, cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return {"commit": run("git", "rev-parse", "--short", "HEAD"),
            "app_modified_since_commit": bool(run("git", "status", "--porcelain", "app", "requirements.txt"))}


def reset_and_ingest(client, corpus):
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE documents RESTART IDENTITY CASCADE"))
    idmap = {}
    for d in corpus:
        r = client.post("/documents", json={k: d[k] for k in ("patient_id", "document_type", "content")})
        if r.status_code != 201:
            sys.exit(f"ingest failed for {d['key']}: HTTP {r.status_code}")
        idmap[d["key"]] = r.json()["id"]
    return idmap


def ask_endpoint(client, question):
    for attempt in range(1, 4):
        r = client.post("/rag/ask", json={"question": question})
        if r.status_code not in (502, 503):
            return r, attempt
        time.sleep(20)
    return r, attempt


def score_question(q, idmap_rev, client, judge_create):
    t0 = time.time()
    db = SessionLocal()
    try:
        hits = rag.search_similar_chunks(db, q["question"], limit=rag.RAG_TOP_K)  # same function/limit as /rag/ask
        retrieved = [{"rank": i + 1, "doc_key": idmap_rev[doc.id], "doc_id": doc.id, "chunk": chunk.content}
                     for i, (chunk, doc) in enumerate(hits)]
        context = "\n\n".join(f"Patient ID: {doc.patient_id}\nDocument Type: {doc.document_type}\nContent: {chunk.content}"
                              for chunk, doc in hits)
    finally:
        db.close()

    gold = q["gold_docs"]
    got = {r["doc_key"] for r in retrieved[:3]}
    got_k = {r["doc_key"] for r in retrieved}
    recall = (len(set(gold) & got) / len(gold)) if gold else None
    recall_k = (len(set(gold) & got_k) / len(gold)) if gold else None
    related = q.get("related_docs") or []  # unanswerable questions: the note where the info would be if present

    resp, attempts = ask_endpoint(client, q["question"])
    rec = {"id": q["id"], "category": q["category"], "question": q["question"], "gold_docs": gold,
           "retrieved_docs": [r["doc_key"] for r in retrieved], "retrieved_chunks": [r["chunk"] for r in retrieved],
           "recall_at_3": recall, "hit_at_3": (bool(set(gold) & got) if gold else None),
           "recall_at_k": recall_k, "related_docs": related,
           "related_hit_at_3": (bool(set(related) & got) if related else None),
           "related_hit_at_k": (bool(set(related) & got_k) if related else None),
           "http_status": resp.status_code, "attempts": attempts, "answer": None, "error": None}
    if resp.status_code != 200:
        rec["error"] = f"HTTP {resp.status_code}"
        rec["latency_s"] = round(time.time() - t0, 2)
        return rec
    answer = resp.json()["answer"]
    rec["answer"] = answer

    expect_abstain = q["category"] == "unanswerable"
    abstained = bool(ABSTAIN_RE.search(answer))
    rule_facts = all(re.search(p, answer, re.I) for p in q["required_facts"]) if q["required_facts"] else None
    rec.update({"expected_abstain": expect_abstain, "abstained": abstained,
                "rule_correct": (not abstained and rule_facts) if not expect_abstain else abstained})
    j = judge(judge_create, q["question"], q["reference_answer"], answer, context)
    rec["judge"] = j
    flags = []
    if j["error"]:
        flags.append("judge_error")
    else:
        if j["grounded"] is False:
            flags.append("judge_ungrounded")
        if j["matches_reference"] != rec["rule_correct"]:
            flags.append("rule_vs_judge_disagree")
    if not expect_abstain and rec["rule_correct"] and rec["hit_at_3"] is False:
        flags.append("correct_without_gold_retrieval")
    rec["review_flags"] = flags
    rec["latency_s"] = round(time.time() - t0, 2)
    return rec


def apply_reviews(rec, reviews):
    rv = reviews.get(rec["id"])
    rec["review"] = rv
    if rec["error"]:
        rec.update(final_correct=None, final_grounded=None, final_abstained=None, review_status="error")
        return
    rec["final_abstained"] = rv["abstained"] if rv and "abstained" in rv else rec["abstained"]
    if rec["expected_abstain"]:
        auto_correct = rec["final_abstained"]
    else:
        auto_correct = rec["rule_correct"] if not (rv and "abstained" in rv) else (rec["rule_correct"] and not rv["abstained"])
    rec["final_correct"] = rv["correct"] if rv and "correct" in rv else auto_correct
    auto_grounded = rec["judge"]["grounded"]
    rec["final_grounded"] = rv["grounded"] if rv and "grounded" in rv else auto_grounded
    if rv:
        rec["review_status"] = "reviewed"
    elif rec["review_flags"]:
        rec["review_status"] = "flagged_unreviewed"
    else:
        rec["review_status"] = "auto"


def mean(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 4) if xs else None


def aggregate(recs):
    ok = [r for r in recs if not r["error"]]
    ans = [r for r in ok if r["category"] != "unanswerable"]
    unans = [r for r in ok if r["category"] == "unanswerable"]
    cats = {}
    for c in ("answerable", "semantic", "unanswerable"):
        cr = [r for r in ok if r["category"] == c]
        cats[c] = {"n": len([r for r in recs if r["category"] == c]), "scored": len(cr),
                   "recall_at_3": mean([r["recall_at_3"] for r in cr]),
                   "correct": mean([r["final_correct"] for r in cr]),
                   "grounded": mean([r["final_grounded"] for r in cr])}
    return {
        "questions": len(recs), "scored": len(ok), "api_errors": len(recs) - len(ok),
        "judge_errors": len([r for r in ok if r["judge"]["error"]]),
        "retrieval": {"recall_at_3": mean([r["recall_at_3"] for r in ans]),
                      "hit_rate_at_3": mean([r["hit_at_3"] for r in ans]),
                      "questions_with_gold": len(ans),
                      "recall_at_k": mean([r["recall_at_k"] for r in ans]),
                      "unanswerable_related_doc_hit_at_3": mean([r["related_hit_at_3"] for r in unans]),
                      "unanswerable_related_doc_hit_at_k": mean([r["related_hit_at_k"] for r in unans]),
                      "unanswerable_with_related_doc": len([r for r in unans if r["related_hit_at_3"] is not None])},
        "answer_correctness_answerable": mean([r["final_correct"] for r in ans]),
        "groundedness_all": mean([r["final_grounded"] for r in ok]),
        "groundedness_non_abstained": mean([r["final_grounded"] for r in ok if not r["final_abstained"]]),
        "abstention_accuracy": mean([r["final_abstained"] == r["expected_abstain"] for r in ok]),
        "correct_abstention_on_unanswerable": mean([r["final_abstained"] for r in unans]),
        "false_abstention_on_answerable": mean([r["final_abstained"] for r in ans]),
        "overall_correct": mean([r["final_correct"] for r in ok]),
        "by_category": cats,
        "review": {"reviewed": len([r for r in ok if r["review_status"] == "reviewed"]),
                   "flagged_unreviewed": len([r for r in ok if r["review_status"] == "flagged_unreviewed"])},
        "median_latency_s": round(statistics.median([r["latency_s"] for r in ok]), 2) if ok else None,
    }


def write_outputs(name, meta, agg, recs):
    out = EVAL / "results"
    out.mkdir(exist_ok=True)
    (out / f"{name}.json").write_text(json.dumps({"meta": meta, "aggregate": agg, "questions": recs}, indent=2))
    cols = ["id", "category", "recall_at_3", "recall_at_k", "hit_at_3", "http_status", "expected_abstain", "abstained", "final_abstained",
            "rule_correct", "final_correct", "final_grounded", "related_hit_at_3", "review_status", "review_flags", "retrieved_docs",
            "gold_docs", "question", "answer"]
    with open(out / f"{name}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in recs:
            w.writerow([";".join(r[c]) if isinstance(r.get(c), list) else r.get(c, "") for c in cols])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="result name, e.g. baseline or improved")
    ap.add_argument("--sample", type=int, default=0, help="sample index; a new value forces fresh Claude answers")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--variant", choices=["current", "baseline", "headers", "headers_k5", "k5", "idmatch", "idmatch_k5"],
                    default="current",
                    help="retrieval configuration (metadata header / top-k / patient-ID matching): "
                         "baseline = off/3/off (original behaviour); headers = on/3/off; headers_k5 = on/5/off; "
                         "k5 = off/5/off; idmatch = off/3/on; idmatch_k5 = off/5/on; current = app defaults")
    ap.add_argument("--dataset", choices=["v1", "v2"], default="v2",
                    help="v1 = original 14 documents / 30 questions; v2 adds distractor documents and 6 questions")
    ap.add_argument("--offline", action="store_true",
                    help="never call Voyage/Claude: fail on any cache miss (verifies a run is reproducible from the cache)")
    args = ap.parse_args()
    global OFFLINE
    OFFLINE = args.offline
    if OFFLINE:
        os.environ.setdefault("ANTHROPIC_API_KEY", "offline-no-calls")  # client construction only; never used

    corpus = json.loads((EVAL / "data/corpus.json").read_text())
    questions = json.loads((EVAL / "data/questions.json").read_text())
    if args.dataset == "v1":
        corpus = [d for d in corpus if d["set"] == "core"]
        questions = [q for q in questions if q["added_in"] == "v1"]
    questions = questions[: args.limit]
    rv_path = EVAL / "reviews" / f"{args.name}.json"
    reviews = json.loads(rv_path.read_text()) if rv_path.exists() else {}

    variants = {"baseline": (False, 3, False), "headers": (True, 3, False), "headers_k5": (True, 5, False),
                "k5": (False, 5, False), "idmatch": (False, 3, True), "idmatch_k5": (False, 5, True)}
    if args.variant in variants:
        rag.EMBED_METADATA_HEADER, rag.RAG_TOP_K, rag.MATCH_PATIENT_IDS = variants[args.variant]
    rag.generate_document_embedding = cached_embed("document")
    rag.generate_query_embedding = cached_embed("query")
    app_main.client.messages.create = cached_create(app_main.client.messages.create, "endpoint", args.sample)
    judge_client = anthropic.Anthropic()
    judge_create = cached_create(judge_client.messages.create, "judge", 0)

    print(f"[{args.name}] embedding model={EMBED_MODEL}, answer model={ENDPOINT_MODEL}, judge={JUDGE_MODEL}", flush=True)
    def doc_inputs(d):
        meta_doc = types.SimpleNamespace(patient_id=d["patient_id"], document_type=d["document_type"])
        return [rag.embedding_text(meta_doc, c) for c in rag.chunk_text(d["content"])]
    prewarm([t for d in corpus for t in doc_inputs(d)], [q["question"] for q in questions])

    client = TestClient(app_main.app)
    idmap = reset_and_ingest(client, corpus)
    rev = {v: k for k, v in idmap.items()}
    db = SessionLocal()
    n_chunks = db.execute(text("SELECT count(*) FROM document_chunks")).scalar()
    db.close()
    print(f"  indexed {len(corpus)} documents -> {n_chunks} chunks", flush=True)

    recs = []
    for q in questions:
        rec = score_question(q, rev, client, judge_create)
        recs.append(rec)
        print(f"  {rec['id']} [{rec['category'][:6]}] http={rec['http_status']} recall={rec['recall_at_3']} "
              f"flags={rec.get('review_flags')}", flush=True)
    for rec in recs:
        apply_reviews(rec, reviews)

    sig = inspect.signature(rag.chunk_text).parameters
    meta = {"name": args.name, "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "git": git_info(), "sample": args.sample, "embedding_model": EMBED_MODEL, "answer_model": ENDPOINT_MODEL,
            "judge_model": JUDGE_MODEL, "chunk_size": sig["chunk_size"].default, "chunk_overlap": sig["overlap"].default,
            "dataset": args.dataset, "variant": args.variant, "embed_metadata_header": rag.EMBED_METADATA_HEADER,
            "match_patient_ids": rag.MATCH_PATIENT_IDS,
            "retrieval_limit": rag.RAG_TOP_K, "documents": len(corpus), "chunks": n_chunks, "api_usage": dict(STATS)}
    agg = aggregate(recs)
    write_outputs(args.name, meta, agg, recs)
    print(json.dumps(agg, indent=2))
    print("api usage this run:", STATS)


if __name__ == "__main__":
    main()
