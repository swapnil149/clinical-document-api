import os
# SQLAlchemy is a Python library. More specifically, it is a database toolkit and ORM library for Python.
# create_engine creates the main SQLAlchemy connection interface to your database.
# sessionmaker helps create database sessions.A session is basically a working conversation with the database where you can:
# query data, insert data, update data, delete data, commit changes
# declarative_base() gives us the base class that our ORM database models will inherit from.
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# postgresql:// → database type, swapnil → PostgreSQL user, localhost → database server is on your laptop, 5432 → PostgreSQL port
# clinical_document_db → database name
# DATABASE_URL = "postgresql://swapnil@localhost:5432/clinical_document_db"
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://swapnil@localhost:5432/clinical_document_db"
)

# Explicitly use the psycopg2 PostgreSQL driver.
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg2://",
        1
    )

engine = create_engine(DATABASE_URL)

# Factory: An object/function configured to create other objects. 
# SessionLocal is a session factory; every call to SessionLocal() creates a new SQLAlchemy database session using the same configuration.
# Session factory: sessionmaker() creates a factory that can produce database session objects. 
# Calling SessionLocal() creates one session, which should usually be closed after the HTTP request finishes.
SessionLocal = sessionmaker(
    autocommit=False, # Database changes are not automatically committed. We explicitly call db.commit().
    autoflush=False, # SQLAlchemy will not automatically flush pending changes in some situations; we control that behavior more explicitly.
    bind=engine  # Sessions created by this factory use the SQLAlchemy engine, which knows how to connect to our PostgreSQL database.
)

# Later we will use session local factory as below:
# db1 = SessionLocal()  # a new database session object is created
# db2 = SessionLocal()
# db3 = SessionLocal()

# creates a base class that our ORM models will inherit from
Base = declarative_base()