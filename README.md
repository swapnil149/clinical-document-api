# Clinical Document API

A containerized backend API for storing, managing, analyzing, and semantically searching synthetic clinical documents using FastAPI, PostgreSQL, RAG, AWS, and the Anthropic Claude API.

The project demonstrates REST API development, relational database integration, Docker containerization, AWS cloud deployment, secure secret management, logging/monitoring, LLM API integration, and Retrieval-Augmented Generation (RAG).

The RAG pipeline uses Voyage AI embeddings and PostgreSQL with pgvector to retrieve relevant clinical document context before generating grounded answers with Claude.

> Note: The core API and Claude document-analysis functionality are deployed on AWS. The RAG functionality is currently implemented and tested locally.

## Tech Stack

## Tech Stack

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- psycopg2
- Pydantic
- Docker
- Anthropic Claude API
- Voyage AI
- pgvector
- AWS ECR
- AWS RDS
- AWS ECS/Fargate
- AWS IAM
- AWS Secrets Manager
- AWS CloudWatch

## Project Architecture

### Local Development

```text
Client / Swagger UI
        ↓
FastAPI
        ↓
SQLAlchemy
        ↓
psycopg2
        ↓
PostgreSQL
```
### RAG Architecture

The application also supports Retrieval-Augmented Generation (RAG) for question answering across stored clinical documents.

#### Document Indexing

When a new document is created, the document is first stored in PostgreSQL and then indexed for RAG.

```text
POST /documents
      ↓
Store document in PostgreSQL
      ↓
Split document into overlapping chunks
      ↓
Generate document embeddings with Voyage AI
      ↓
Store chunks + embeddings
      ↓
PostgreSQL + pgvector
```

Each chunk is linked to its original document using `document_id`. The embeddings are stored as 1024-dimensional pgvector vectors.

#### Question Answering

When a user asks a question:

```text
POST /rag/ask
      ↓
User question
      ↓
Generate query embedding with Voyage AI
      ↓
Cosine-distance search with pgvector
      ↓
Retrieve most relevant document chunks
      ↓
Join chunks with parent document metadata
      ↓
Build retrieved context
      ↓
Send context + question to Claude
      ↓
Return grounded answer
```
Claude is instructed to answer only from the retrieved clinical document context and to indicate when the available context does not contain enough information.

The RAG functionality is currently implemented and tested locally and has not yet been deployed to AWS.

### AWS Architecture

```text
                         Amazon ECR
                             │
                       Docker image
                             │
                             ▼
Client / Swagger ──► ECS / Fargate
                             │
                             ▼
                     FastAPI Container
                       │           │
                       │           │
                       ▼           ▼
                  SQLAlchemy    Anthropic
                       │        Claude API
                       ▼           ▲
                   psycopg2        │
                       │      API key injected
                       ▼           │
                PostgreSQL RDS     │
                                   │
                         AWS Secrets Manager

FastAPI container logs
         │
         ▼
   AWS CloudWatch


The application is deployed on AWS using Amazon ECS with AWS Fargate.
The Docker image is stored in Amazon ECR and executed as an ECS task using AWS Fargate. The FastAPI application connects to PostgreSQL hosted on Amazon RDS using SQLAlchemy and psycopg2.

Clinical documents can also be analyzed through the Anthropic Claude API. The Anthropic API key is stored in AWS Secrets Manager and securely injected into the ECS container at runtime. Application logs are sent to AWS CloudWatch.

## API Endpoints

The API supports storing, retrieving, deleting, analyzing, and semantically searching clinical documents.

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET | `/health` | Health check |
| POST | `/documents` | Create and index a document |
| GET | `/documents` | Get all documents |
| GET | `/documents/{id}` | Get a document by ID |
| DELETE | `/documents/{id}` | Delete a document |
| POST | `/documents/{id}/analyze` | Analyze a specific clinical document using Claude |
| POST | `/rag/ask` | Ask questions across indexed documents using RAG |

## Document Model

A clinical document could be:
- a lab report — blood test results, cholesterol levels, etc.
- a doctor's note — symptoms, diagnosis, treatment notes
- a discharge summary — what happened during a hospital stay
- a radiology report — written results from an X-ray, MRI, CT scan
- a prescription/medication record
A clinical document contains:

```json
{
  "patient_id": "patient-001",
  "document_type": "lab-report",
  "content": "Clinical document content"
}
```
A stored document also contains an automatically generated ID.

Example:

```json
{
  "id": 1,
  "patient_id": "patient-001",
  "document_type": "lab-report",
  "content": "Clinical document content"
}
```

## AI Document Analysis

The API supports AI-powered analysis of stored clinical documents using the Anthropic Claude API.

Request flow:

POST /documents/{id}/analyze
        ↓
FastAPI
        ↓
Retrieve document from PostgreSQL RDS
        ↓
Send document content to Claude
        ↓
Generate clinical summary
        ↓
Return analysis as JSON
Example:
{
  "document_id": 4,
  "analysis": "Clinical summary generated from the stored document."
}

## RAG Question Answering

The API also supports question answering across indexed clinical documents using Retrieval-Augmented Generation (RAG).

Unlike `/documents/{id}/analyze`, the user does not need to know which document contains the answer. The application searches the indexed document chunks for relevant context before calling Claude.

Example request:

```json
{
  "question": "Which patient reported persistent headaches?"
}
```

The application:

1. Generates an embedding for the question using Voyage AI.
2. Uses pgvector cosine-distance search to retrieve the most relevant document chunks.
3. Joins the chunks with their parent documents to retrieve metadata such as patient ID and document type.
4. Provides the retrieved context and question to Claude.
5. Instructs Claude to answer only from the retrieved context.

Example response:

```json
{
  "question": "Which patient reported persistent headaches?",
  "answer": "According to the clinical document context, Patient P3001 reported persistent headaches for the past three days."
}
```

If the retrieved context does not contain enough information, Claude is instructed to state that the available context is insufficient rather than inventing missing clinical details.

## Database

The application uses PostgreSQL as its relational database.

SQLAlchemy is used as the ORM layer, and psycopg2 is used as the PostgreSQL database driver.

```text
FastAPI
   ↓
