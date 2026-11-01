"""Tests for patient-ID extraction/lookup and ID-pinned retrieval (app/rag.py).

Run:  .venv312/bin/python -m unittest discover -s tests -v

Nothing here calls Voyage, Claude or AWS. Query embeddings are stubbed. The PostgreSQL tests need a LOCAL
throwaway database and are skipped unless TEST_DATABASE_URL points at one (a 127.0.0.1/localhost database whose
name ends in "_test"); e.g. after `eval "$(eval/local_db.sh start)"`:
    createdb -h 127.0.0.1 -p 5548 -U evaluser clinical_test
    TEST_DATABASE_URL=postgresql://evaluser@127.0.0.1:5548/clinical_test .venv312/bin/python -m unittest discover -s tests -v
"""
import os
import re
import unittest
from unittest import mock

os.environ.setdefault("VOYAGE_API_KEY", "test-not-used")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-not-used")

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app import models, rag  # noqa: E402

KNOWN = ["P-A101", "P-A102", "P-A110", "P-A1011", "SYNTH-001"]


class ExtractionTests(unittest.TestCase):
    """Pure regex extraction: no database."""

    def extract(self, q):
        return rag.extract_patient_id_candidates(q)

    def test_case_insensitive_candidates_are_normalised(self):
        for q in ("What meds is P-A101 on?", "what meds is p-a101 on?", "P-a101?", "p-A101"):
            self.assertEqual(self.extract(q), ["P-A101"], q)

    def test_punctuation_next_to_id_is_allowed(self):
        for q in ("(P-A101)", "P-A101, then", "Is P-A101's BP ok?", "Notes: P-A101.", '"P-A101"'):
            self.assertEqual(self.extract(q), ["P-A101"], q)

    def test_ids_embedded_in_longer_tokens_are_not_extracted(self):
        for q in ("P-A101-2", "P-A101x", "ID_P-A101", "P--A101"):
            self.assertEqual(self.extract(q), [], q)
        # A longer prefix is a different (unknown) candidate, never P-A101.
        self.assertEqual(self.extract("XP-A101"), ["XP-A101"])

    def test_partial_ids_do_not_extract_other_ids(self):
        # A prefix/suffix of a real ID is its own (different) candidate or nothing; never the full ID.
        self.assertEqual(self.extract("patient P-A10 and A101 and P-A"), ["P-A10"])
        self.assertEqual(self.extract("P-A1011"), ["P-A1011"])

    def test_no_id_in_question(self):
        for q in ("", "What is the HbA1c target?", "patient 101", "A101 and 1001 and P_A101"):
            self.assertEqual(self.extract(q), [], q)

    def test_multiple_ids_in_order_deduplicated(self):
        self.assertEqual(self.extract("Compare P-A102 with p-a101, and again P-A102"), ["P-A102", "P-A101"])

    def test_other_synthetic_id_format(self):
        self.assertEqual(self.extract("summary for synth-001 please"), ["SYNTH-001"])

    def test_non_id_hyphenated_terms_are_only_candidates(self):
        # Shaped like an ID, so it is looked up; the database lookup (below) rejects it.
        self.assertEqual(self.extract("Summarise the COVID-19 notes"), ["COVID-19"])

    def test_candidate_count_is_capped(self):
        q = " ".join(f"P-A{n}" for n in range(100, 100 + 3 * rag.MAX_ID_CANDIDATES))
        self.assertEqual(len(self.extract(q)), rag.MAX_ID_CANDIDATES)


class LookupSqliteTests(unittest.TestCase):
    """find_mentioned_patient_ids against an in-memory database (validates candidates against real rows)."""

    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite://")
        models.Document.__table__.create(cls.engine)
        cls.db = sessionmaker(bind=cls.engine)()
        for i, pid in enumerate(KNOWN + ["P-A101"]):  # P-A101 twice: result must be distinct
            cls.db.add(models.Document(patient_id=pid, document_type="note", content=f"c{i}"))
        cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def find(self, q):
        return sorted(rag.find_mentioned_patient_ids(self.db, q))

    def test_exact_and_case_insensitive(self):
        self.assertEqual(self.find("meds for P-A101"), ["P-A101"])
        self.assertEqual(self.find("meds for p-a101"), ["P-A101"])  # returned as stored

    def test_other_format_and_non_id_terms(self):
        self.assertEqual(self.find("notes for synth-001"), ["SYNTH-001"])
        self.assertEqual(self.find("Summarise the COVID-19 notes"), [])

    def test_partial_ids_do_not_match(self):
        self.assertEqual(self.find("P-A10"), [])       # prefix of P-A101 / P-A102 / P-A110
        self.assertEqual(self.find("P-A1"), [])
        self.assertEqual(self.find("A101"), [])
        self.assertEqual(self.find("P-A10111"), [])    # longer than a real ID

    def test_longer_id_does_not_match_shorter_one(self):
        self.assertEqual(self.find("P-A1011"), ["P-A1011"])  # not also P-A101

    def test_invalid_or_unknown_ids(self):
        self.assertEqual(self.find("P-A150"), [])      # well-formed but not in the database
        self.assertEqual(self.find("P-1O1 and P_A101 and P A101"), [])
        self.assertEqual(self.find("XP-A101 and P-A101-2"), [])  # embedded in longer tokens

    def test_multiple_ids(self):
        self.assertEqual(self.find("Compare p-a102 and P-A110, ignore P-A150"), ["P-A102", "P-A110"])

    def test_question_without_ids_makes_no_database_query(self):
        db = mock.Mock()
        self.assertEqual(rag.find_mentioned_patient_ids(db, "What is the HbA1c target?"), [])
        db.query.assert_not_called()

    def test_lookup_is_filtered_by_the_candidates(self):
        # The query must filter on the candidates, not scan every patient_id.
        from sqlalchemy import event
        seen = []

        def record(conn, cursor, statement, *args):
            seen.append(statement)

        event.listen(self.engine, "before_cursor_execute", record)
        try:
            self.find("P-A101")
        finally:
            event.remove(self.engine, "before_cursor_execute", record)
        self.assertEqual(len(seen), 1)
        self.assertIn("upper(documents.patient_id) IN", seen[0].replace("UPPER", "upper"))


TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", "")
LOCAL_TEST_DB = re.match(r"^postgresql(\+psycopg2)?://[^@/]*@(127\.0\.0\.1|localhost)(:\d+)?/\w+_test$", TEST_DB_URL)


def vec(*head):
    return list(head) + [0.0] * (1024 - len(head))


@unittest.skipUnless(LOCAL_TEST_DB, "set TEST_DATABASE_URL to a local *_test PostgreSQL database with pgvector")
class RetrievalPostgresTests(unittest.TestCase):
    """search_similar_chunks on real pgvector, with stubbed query embeddings (no API calls)."""

    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(TEST_DB_URL.replace("postgresql://", "postgresql+psycopg2://", 1))
        with cls.engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.execute(text("DROP TABLE IF EXISTS document_chunks, documents CASCADE"))
        models.Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)
        db = cls.Session()
        # Query vector is (1,0,...). Patient notes P-A101/P-A102 are far from it; filler chunks are near it.
        specs = [("P-A101", [vec(0, 1, 0.1), vec(0, 1, 0.2), vec(0, 1, 0.3)]),
                 ("P-A102", [vec(0, 1, 0.4)]),
                 ("P-A103", [vec(1, 0.1), vec(1, 0.2), vec(1, 0.3), vec(1, 0.4)])]
        for pid, embs in specs:
            doc = models.Document(patient_id=pid, document_type="note", content=pid)
            db.add(doc)
            db.flush()
            for i, e in enumerate(embs):
                db.add(models.DocumentChunk(document_id=doc.id, content=f"{pid}#{i}", embedding=e))
        db.commit()
        db.close()

    @classmethod
    def tearDownClass(cls):
        with cls.engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS document_chunks, documents CASCADE"))

    def setUp(self):
        self.db = self.Session()
        p = mock.patch.object(rag, "generate_query_embedding", return_value=vec(1))
        p.start()
        self.addCleanup(p.stop)
        self.addCleanup(self.db.close)

    def search(self, q, limit=5):
        return [c.content for c, _ in rag.search_similar_chunks(self.db, q, limit=limit)]

    def test_without_id_it_is_plain_vector_order(self):
        self.assertEqual(self.search("what is the target?", limit=3), ["P-A103#0", "P-A103#1", "P-A103#2"])

    def test_named_patient_chunks_are_pinned_first_then_vector_results(self):
        # 2 best P-A101 chunks first (closest first), then the usual top results; limit respected.
        self.assertEqual(self.search("meds for P-A101?", limit=5),
                         ["P-A101#0", "P-A101#1", "P-A103#0", "P-A103#1", "P-A103#2"])

    def test_case_insensitive_id_pins_same_chunks(self):
        self.assertEqual(self.search("meds for p-a101?"), self.search("meds for P-A101?"))

    def test_pinned_chunks_are_not_duplicated_when_also_in_vector_results(self):
        out = self.search("meds for P-A103?", limit=5)
        self.assertEqual(len(out), len(set(out)))
        self.assertEqual(out[:2], ["P-A103#0", "P-A103#1"])

    def test_limit_is_respected(self):
        self.assertEqual(len(self.search("meds for P-A101?", limit=3)), 3)
        self.assertEqual(self.search("meds for P-A101?", limit=1), ["P-A101#0"])

    def test_multiple_ids_pin_the_two_closest_chunks_across_them(self):
        out = self.search("compare P-A101 and P-A102", limit=5)
        self.assertEqual(out[:2], ["P-A101#0", "P-A101#1"])
        self.assertEqual(len(out), 5)

    def test_unknown_or_partial_id_falls_back_to_vector_search(self):
        plain = self.search("what is the target?")
        self.assertEqual(self.search("notes for P-A150?"), plain)
        self.assertEqual(self.search("notes for P-A10?"), plain)

    def test_disabled_flag_gives_plain_vector_search(self):
        with mock.patch.object(rag, "MATCH_PATIENT_IDS", False):
            self.assertEqual(self.search("meds for P-A101?"), self.search("what is the target?"))

    def test_expression_index_exists_and_is_usable(self):
        models.ix_documents_patient_id_upper.create(bind=self.engine, checkfirst=True)  # idempotent
        with self.engine.begin() as conn:
            conn.execute(text("SET LOCAL enable_seqscan = off"))  # tiny table: force the planner's index choice
            plan = "\n".join(r[0] for r in conn.execute(text(
                "EXPLAIN SELECT DISTINCT patient_id FROM documents WHERE upper(patient_id) IN ('P-A101')")))
        self.assertIn("ix_documents_patient_id_upper", plan, plan)


if __name__ == "__main__":
    unittest.main()
