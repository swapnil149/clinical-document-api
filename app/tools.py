from anthropic import beta_tool

from app.database import SessionLocal
from app.models import Document
from app.rag import search_similar_chunks


@beta_tool
def get_document(document_id: int) -> str:
    print(f"TOOL CALLED: get_document({document_id})")
    """Retrieve a clinical document from the database using its document ID.

    Args:
        document_id: The database ID of the clinical document.
    """

    db = SessionLocal()

    try:
        document = (
            db.query(Document)
            .filter(Document.id == document_id)
            .first()
        )

        if document is None:
            return f"Document with ID {document_id} was not found."

        return (
            f"Document ID: {document.id}\n"
            f"Patient ID: {document.patient_id}\n"
            f"Document Type: {document.document_type}\n"
            f"Content: {document.content}"
        )

    finally:
        db.close()

@beta_tool
def search_documents(question: str) -> str:
    print(f"TOOL CALLED: search_documents({question})")
    """Search clinical documents for information relevant to a question.

    Args:
        question: The question or information to search for.
    """

    db = SessionLocal()

    try:
        results = search_similar_chunks(
            db,
            question,
            limit=3
        )

        if not results:
            return "No relevant documents were found."

        result_parts = []

        for chunk, document in results:
            result_parts.append(
                f"""Document ID: {document.id}
Patient ID: {document.patient_id}
Document Type: {document.document_type}
Relevant Content: {chunk.content}"""
            )

        return "\n\n".join(result_parts)

    finally:
        db.close()