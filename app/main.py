# fastapi is the installed Python package/framework. From the fastapi package, import the FastAPI class
# HTTPException: A FastAPI exception used to intentionally return an HTTP error response, such as 404 Not Found.
from fastapi import FastAPI, HTTPException

# Pydantic is a separate Python library for data validation and data parsing. 
# FastAPI integrates with Pydantic to validate request and response data.
# Note fastapi and pydantic are two different packages
# BaseModel is a class provided by Pydantic
from pydantic import BaseModel

# Below we have created an object (instance) of that class, and that object represents your web application.
# Import the FastAPI class and create a FastAPI web application object called app.
app = FastAPI()

# We use BaseModel class to describe: What should a valid document request look like?
# class DocumentCreate(BaseModel): defines a new class DocumentCreate that inherits from Pydantic's BaseModel class, 
# giving it Pydantic's validation and parsing behavior.
# patient_id: str tells Pydantic that patient_id is expected to be a string. 
# The class below defines the structure of a valid document coming into our API. 
# It must contain patient_id, document_type, and content, and all three must be strings.
# Since DocumentCreate inherits from BaseModel, Pydantic uses this annotation during validation.
class DocumentCreate(BaseModel):
    patient_id: str
    document_type: str
    content: str

# Document inherits from DocumentCreate
class Document(DocumentCreate):
    id: int

# Empty Python list that will temporarily act like our database.
# One more important thing: because below documents list is in-memory storage, every server restart resets below two lines
documents = []
# next_document_id is acting as a simple in-memory ID counter
next_document_id = 1
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
def create_document(document: DocumentCreate):
    global next_document_id
    new_document = {
        "id": next_document_id,
        "patient_id": document.patient_id,
        "document_type": document.document_type,
        "content": document.content,
    }
    documents.append(new_document)
    next_document_id += 1
    return new_document

# For the above post request
# Client sends: POST /documents + JSON body
#       ↓
# FastAPI receives HTTP request
#       ↓
# FastAPI reads the JSON body
#       ↓
# Pydantic creates/validates a Python object
#       ↓
# Your Python function receives that object
#       ↓
# Your function returns Python data
#       ↓
# FastAPI serializes that Python data back to JSON
#       ↓
# Client receives HTTP response

# This tells FastAPI: When a client sends a GET request to /documents, run the function directly below (get_documents).
@app.get("/documents")
def get_documents():
    return documents

# Below, The {document_id} part is called a path parameter.
@app.get("/documents/{document_id}")
def get_document(document_id: int):
    for document in documents:
        if document["id"] == document_id:
            return document

    raise HTTPException(status_code=404, detail="Document not found")

# Register a DELETE endpoint where document_id comes from the URL.
@app.delete("/documents/{document_id}")
def delete_document(document_id: int):
    # enumerate() gives you both: index and document
    for index, document in enumerate(documents):
        if document["id"] == document_id:
            deleted_document = documents.pop(index)
            return deleted_document

    raise HTTPException(status_code=404, detail="Document not found")