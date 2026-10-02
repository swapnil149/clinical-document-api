# RAG helps an LLM find the relevant information from an external knowledge source before answering a question.
from app.models import DocumentChunk, Document
from app.embeddings import (
    generate_document_embedding,
    generate_query_embedding
)

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
            embedding = generate_document_embedding(chunk)

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
def search_similar_chunks(db, query: str, limit: int = 3):
    query_embedding = generate_query_embedding(query)

    results = (
        db.query(DocumentChunk, Document)
        .join(
            Document,
            DocumentChunk.document_id == Document.id
        )
        .order_by(
            DocumentChunk.embedding.cosine_distance(query_embedding)
        )
        .limit(limit)
        .all()
    )

    return results