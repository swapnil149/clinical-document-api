
# Pydantic is a separate Python library for data validation and data parsing. 
# FastAPI integrates with Pydantic to validate request and response data.
# Note fastapi and pydantic are two different packages
# BaseModel is a class provided by Pydantic
from pydantic import BaseModel

# Pydantic BaseModel is used for API request/response validation.
# This is different from SQLAlchemy's Base, which is used for database table mapping.

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

    # Nested Pydantic configuration class.
    # This is not a field of Document.
    # from_attributes=True allows Pydantic to build this schema
    # from SQLAlchemy ORM objects using attributes like obj.id.
    class Config:
        from_attributes = True

# Request schema for the RAG question-answering endpoint.
class QuestionRequest(BaseModel):
    question: str
    question: str

class AgentRequest(BaseModel):
    message: str