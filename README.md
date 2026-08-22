# Clinical Document API

A backend API for storing and managing clinical documents.

This project was built to practice backend development with Python, FastAPI, PostgreSQL, SQLAlchemy, Docker, AWS, and Terraform.

## Tech Stack

* Python
* FastAPI
* PostgreSQL
* SQLAlchemy
* psycopg2
* Pydantic
* Docker
* AWS ECR
* AWS RDS
* AWS ECS/Fargate
* Terraform

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

### AWS Architecture

```text
Docker image
    ↓
Amazon ECR
    ↓
Amazon ECS
    ↓
AWS Fargate
    ↓
FastAPI container
    ↓
Amazon RDS PostgreSQL
```

At the current stage of the project, the Docker image is stored in ECR and the application can connect successfully from a local Docker container to PostgreSQL running in Amazon RDS.

ECS/Fargate deployment is the next step.

## API Endpoints

The API supports CRUD operations for clinical documents.

| Method | Endpoint          | Description          |
| ------ | ----------------- | -------------------- |
| GET    | `/health`         | Health check         |
| POST   | `/documents`      | Create a document    |
| GET    | `/documents`      | Get all documents    |
| GET    | `/documents/{id}` | Get a document by ID |
| PUT    | `/documents/{id}` | Update a document    |
| DELETE | `/documents/{id}` | Delete a document    |

## Document Model

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

## RDS Security Group

A dedicated security group controls access to PostgreSQL.

The PostgreSQL inbound rule uses:

```text
Protocol: TCP
Port: 5432
Source: My IP
```

This means PostgreSQL connections are only allowed from the configured public IP address.

Port `5432` is the default PostgreSQL server port.

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

## Next Step — Day 4

Deploy the FastAPI container completely into AWS using:

```text
Amazon ECR
     ↓
Amazon ECS
     ↓
AWS Fargate
     ↓
FastAPI container
     ↓
Amazon RDS PostgreSQL
```

After this step, FastAPI will no longer need to run on the local Mac.

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

* Deploy API using ECS and Fargate
* Add Terraform infrastructure
* Improve secret management
* Add production networking
* Add logging and monitoring with CloudWatch
* Add authentication and authorization
* Add database migrations
* Add automated tests
* Add CI/CD

## RDS Security Group

A dedicated security group controls access to PostgreSQL.
The PostgreSQL inbound rule uses:

```text
Protocol: TCP
Port: 5432
Source: My IP

This means PostgreSQL connections are allowed only from my current public IP address.
The security group stores that IP as a /32 CIDR rule, which represents one specific IP address.
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