SQLAlchemy
   ↓
psycopg2
   ↓
PostgreSQL
```

The database connection is supplied through the `DATABASE_URL` environment variable.

Example format:

```text
postgresql://<username>:<password>@<host>:5432/<database_name>
```

For AWS RDS connections, SSL can be required:

```text
postgresql://<username>:<password>@<rds-endpoint>:5432/<database_name>?sslmode=require
```

Real database credentials should never be committed to GitHub.

## Local Setup

### 1. Create a virtual environment

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the database

Set a PostgreSQL connection string using `DATABASE_URL`.

Example:

```bash
export DATABASE_URL="postgresql://<username>:<password>@localhost:5432/clinical_document_db"
```

### 4. Run the FastAPI application

```bash
fastapi dev app/main.py
```

Swagger documentation will be available at:

```text
http://localhost:8000/docs
```

### 5. Add a Secrets Manager section

This is important enough to document because it's something you can discuss in interviews.

```markdown
## AWS Secrets Manager

The Anthropic API key is not hard-coded in the application or Docker image.

The key is stored in AWS Secrets Manager and referenced by the ECS task definition.
AWS Secrets Manager
        ↓
ECS Task Execution Role
        ↓
ECS/Fargate Task
        ↓
ANTHROPIC_API_KEY environment variable
        ↓
FastAPI / Anthropic SDK

### 6. Add CloudWatch

Your old Future Work says *“Add logging and monitoring with CloudWatch”*, but you've now done that. :chatgpt-content-reference{index="5"}

Add:

```markdown
## AWS CloudWatch

The ECS container sends application logs to AWS CloudWatch.

CloudWatch logs were used to diagnose deployment issues including:

- container startup failures
- PostgreSQL driver configuration errors
- Anthropic API authentication errors

This allows application failures to be investigated without direct access to the running container.

## Docker

### Build the Docker image

```bash
docker build -t clinical-document-api .
```

### Run the container

```bash
docker run -p 8000:8000 \
  -e DATABASE_URL="<DATABASE_URL>" \
  clinical-document-api
```

Port mapping:

```text
Mac port 8000
      ↓
Container port 8000
      ↓
FastAPI
```

Swagger documentation is available at:

```text
http://localhost:8000/docs
```

## AWS Setup

### IAM

An IAM development user is used for normal AWS development instead of the AWS root user.

IAM controls:

```text
Who can access AWS
        +
What they are allowed to do
```

The development user has permissions required for:

* Amazon ECR
* Amazon ECS
* Amazon RDS
* Required security group operations

The AWS root user is protected with MFA and is not used for normal project work.

## AWS CLI

The AWS CLI is used to manage AWS resources from the terminal.

Verify the configured identity:

```bash
aws sts get-caller-identity --profile clinical-api-dev
```

The returned ARN should correspond to the IAM user rather than the AWS root account.

## Amazon ECR

Amazon Elastic Container Registry stores the Docker image in AWS.

### Create the ECR repository

```bash
aws ecr create-repository \
  --repository-name clinical-document-api \
  --region us-east-1 \
  --profile clinical-api-dev
