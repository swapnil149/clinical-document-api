# Patient-ID matching benchmark

This folder measures one small piece of the RAG pipeline: **finding which known patient IDs a question mentions**. It
compares the original code with the optimized code on a local PostgreSQL database. Everything runs locally. There are no
AWS, Voyage or Claude calls.

**Important:** these numbers are for patient-ID matching only. They are *not* the latency of a complete `/rag/ask` request.
A real request also calls Voyage (embedding the question) and Claude (writing the answer), which take hundreds of
milliseconds to seconds each and are not measured here. See [What this does and does not tell you](#what-this-does-and-does-not-tell-you).

## The problem and the fix

**Original** (`app/rag.py` at commit `f3859d5`). On every question the code:
1. ran `SELECT DISTINCT patient_id FROM documents` and pulled **every** patient ID into Python, then
2. built a regex for **each** ID and searched the question with it.

Work per question grew with the number of patients, even when the question did not contain any patient ID.

**Optimized** (`find_mentioned_patient_ids` in `app/rag.py` today). The code now:
1. finds ID-shaped words in the **question** (for example `P-A101`) with one regex,
2. returns immediately if there are none (no database query at all), and otherwise
3. asks PostgreSQL only about those candidates: `WHERE upper(patient_id) IN (...)`.

Work per question now depends on how many IDs the question contains (usually 0 to 2), not on how many patients exist.

**Role of the index.** Without an index, even that `WHERE` query would have to read the whole table. The index
`ix_documents_patient_id_upper` is built on `upper(patient_id)`, the same expression the query uses (this is how the
match is case-insensitive), so PostgreSQL jumps straight to the matching rows. `EXPLAIN ANALYZE` confirms it (see Results).

## Method

- **Database:** a separate local database named `clinical_bench` (the script refuses to run on any database whose name does
  not end in `_bench`, or that is not on localhost). It is not the app database and not the evaluation database. The
  temporary `documents` table is created for each scale and dropped at the end.
- **Data:** synthetic. IDs like `P-A000123`, 3 notes per patient, at 100 / 1,000 / 10,000 / 100,000 distinct patients
  (302 to 300,002 rows). `ANALYZE` is run after loading.
- **Questions:** a valid ID, an unknown but well-formed ID, no ID, and (extra) two valid IDs.
- **Measuring:** each scenario runs 10 warm-up calls and then 100 measured calls of **each** implementation, alternating
  which goes first. The timer wraps the whole function call: the SQL query, moving rows to Python, and the Python
  matching. Both use the same database session and connection, the same data and the same questions.
- **Statistics:** P50 is the median, P95 is the 95th-percentile sample (nearest-rank), mean is the average, all from the
  100 measured samples. Speedup = original / optimized. Reduction = 100 x (1 - optimized / original).
- **Correctness:** at every scale both versions returned identical matches on 17 test questions (case variants, punctuation,
  partial IDs, IDs inside longer words, unknown IDs, multiple IDs, no ID). They also agreed on every timed call.

## Results

Machine: Apple M2, 8 cores, 16 GB; PostgreSQL 15.6 (Postgres.app, default settings); Python 3.12.4. All times in milliseconds.

| Patients | Scenario | Original P50 / P95 / mean (ms) | Optimized P50 / P95 / mean (ms) | Speedup (P50) | Latency reduction (P50) |
|---|---|---|---|---|---|
| 100 | valid_id | 1.047 / 1.170 / 1.075 | 0.865 / 0.999 / 0.878 | 1.2x | 17.38% |
| 100 | unknown_id | 1.130 / 1.232 / 1.129 | 0.929 / 1.019 / 0.932 | 1.2x | 17.75% |
| 100 | no_id | 1.206 / 1.321 / 1.212 | 0.015 / 0.022 / 0.016 | 79.8x | 98.75% |
| 100 | two_valid_ids | 1.116 / 1.287 / 1.136 | 0.993 / 1.245 / 1.034 | 1.1x | 10.98% |
| 1,000 | valid_id | 36.8 / 62.7 / 42.6 | 0.992 / 1.638 / 1.095 | 37.1x | 97.30% |
| 1,000 | unknown_id | 42.3 / 58.0 / 42.1 | 0.982 / 1.335 / 1.025 | 43.1x | 97.68% |
| 1,000 | no_id | 40.4 / 62.4 / 44.3 | 0.016 / 0.026 / 0.016 | 2,574.4x | 99.96% |
| 1,000 | two_valid_ids | 40.6 / 52.2 / 41.6 | 0.944 / 1.198 / 0.975 | 43.1x | 97.68% |
| 10,000 | valid_id | 381.7 / 568.9 / 403.4 | 1.027 / 1.499 / 1.245 | 371.5x | 99.73% |
| 10,000 | unknown_id | 357.0 / 412.1 / 368.3 | 0.933 / 1.144 / 0.959 | 382.7x | 99.74% |
| 10,000 | no_id | 361.6 / 395.3 / 366.4 | 0.015 / 0.019 / 0.014 | 24,243.4x | 100.00% |
| 10,000 | two_valid_ids | 398.1 / 595.7 / 429.9 | 1.082 / 1.790 / 1.190 | 368.1x | 99.73% |
| 100,000 | valid_id | 3,837.1 / 6,272.2 / 4,265.3 | 1.070 / 1.570 / 1.164 | 3,587.7x | 99.97% |
| 100,000 | unknown_id | 3,685.2 / 5,588.9 / 4,044.6 | 1.041 / 1.525 / 1.110 | 3,540.9x | 99.97% |
| 100,000 | no_id | 3,962.6 / 6,452.7 / 4,329.5 | 0.019 / 0.044 / 0.021 | 209,475.6x | 100.00% |
| 100,000 | two_valid_ids | 3,917.1 / 6,301.5 / 4,251.0 | 1.087 / 2.230 / 1.262 | 3,603.0x | 99.97% |

How to read it:
- At **100 patients** the saving is about 0.2 ms: too small to matter.
- From **about 1,000 patients** the original becomes slow (tens of ms, then hundreds, then seconds at 100,000), while the
  optimized version stays at about 1 ms because that is roughly one database round trip.
- For questions with **no ID**, the optimized version does no database work, so it takes about 0.02 ms. Those very large
  speedups (up to six figures) are real but compare against a tiny number. Treat the valid / unknown ID rows as the typical case.
- The 100,000-patient reductions are 99.97%, not exactly 100%.

**`EXPLAIN ANALYZE`** (full plans in `results/patient_id_matching_raw.json`). The original query is a sequential scan plus
a hash aggregate at every scale: 0.09 ms at 100 patients, 0.7 ms at 1,000, 7.3 ms at 10,000, 81.5 ms at 100,000 (inside
PostgreSQL only). The optimized lookup uses `ix_documents_patient_id_upper` (an index scan; a bitmap index scan at 100
patients) at every scale and takes 0.01 to 0.04 ms inside PostgreSQL.

## Why was the original so slow? (the regex investigation)

The first guess is "scanning the table is slow", but that is the smaller part. `regex_cost_investigation.py` splits the
original's time into fetching IDs from PostgreSQL versus matching in Python (median of 5 runs, unknown-ID question):

| Patients | Fetch IDs from PostgreSQL (ms) | Python regex loop, as originally written (ms) | Same loop, patterns compiled once (ms) |
|---|---|---|---|
| 1,000 | 1.6 | 35.3 | 1.1 |
| 10,000 | 14.6 | 383.3 | 10.4 |
| 100,000 | 152.7 | 5,071.3 | 122.2 |

The regex loop is about 20 to 35 times larger than the database fetch, and compiling the patterns is the reason: the same
loop with patterns compiled once is about 30 to 40 times faster.

**Python's regex cache.** `re.search(pattern_string, text)` first has to compile the pattern string into a matcher, which
costs tens of microseconds. To avoid repeating that, Python keeps a cache of recently compiled patterns. The cache is
limited: `re._MAXCACHE` is 512 in this Python version (3.12.4). The original code builds a *different* pattern for every
patient ID and walks the list in the same order on every question. Once there are more than 512 distinct patterns, each
one is pushed out of the cache before the next question reuses it, so **every pattern is recompiled on every question**. With
512 or fewer patterns the cache works and each question reuses them. The table below shows this directly (no database involved):

| Distinct patterns | `re.search` with pattern strings (ms) | per pattern (us) | Precompiled (ms) | per pattern (us) |
|---|---|---|---|---|
| 100 | 0.13 | 1.3 | 0.10 | 1.03 |
| 256 | 0.35 | 1.4 | 0.27 | 1.04 |
| 400 | 0.85 | 2.1 | 0.41 | 1.03 |
| 500 | 0.99 | 2.0 | 0.51 | 1.02 |
| 512 | 1.01 | 2.0 | 0.52 | 1.02 |
| 520 | 19.71 | 37.9 | 0.62 | 1.18 |
| 600 | 36.09 | 60.2 | 1.01 | 1.69 |
| 1,000 | 63.39 | 63.4 | 1.69 | 1.69 |
| 5,000 | 284.32 | 56.9 | 8.71 | 1.74 |
| 20,000 | 738.07 | 36.9 | 20.69 | 1.03 |

Per-pattern cost is about 2 us up to 512 patterns and jumps to about 35 to 65 us from 520 patterns, while the precompiled
version stays near 1 to 2 us throughout. That is why the original was fine at 100 patients and fell off a cliff after
roughly 500 (the 1,000-patient run is already 35 ms). The exact cache size is an implementation detail of CPython and could
differ in other versions.

Note that "precompile the patterns" would also have helped the original. It would still read every ID from the database and
test every ID on every question (about 120 ms at 100,000 patients here). The optimized design avoids that work entirely.

## What this does and does not tell you

- It measures **patient-ID matching only**. In a real `/rag/ask` request this step is followed by embedding the question
  (Voyage), a vector search, and an answer from Claude. The model calls are not part of this benchmark and normally take
  far longer than 1 ms, so the optimization removes a cost that grows with the number of patients; it does not make a whole
  request thousands of times faster.
- At 100,000 patients the original added several seconds to every question that goes through search, which would be very
  noticeable. At 100 patients it added a fraction of a millisecond, which is not.

## Limitations

- **One machine, one run per scale.** An Apple M2 laptop doing other things can vary by roughly 30%: the regex loop at
  100,000 patients took 5.1 s in the investigation but the whole original call had a 3.7 to 4.0 s median in the main run.
  Compare ratios and orders of magnitude, not exact milliseconds.
- **Warm local database.** All data is in memory, with no network and no concurrent users. A remote database such as RDS adds
  a network round trip to both versions (the optimized time would rise by about that much, and the original would also pay to
  transfer the whole ID list).
- **Synthetic data:** uniform IDs in one format, 3 notes per patient.
- **No confidence intervals** or statistical tests were computed. The original's P95 is 1.1 to 1.7 times its P50 at 1,000+
  patients, so its tail varies from run to run.
- **Restricted ID formats.** The optimized code only recognises ID-shaped tokens (`P-A101`, `SYNTH-001`: letters, hyphen,
  optional letters, digits). IDs such as `MRN12345` or `10042` are found by the original but not by the optimized version
  (verified in `results/patient_id_matching_raw.json`). Results are identical only for supported formats.
- The sequential-scan baseline in `EXPLAIN` is for `DISTINCT patient_id` with no index on `patient_id`, as in the original app.

## Reproducing

Needs a local PostgreSQL server (any port), the project virtualenv, and an empty database whose name ends in `_bench`:

```bash
createdb -h 127.0.0.1 -p PORT -U USER clinical_bench
export BENCH_DATABASE_URL=postgresql://USER@127.0.0.1:PORT/clinical_bench

# Main benchmark (all four scales takes roughly 30 minutes; most of it is the original at 100,000 patients)
.venv312/bin/python bench/patient_id_bench.py
.venv312/bin/python bench/patient_id_bench.py --scales 100,1000 --iters 100   # quick version, a few seconds

# Regex investigation (about a minute)
.venv312/bin/python bench/regex_cost_investigation.py

# Check that the README and CSV match the raw samples (no database needed)
python bench/check_results.py
```

Results are written to `bench/results/` (a custom `--out DIR` is available). The scripts only touch a table named
`documents` in the `_bench` database and drop it when finished.

Files: `patient_id_bench.py` (main benchmark), `regex_cost_investigation.py`, `check_results.py` (recomputes every
reported statistic from the raw samples), `results/patient_id_matching_raw.json` (every sample, plans, environment),
`results/patient_id_matching_summary.csv`, `results/regex_cost_investigation.json`.
