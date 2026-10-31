# Clinical Document API

A backend API for storing, analyzing, and semantically searching **synthetic** clinical documents. It exposes a REST interface built with FastAPI and PostgreSQL, adds retrieval-augmented generation (RAG) with Voyage AI embeddings and pgvector, and uses Anthropic Claude for document analysis, grounded question answering, and a tool-calling agent.

The service runs as a container on AWS ECS Fargate with an RDS PostgreSQL database, secrets in AWS Secrets Manager, and logs in CloudWatch. A small Terraform configuration provisions a separate development ECR repository and log group. A stdio MCP server exposes the same document tools to local MCP clients.

> **Synthetic data only.** This is a portfolio/learning project. Do not store real patient information in it.

## Tech Stack

| Area | Technology |
| --- | --- |
| Language / API | Python 3.12, FastAPI, Pydantic |
| Database | PostgreSQL, SQLAlchemy (ORM), psycopg2, pgvector |
| AI | Voyage AI (`voyage-4` embeddings), Anthropic Claude (`claude-haiku-4-5`) |
| Containers | Docker (deployed as `linux/arm64`) |
| AWS | ECS Fargate, ECR, RDS PostgreSQL, Secrets Manager, CloudWatch, IAM |
| Infrastructure as code | Terraform (AWS provider 5.x) |
| Tooling | MCP Python SDK (stdio server) |

## Architecture

```mermaid
flowchart LR
    client["Client / Swagger UI"] -->|HTTP :8000| api

    subgraph aws["AWS (us-east-1)"]
        ecr[("ECR<br/>container image")] -.->|image pull| api
        sm["Secrets Manager<br/>DATABASE_URL, ANTHROPIC_API_KEY,<br/>VOYAGE_API_KEY"] -.->|injected at start| api
        api["FastAPI container<br/>ECS Fargate"] -->|logs| cw["CloudWatch Logs"]
        api -->|SQLAlchemy / psycopg2| rds[("RDS PostgreSQL<br/>documents + document_chunks<br/>pgvector")]
    end

    api -->|embeddings| voyage["Voyage AI"]
    api -->|analyze, RAG answer,<br/>agent tool loop| claude["Anthropic Claude"]

    mcpclient["Local MCP client"] -->|stdio| mcp["MCP server<br/>(local only)"]
    mcp --> rds
    mcp --> voyage
```

**Request flows**

- **Indexing:** `POST /documents` saves the document, splits it into 500-character chunks (100-character overlap), embeds each chunk with Voyage AI, and stores the vectors in the `document_chunks` table (`vector(1024)`).
- **RAG:** `POST /rag/ask` embeds the question, runs a cosine-distance search with pgvector, joins the top 3 chunks to their parent documents, and asks Claude to answer **only** from that context.
- **Agent:** `POST /agent/chat` runs a Claude tool loop with two tools, `get_document` and `search_documents`, and returns a structured response.
- **MCP:** `app/mcp_server.py` is a separate stdio process that reuses the same two tool functions. It is not part of the HTTP API and is not deployed.

## Features

- **Document CRUD:** create, list, fetch, and delete documents; deleting a document cascades to its chunks.
- **AI analysis:** `POST /documents/{id}/analyze` summarizes a stored document with Claude, with a prompt that restricts it to stated facts.
- **Embeddings and semantic search:** automatic indexing on create, pgvector cosine search.
- **RAG question answering:** grounded answers, with an explicit "insufficient information" path.
- **Agent tool calling:** Claude chooses between fetching a document by ID and searching by meaning; output is validated against a Pydantic schema (`document_id`, `patient_id`, `document_type`, `answer`).
- **Upstream error handling:** Claude and Voyage failures return `503` (temporary: rate limits, timeouts, 5xx) or `502` (other API errors) with generic messages, and only the exception type is logged.
- **MCP server:** exposes `get_document` and `search_documents` over stdio; tool `print` output is redirected to stderr so it cannot corrupt the protocol stream.

## API Endpoints