```

### Authenticate Docker to ECR

```bash
aws ecr get-login-password \
  --region us-east-1 \
  --profile clinical-api-dev \
| docker login \
  --username AWS \
  --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
```

### Tag the local Docker image

```bash
docker tag clinical-document-api:latest \
<AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/clinical-document-api:latest
```

### Push the image to ECR

```bash
docker push \
<AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/clinical-document-api:latest
```

The Docker image is now stored in AWS ECR.

```text
Local Docker image
        ↓
docker tag
        ↓
docker push
        ↓
Amazon ECR
```

## Amazon RDS

Amazon RDS is used to run PostgreSQL in AWS.

The project uses a small development configuration:

```text
Engine: PostgreSQL
Deployment: Single-AZ
Instance class: db.t4g.micro
Storage: General Purpose SSD
Allocated storage: 20 GiB
```

A PostgreSQL database named:

```text
clinical_document_db
```

is used by the application.

## Security group

A Security Group is essentially a network firewall controlling permitted traffic.

ECS/Fargate Security Group: controls who can reach your FastAPI container. We allowed your current public IP to reach port 8000.
RDS Security Group: controls who can reach PostgreSQL. We allowed the ECS security group to reach port 5432.

## RDS Security Group

A dedicated security group controls access to PostgreSQL on port 5432.

For development, two types of access may be configured:

1. My current public IP (`/32`)
   - Allows direct PostgreSQL access from my development machine.

2. ECS task security group
   - Allows the FastAPI container running on Fargate to connect to RDS.

The application does not require RDS to be open to `0.0.0.0/0`.

The `/32` rule allows direct PostgreSQL connections from only my current public IP address. Separately, the ECS task security group allows the FastAPI container running on Fargate to connect to RDS.
The `/32` CIDR rule represents one specific public IP address.

If My Public IP Changes
My public IP address can change over time, for example after switching Wi-Fi networks, restarting the router, or because of changes made by the internet service provider.
If my public IP changes, the RDS security group may still contain the old IP address. In that case, connections to PostgreSQL can fail with a timeout.
To update access:
Open the AWS Console.
Go to EC2 → Security Groups.
Open clinical-document-db-sg.
Go to Inbound rules → Edit inbound rules.
Find the PostgreSQL rule for port 5432.
Change the source to My IP.
Save the rule.

AWS will replace the old IP with my current public IP.
This is safer than using 0.0.0.0/0, because 0.0.0.0/0 would allow any IPv4 address on the internet to attempt to connect to the database.

## Connecting to RDS with psql

Example:

```bash
psql \
  -h <RDS_ENDPOINT> \
  -p 5432 \
  -U postgres \
  -d clinical_document_db
```

A successful connection results in a PostgreSQL prompt similar to:

```text
clinical_document_db=>
```

## Running Docker Against AWS RDS

The same Docker image can be run with an RDS database by supplying a different `DATABASE_URL`.

```bash
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql://postgres:<PASSWORD>@<RDS_ENDPOINT>:5432/clinical_document_db?sslmode=require" \
  clinical-document-api
```

This demonstrates that the Docker image does not need to be rebuilt just because the database location changes.

```text
Same Docker image
      ↓
Different DATABASE_URL
      ↓
Different PostgreSQL server
```

The current working flow is:

```text
Browser / Swagger
        ↓
FastAPI in Docker
        ↓
SQLAlchemy
        ↓
psycopg2
        ↓
