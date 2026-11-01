# RAG helps an LLM find the relevant information from an external knowledge source before answering a question.
from app.models import DocumentChunk, Document
from app.embeddings import (
    generate_document_embedding,
    generate_query_embedding
)

import re

from sqlalchemy import func

# Optional: prefix each chunk with its patient and document type before embedding (only the embedded text
# changes). Evaluated in eval/ and found to give no measurable retrieval benefit, so it is off by default.
EMBED_METADATA_HEADER = False

# Number of chunks retrieved for /rag/ask.
RAG_TOP_K = 5

# Dense embeddings match exact identifiers poorly. When a question names a known patient ID, the best chunks
# of that patient's notes are placed first in the results (up to PATIENT_MATCH_CHUNKS), followed by the usual
# cosine-distance results.
MATCH_PATIENT_IDS = True
PATIENT_MATCH_CHUNKS = 2


def embedding_text(document, chunk: str) -> str:
    if not EMBED_METADATA_HEADER:
        return chunk
    return f"Patient {document.patient_id} | {document.document_type}\n{chunk}"


# this is character-based chunking, not token-based or semantic chunking.
# Different types of chunking strategies: character based, token based, sentence based, structure based, and semantic based.
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100):
    chunks = []

    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        chunk = text[start:end]

        chunks.append(chunk)

        if end == len(text):
            break

        start += chunk_size - overlap

    return chunks

# Indexing: split a document into chunks, generate embeddings,
# and store the chunks + embeddings for later retrieval.
def index_document(db, document):
    chunks = chunk_text(document.content)

    try:
        # Remove any previous RAG index for this document
        db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document.id
        ).delete(synchronize_session=False)

        for chunk in chunks:
            embedding = generate_document_embedding(embedding_text(document, chunk))

            db_chunk = DocumentChunk(
                document_id=document.id,
                content=chunk,
                embedding=embedding
            )

            db.add(db_chunk)

        db.commit()

        return len(chunks)

    except Exception:
        db.rollback()
        raise

# Retrieval: embed the user's question and find the most semantically
# similar stored chunks using cosine distance.
# Patient IDs in the synthetic data look like "P-A101" (eval corpus) or "SYNTH-001" (manual API tests): a letter
# prefix, a hyphen, an optional letter group and a number. The pattern is deliberately generic so unknown IDs
# (e.g. "P-A150") are still extracted and then rejected by the database lookup. Neighbouring word characters and hyphens are excluded so an ID
# is never matched inside a longer token ("XP-A101", "P-A1015", "P-A101-2").
PATIENT_ID_PATTERN = re.compile(r"(?<![\w-])[A-Za-z]{1,6}-[A-Za-z]{0,3}\d{1,10}(?![\w-])")
MAX_ID_CANDIDATES = 10


def extract_patient_id_candidates(query: str):
    """ID-shaped tokens in the question, upper-cased and de-duplicated, in order of appearance."""
    found = (m.group(0).upper() for m in PATIENT_ID_PATTERN.finditer(query))
    return list(dict.fromkeys(found))[:MAX_ID_CANDIDATES]


def find_mentioned_patient_ids(db, query: str):
    """Known patient IDs named in the question (case-insensitive, exact). Returns IDs as stored.

    Candidates are extracted from the question first and only those are looked up (indexed on
    upper(patient_id)), so the cost does not depend on how many patients exist and questions
    without an ID never touch the database.
    """
    candidates = extract_patient_id_candidates(query)
    if not candidates:
        return []
    rows = db.query(Document.patient_id).filter(func.upper(Document.patient_id).in_(candidates)).distinct()
    return [row[0] for row in rows]


def search_similar_chunks(db, query: str, limit: int = 3):
    query_embedding = generate_query_embedding(query)
    distance = DocumentChunk.embedding.cosine_distance(query_embedding)

    base = db.query(DocumentChunk, Document).join(
        Document,
        DocumentChunk.document_id == Document.id
    )

    results = base.order_by(distance).limit(limit).all()

    if MATCH_PATIENT_IDS:
        patient_ids = find_mentioned_patient_ids(db, query)
        if patient_ids:
            pinned = (
                base.filter(func.upper(Document.patient_id).in_([p.upper() for p in patient_ids]))
                .order_by(distance)
                .limit(min(PATIENT_MATCH_CHUNKS, limit))
                .all()
            )
            pinned_ids = {chunk.id for chunk, _ in pinned}
            results = pinned + [r for r in results if r[0].id not in pinned_ids]
            results = results[:limit]

    return results