# Clinical Document API

A backend project built with **Python** and **FastAPI** that will evolve into a cloud-deployed clinical document processing service.

The goal of this project is to practice building a production-style backend using:

* Python
* FastAPI
* REST APIs
* PostgreSQL
* Docker
* AWS
* ECS / Fargate
* Terraform
* CloudWatch
* CI/CD
* Generative AI integration

This project is being built incrementally over 5 days, with a focus on understanding each backend and cloud concept rather than just assembling the final application.

## Project Goal

The API will accept synthetic clinical documents, store them, and eventually process them using an LLM to return structured information such as:

* summaries
* medications
* conditions
* follow-up information

No real patient data should be used in this project.

## Planned Architecture

```text
Client
  |
  v
Application Load Balancer
  |
  v
AWS ECS / Fargate
  |
  v
FastAPI Docker Container
  |
  +----> PostgreSQL / RDS
  |
  +----> LLM API
  |
  v
CloudWatch

Terraform provisions the AWS infrastructure.
```

## 5-Day Development Plan

### Day 1 — FastAPI Fundamentals

Build the REST API locally.

Planned endpoints:

```text
GET     /health
POST    /documents
GET     /documents
GET     /documents/{id}
DELETE  /documents/{id}
```

Topics:

* Python virtual environments
* FastAPI application setup
* REST endpoints
* request and response flow
* Pydantic models
* request validation
* HTTP status codes
* Swagger / OpenAPI documentation

### Day 2 — PostgreSQL and Docker

Replace temporary in-memory storage with PostgreSQL.

Topics:

* SQLAlchemy
* database models
* database sessions
* environment variables
* Docker images
* Docker containers
* Dockerfile
* containerized FastAPI application

### Day 3 — Generative AI and AWS

Add document-processing functionality and begin deploying the backend to AWS.

Topics:

* LLM API integration
* structured AI responses
* AWS IAM
* AWS regions
* Amazon ECR
* Amazon ECS
* AWS Fargate
* CloudWatch

### Day 4 — Terraform

Provision AWS infrastructure using Infrastructure as Code.

Topics:

* Terraform providers
* resources
* variables
* outputs
* `terraform init`
* `terraform plan`
* `terraform apply`
* VPC networking
* security groups
* Application Load Balancer
* ECS infrastructure

### Day 5 — Production Polish

Finish deployment and improve production readiness.

Topics:

* health checks
* logging
* error handling
* monitoring
* CI/CD
* architecture documentation
* testing
* production deployment

## Local Setup

### 1. Create a virtual environment

```bash
python3 -m venv .venv
```

`-m` tells Python to run a Python module as a program.

In this command:

```text
python3
```

runs Python 3.

```text
-m venv
```

runs Python's built-in `venv` module.

```text
.venv
```

is the directory where the virtual environment will be created.

### 2. Activate the virtual environment

On macOS:

```bash
source .venv/bin/activate
```

After activation, the terminal should show something similar to:

```text
(.venv)
```

### 3. Install FastAPI

```bash
pip install "fastapi[standard]"
```

## Current Project Structure

```text
clinical-document-api/
|
├── app/
│   ├── __init__.py
│   └── main.py
|
├── .venv/
|
└── README.md
```

## Current FastAPI Application

`app/main.py`

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

## Running the Application

From the project root:

```bash
fastapi dev app/main.py
```

The development server should run at:

```text
http://127.0.0.1:8000
```

### Health Check

Open:

```text
http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "healthy"
}
```

### Swagger API Documentation

FastAPI automatically generates interactive API documentation.

Open:

```text
http://127.0.0.1:8000/docs
```

## Request Flow

When a client calls:

```text
GET /health
```

the request currently flows like this:

```text
Browser / Client
      |
      | GET /health
      v
FastAPI Server
      |
      v
FastAPI Router
      |
      v
health_check()
      |
      v
Python dictionary
      |
      v
JSON response
      |
      v
Client
```

Later, after deployment to AWS, the same basic request flow will become:

```text
Client
  |
  v
AWS Application Load Balancer
  |
  v
ECS / Fargate
  |
  v
Docker Container
  |
  v
FastAPI
  |
  v
Route Handler
```

## Important Concepts Learned So Far

### Virtual Environment

A Python virtual environment isolates the packages used by this project from packages installed globally or used by other projects.

```text
clinical-document-api/
└── .venv/
    ├── Python
    └── project dependencies
```

### FastAPI

FastAPI is the Python web framework used to create the REST API.

```python
app = FastAPI()
```

creates the application.

### Route Decorator

```python
@app.get("/health")
```

registers the function below it as the handler for:

```text
GET /health
```

### Route Handler

```python
def health_check():
```

is the Python function FastAPI executes when the endpoint is called.

### Automatic JSON Serialization

Returning:

```python
{"status": "healthy"}
```

causes FastAPI to automatically create a JSON HTTP response.

## Next Step

Implement:

```text
POST /documents
```

and learn:

* Pydantic models
* request bodies
* Python type hints
* automatic request validation
* HTTP response codes