| Method | Endpoint | Description | Success |
| --- | --- | --- | --- |
| GET | `/health` | Liveness check | `200` |
| POST | `/documents` | Create a document and index it for RAG | `201` |
| GET | `/documents` | List all documents | `200` |
| GET | `/documents/{id}` | Get one document | `200` / `404` |
| DELETE | `/documents/{id}` | Delete a document and its chunks | `200` / `404` |
| POST | `/documents/{id}/analyze` | Summarize a document with Claude | `200` / `404` |
| POST | `/rag/ask` | Answer a question using retrieved chunks | `200` / `404` |
| POST | `/agent/chat` | Tool-calling agent over the documents | `200` |

Interactive docs are served at `/docs`. The error semantics are:

- `POST /documents` returns `503` if the document was saved but Voyage indexing failed.
- `/rag/ask` returns `404` when no indexed documents exist.
- The Claude-backed routes (`analyze`, `rag/ask`, `agent/chat`) return `502` or `503` on upstream errors.

**Create a document**

```bash
curl -X POST http://localhost:8000/documents \
  -H "Content-Type: application/json" \
  -d '{"patient_id": "SYNTH-001", "document_type": "discharge_summary",
       "content": "Synthetic note: admitted with pneumonia, treated with azithromycin for 5 days."}'
```

```json
{"id": 1, "patient_id": "SYNTH-001", "document_type": "discharge_summary",
 "content": "Synthetic note: admitted with pneumonia, treated with azithromycin for 5 days."}
```

**Ask a question (RAG)**

```bash
curl -X POST http://localhost:8000/rag/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What antibiotic was used and for how long?"}'
```

```json
{"question": "What antibiotic was used and for how long?",
 "answer": "The patient was treated with azithromycin for 5 days."}
```

**Agent**

```bash
curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the document type and patient ID of document 1?"}'
```

```json
{"document_id": 1, "patient_id": "SYNTH-001", "document_type": "discharge_summary",
 "answer": "Document 1 is a discharge_summary for patient SYNTH-001."}
```

`POST /documents/{id}/analyze` returns `{"document_id": 1, "analysis": "<summary>"}`.

## Local Development

