# fastapi is the installed Python package/framework. From the fastapi package, import the FastAPI class
# HTTPException: A FastAPI exception used to intentionally return an HTTP error response, such as 404 Not Found.
# Depends: Dependency: In FastAPI, Depends(...) lets an endpoint request something it needs, such as a database session.
# FastAPI creates/provides that dependency before calling the endpoint.
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app import models
from app.schemas import DocumentCreate, Document
# Below 3 lines for claude integration
import os
from dotenv import load_dotenv
from anthropic import Anthropic

#Reads .env
load_dotenv()
# os.getenv("ANTHROPIC_API_KEY") -> Gets the API key
# Anthropic(api_key=...) -> Creates a client we can use to talk to Claude
# client as our connection/interface to the Claude API.
client = Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

# Look at all SQLAlchemy models that inherit from Base, and create the corresponding database tables if they do not already exist.
models.Base.metadata.create_all(bind=engine)

# helper function whose job is to provide a database session.
# get_db() creates a SQLAlchemy session, yields it to the endpoint, and closes it after the request finishes.
def get_db():
    db = SessionLocal()
    try:
        # yield means Give this database session to the FastAPI endpoint that needs it.
        yield db
    finally:
        db.close()


# Below we have created an object (instance) of that class, and that object represents your web application.
# Import the FastAPI class and create a FastAPI web application object called app.
app = FastAPI()

# The @ means apply this decorator to the function directly below it.
# That app object is the central object for our backend. We use it to tell FastAPI:
# 1) to Register a GET route, and 2) Register a POST route.
# Register the Python function immediately below i.e. health check as the function responsible for handling GET requests to /health
@app.get("/health")
def health_check():
    return {"status": "healthy"}

# document: DocumentCreate - That is a Python type hint. It tells FastAPI:
# The document parameter should contain data matching the DocumentCreate model.
# Below function creates a Python dictionary for the new document and assigns an ID.
# The successful response from this endpoint should have the structure defined by the Document Pydantic model.
@app.post(
    "/documents",
    status_code=201,
    response_model=Document
)
def create_document(
    document: DocumentCreate,
    # FastAPI, before calling this function (create_Document), run get_db() and give me the database session as db.
    db: Session = Depends(get_db)
):
    # models.Document: This creates a SQLAlchemy ORM object. It represents a future row in the PostgreSQL documents table.
    db_document = models.Document(
        patient_id=document.patient_id,
        document_type=document.document_type,
        content=document.content
    )

    # Tell this SQLAlchemy session that I want to insert this object into the database.
    db.add(db_document)
    db.commit()  # Permanently save the pending database changes.
    db.refresh(db_document)  # reloads the object from PostgreSQL.
    # This is useful because the database may have generated values such as: id = 1.
    # After refresh, db_document.id contains that database-generated ID.
    return db_document

# This tells FastAPI: When a client sends a GET request to /documents, run the function directly below (get_documents).
@app.get("/documents", response_model=list[Document])
# means FastAPI gives this endpoint ("/documnets") a database session.
def get_documents(db: Session = Depends(get_db)):
    # Query the Document ORM model, which maps to the PostgreSQL documents table that Return all rows.
    return db.query(models.Document).all()

# Below, The {document_id} part is called a path parameter.
@app.get("/documents/{document_id}", response_model=Document)
def get_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    document = (
        db.query(models.Document)
        .filter(models.Document.id == document_id)
        .first() # returns the first matching row, or None if nothing matches.
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    return document

# Register a DELETE endpoint where document_id comes from the URL.
@app.delete("/documents/{document_id}", response_model=Document)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    document = (
        db.query(models.Document)
        .filter(models.Document.id == document_id)
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    db.delete(document)
    db.commit()
    return document

@app.post("/documents/{document_id}/analyze")
def analyze_document(
    document_id: int,
    db: Session = Depends(get_db)
):
    # 1. Get the document from PostgreSQL
    document = (
        db.query(models.Document)
        .filter(models.Document.id == document_id)
        .first()
    )

    # 2. Return 404 if the document doesn't exist
    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    # 3. Send the document content to Claude
    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=500,
        messages=[
            {
                "role": "user",
                "content": f"""
Summarize the following clinical document.

Document:
{document.content}
"""
            }
        ]
    )

    # 4. Return Claude's response
    return {
        "document_id": document.id,
        "analysis": message.content[0].text
    }