AWS RDS PostgreSQL
```

## Testing the API

Open:

```text
http://localhost:8000/docs
```

Use Swagger UI to test the endpoints.

Example `POST /documents` request:

```json
{
  "patient_id": "patient-001",
  "document_type": "lab-report",
  "content": "Test document stored in AWS RDS"
}
```

Then use:

```text
GET /documents
```

to verify that the saved document can be retrieved.

The database can also be checked directly with:

```sql
SELECT * FROM documents;
```

## Project Progress

### Day 1 — FastAPI CRUD

Completed:

* Created FastAPI application
* Added health endpoint
* Added document CRUD endpoints
* Added Pydantic request/response models
* Tested endpoints using Swagger UI

### Day 2 — PostgreSQL and Docker

Completed:

* Installed PostgreSQL
* Created local PostgreSQL database
* Added SQLAlchemy ORM
* Added psycopg2 PostgreSQL driver
* Added database sessions
* Replaced in-memory storage with PostgreSQL
* Dockerized the FastAPI application
* Connected Docker container to PostgreSQL on the Mac
* Verified database persistence

### Day 3 — AWS ECR and RDS

Completed:

* Created AWS account
* Configured AWS Region `us-east-1`
* Enabled MFA on the root account
* Created IAM development user
* Installed and configured AWS CLI
* Created Amazon ECR repository
* Authenticated Docker with ECR
* Tagged and pushed Docker image to ECR
* Created Amazon RDS PostgreSQL instance
* Configured RDS security group
* Connected to RDS using `psql`
* Created `clinical_document_db`
* Connected the local Dockerized FastAPI application to AWS RDS
* Verified the application can store and retrieve data from RDS

### Day 4 — ECS/Fargate Deployment

Completed:

* Created an ECS cluster
* Created an ECS task definition for the FastAPI container
* Configured the task to use the Docker image stored in ECR
* Configured Fargate with 0.25 vCPU and 512 MiB memory
* Configured container port 8000
* Configured the `DATABASE_URL` environment variable for RDS
* Configured VPC networking and security groups
* Allowed the ECS/Fargate task to connect to RDS on PostgreSQL port 5432
* Launched the container using AWS Fargate
* Assigned a public IP to the Fargate task
* Accessed FastAPI Swagger UI through the Fargate public IP
* Verified `GET /documents` returns HTTP 200 from the deployed API

### Day 5 — Claude API and AWS Secrets Manager

Completed:

- Integrated the Anthropic Claude API
- Added `POST /documents/{id}/analyze`
- Retrieved stored documents from PostgreSQL before analysis
- Added AWS Secrets Manager for Anthropic API credentials
- Configured IAM permissions for ECS secret retrieval
- Injected `ANTHROPIC_API_KEY` into the Fargate container
- Added CloudWatch logging for the ECS task
- Diagnosed and fixed a PostgreSQL driver mismatch between local and Docker environments
- Explicitly configured SQLAlchemy to use psycopg2
- Fixed ECS Secrets Manager JSON-key extraction
- Deployed ECS task definition Revision 3
- Successfully tested end-to-end document analysis through Swagger UI

### Day 6 — Retrieval-Augmented Generation (RAG)

Completed locally:

- Added pgvector support to PostgreSQL
- Added a `document_chunks` table for storing document chunks and embeddings
- Implemented overlapping character-based document chunking
- Integrated Voyage AI for document and query embeddings
- Automatically index newly created documents for RAG
- Store 1024-dimensional embeddings using pgvector
- Implemented cosine-distance vector search for semantic retrieval
- Joined retrieved chunks with parent documents to include metadata
- Added `POST /rag/ask` for question answering across indexed documents
- Integrated retrieved context with Claude for grounded responses
- Added handling for RAG indexing failures
- Added handling for an empty RAG index
- Configured cascade deletion so deleting a document also removes its indexed chunks
- Tested automatic indexing, semantic retrieval, grounded question answering, missing-information behavior, and cascade deletion

The RAG implementation is currently working locally. AWS deployment of the RAG-enabled version is the next step.

## Security Notes

Do not commit any of the following to GitHub:

```text
AWS access keys
AWS secret access keys
AWS temporary tokens
RDS passwords
real DATABASE_URL values containing passwords
.env files containing secrets
```

Use environment variables or AWS-managed secret storage for sensitive configuration.

## Future Work

- Deploy the RAG-enabled application to AWS
- Manage AWS infrastructure using Terraform
- Add an Application Load Balancer and HTTPS
- Move database credentials to AWS Secrets Manager
- Add authentication and authorization
- Add database migrations
- Add automated tests
- Add CI/CD
- Add production-grade error handling and retry logic for external API calls

## Troubleshooting

### Swagger UI times out

If the ECS/Fargate task shows `RUNNING` but:

http://<FARGATE_PUBLIC_IP>:8000/docs

times out, check the ECS task security group's inbound rule.

AWS Console:
EC2 → Security Groups → ECS task security group → Inbound rules

The rule should be:

- Type: Custom TCP
- Port: 8000
- Source: My IP

If my public IP has changed:
1. Click "Edit inbound rules"
2. Find the port 8000 rule
3. Change Source to "My IP"
4. Save rules
5. Reload Swagger

Reason: `/32` allows only one specific public IP address. My public IP can change, so an old `/32` rule can block access even while the Fargate task is running.