**Prerequisites:** Python 3.12, PostgreSQL with the [pgvector](https://github.com/pgvector/pgvector) extension available, and API keys for Anthropic and Voyage AI.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create the database and enable the extension. This is a one-time step, because the app creates tables on startup but does not create extensions:

```bash
createdb clinical_document_db
psql clinical_document_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

Configure environment variables (a git-ignored `.env` file works; it is loaded with `python-dotenv`):

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy connection string, e.g. `postgresql://user:password@localhost:5432/clinical_document_db` (use `?sslmode=require` for RDS). Defaults to a local database if unset. |
| `ANTHROPIC_API_KEY` | Claude access |
| `VOYAGE_API_KEY` | Voyage AI embeddings |

Run the API:

```bash
fastapi dev app/main.py        # http://localhost:8000/docs
```

Tables (`documents`, `document_chunks`) are created automatically on startup.

**Optional: MCP server**

```bash
pip install -r requirements-mcp.txt
python -m app.mcp_server       # stdio transport; register this command in an MCP client
```

## Docker

```bash
docker build -t clinical-document-api .

docker run -p 8000:8000 \
  -e DATABASE_URL="<database-url>" \
  -e ANTHROPIC_API_KEY="<anthropic-key>" \
  -e VOYAGE_API_KEY="<voyage-key>" \
  clinical-document-api
```

The image is based on `python:3.12-slim` and starts `fastapi run app/main.py --port 8000`. `.env` is excluded from the build context by `.dockerignore`. The ECS task runs on ARM64, so build with `--platform linux/arm64` for deployment. Dependencies in `requirements.txt` are pinned to exact versions.

## AWS Deployment

The API runs on **ECS Fargate** (ARM64, 0.25 vCPU, 512 MB) in `us-east-1`, as a single-task ECS service in the default VPC with a public IP and no load balancer.

| Component | Role |
| --- | --- |
| ECR | Stores the container image, tagged with the Git commit SHA |
| ECS task definition | Container on port 8000, a Python-based `/health` check, logs to CloudWatch |
| RDS PostgreSQL | Single-AZ `db.t4g.micro`, 20 GiB, with the `vector` extension enabled |
| Secrets Manager | `DATABASE_URL`, `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY` injected into the task as environment variables by the task execution role |
| CloudWatch Logs | Container stdout/stderr, including agent tool-call log lines |
| Security groups | A dedicated ECS group allows inbound port 8000 from a single IP address; the RDS group allows port 5432 from the ECS group |

Deployment flow: build the ARM64 image, push it to ECR with the commit SHA, register a task definition revision that references the new tag, and update the service.

## Terraform

The `terraform/` directory holds a deliberately small configuration (`versions.tf`, `variables.tf`, `main.tf`, `outputs.tf`; the provider lock file is committed). It authenticates through the AWS CLI profile or environment, with no credentials in code, and uses local state that is git-ignored.

**Terraform-managed**

- A separate **development ECR repository** (image scanning on push).
- A separate **development CloudWatch log group** (14-day retention).

Both are tagged `ManagedBy=terraform`. They are not currently used by the running service.

**Created manually (not managed by Terraform)**

- ECS cluster, service, and task definitions
- The production ECR repository and its image tags
- RDS instance, subnet/network configuration, and security groups
- Secrets Manager secrets and IAM roles/policies

Importing the manually created resources into Terraform is future work.

## Testing and Current Status

There is **no automated test suite** (unit, integration, or CI) in the repository. Everything below was verified manually with synthetic data.

| Area | Implemented | Verified |
| --- | --- | --- |
| Document CRUD, health check | Yes | Locally and on the deployed service (`/health`, `GET /documents`, `POST /documents`) |
| `/documents/{id}/analyze` | Yes | On the deployed service |
| Embedding and automatic indexing | Yes | On the deployed service (`POST /documents` returned `201`); existing documents backfilled through a one-off ECS task |
| `/rag/ask` | Yes | On the deployed service: two answerable questions and one unanswerable question (correctly declined) |
| `/agent/chat` | Yes | On the deployed service: `get_document` calls, a `search_documents` then `get_document` chain, and an unanswerable question (correctly declined); tool calls confirmed in CloudWatch logs |
| 502/503 upstream error handling | Yes | Locally, using invalid keys and a stubbed Claude endpoint |
| Docker image | Yes | Built for `linux/arm64`; container startup and endpoints exercised locally and on ECS |
| MCP server | Yes | Locally over stdio with a real MCP client against a throwaway database: tool discovery, `get_document`, not-found handling, `search_documents`. Not deployed. |
| Terraform | Yes | `fmt`, `validate`, `plan`, and `apply` completed for the two resources; a subsequent plan showed no changes |

## Security and Limitations

**Security measures**

- Synthetic data only; no real patient data should ever be stored.
- API keys and the database URL are held in Secrets Manager and injected at runtime. They are not in the image or the repository, and `.env`, Terraform state, and `*.tfvars` are git-ignored.
- Access uses an IAM user with limited permissions rather than the root account.
- Inbound access to the API is limited to one IP address, and the database accepts connections only from approved sources.
- Claude prompts instruct the model to use only provided context and to say when information is missing; client-facing errors never include upstream error details.

**Limitations**

- **Development-grade deployment:** plain HTTP, a single task, no load balancer, and a public IP that changes whenever the task restarts.
- **No authentication or authorization** on the API.
- **No HTTPS** and no custom domain.
- **Outbound traffic** from the ECS security group is currently unrestricted.
- **The RDS instance is publicly accessible** (restricted by security group) rather than private-only.
- **Schema management** uses `create_all` on startup; there are no migrations, and the `vector` extension must be enabled manually.
- **Retrieval is basic:** fixed-size character chunking, top-3 results, and no vector index or re-ranking.
- **The agent's structured output** always includes document fields, so it fits questions about a specific document better than open-ended ones.
- **Terraform state is local**, and most infrastructure is not yet under Terraform.
- **No CI/CD or automated tests.**

## Future Work

- Application Load Balancer with HTTPS
- Authentication and authorization
- Database migrations (e.g. Alembic) and a private RDS instance
- Automated tests and CI/CD
- Remote Terraform state and importing existing infrastructure
