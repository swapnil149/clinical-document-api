# COMMANDS.md

A running reference for the terminal commands used while building the **Clinical Document API** project.

The goal of this file is not just to list commands, but to explain what each part of a command means.

---

## Project Navigation

### `cd ~`

```bash
cd ~
```

**Meaning:** Move to your home directory.

- `cd` = change directory
- `~` = your current user's home directory

On this Mac, that is typically:

```text
/Users/swapnil
```

---

### `mkdir -p Projects`

```bash
mkdir -p Projects
```

**Meaning:** Create a directory named `Projects`.

- `mkdir` = make directory
- `-p` = create the directory if needed and do not error if it already exists
- `Projects` = directory name

---

### `cd Projects`

```bash
cd Projects
```

**Meaning:** Move into the `Projects` directory.

---

### `mkdir clinical-document-api`

```bash
mkdir clinical-document-api
```

**Meaning:** Create the project directory.

---

### `cd clinical-document-api`

```bash
cd clinical-document-api
```

**Meaning:** Move into the project directory.

---

### `code .`

```bash
code .
```

**Meaning:** Open the current directory in Visual Studio Code.

- `code` = VS Code command-line launcher
- `.` = current directory

So this means:

> Open this folder in VS Code.

---

## Python Commands

### `python3 --version`

```bash
python3 --version
```

**Meaning:** Display the installed Python 3 version.

- `python3` = run Python 3
- `--version` = print the version instead of starting Python

Example output:

```text
Python 3.13.5
```

---

## Python Virtual Environment

### `python3 -m venv .venv`

```bash
python3 -m venv .venv
```

**Meaning:** Create an isolated Python environment for this project.

Breaking it down:

### `python3`

Runs Python 3.

### `-m`

`-m` means:

> Run a Python module as a program.

Instead of asking Python to execute a `.py` file, we are asking it to locate and execute a module.

For example:

```bash
python3 -m venv
```

means:

> Python, run your built-in `venv` module.

### `venv`

`venv` is Python's built-in module for creating virtual environments.

### `.venv`

This is the name of the directory where the virtual environment will be created.

The leading `.` makes the folder hidden by default on macOS/Linux.

After running the command, the project looks roughly like:

```text
clinical-document-api/
└── .venv/
```

### Why use a virtual environment?

It keeps this project's Python packages separate from:

- system Python packages
- other Python projects
- other versions of the same dependency

Conceptually:

```text
Project A
└── .venv
    └── FastAPI version A

Project B
└── .venv
    └── FastAPI version B
```

---

### `source .venv/bin/activate`

```bash
source .venv/bin/activate
```

**Meaning:** Activate the project's virtual environment.

Breaking it down:

### `source`

Runs a shell script inside the **current terminal session**.

This matters because activating a virtual environment needs to modify environment variables in your current shell.

### `.venv/bin/activate`

This is the activation script created by Python when the virtual environment was created.

After activation, the prompt should usually begin with:

```text
(.venv)
```

For example:

```text
(.venv) swapnil@MacBook clinical-document-api %
```

This tells you that commands such as:

```bash
python
pip
```

will use the versions inside this project's `.venv`.

---

## Installing Python Packages

### `pip install "fastapi[standard]"`

```bash
pip install "fastapi[standard]"
```

**Meaning:** Install FastAPI and its standard development dependencies into the active virtual environment.

Breaking it down:

### `pip`

Python package installer.

It plays a similar role to:

```text
npm
```

in the JavaScript ecosystem.

### `install`

Tells `pip` that we want to install a package.

### `"fastapi[standard]"`

Installs FastAPI along with its standard optional dependencies.

The quotes protect the square brackets from being interpreted by the shell.

Because `.venv` is activated, FastAPI is installed inside:

```text
clinical-document-api/.venv/
```

rather than globally on the computer.

---

## Creating Project Files

### `mkdir app`

```bash
mkdir app
```

**Meaning:** Create the `app` directory that will contain the backend application code.

Result:

```text
clinical-document-api/
├── .venv/
└── app/
```

---

### `touch app/__init__.py`

```bash
touch app/__init__.py
```

**Meaning:** Create an empty file named `__init__.py` inside the `app` directory.

### `touch`

Creates an empty file if the file does not already exist.

If it does exist, `touch` updates its timestamp without deleting its contents.

### Why `__init__.py`?

It tells Python that the directory can be treated as a Python package.

---

### `touch app/main.py`

```bash
touch app/main.py
```

**Meaning:** Create the main Python file for our FastAPI application.

This will contain code such as:

```python
from fastapi import FastAPI

app = FastAPI()
```

---

## Running FastAPI

### `fastapi dev app/main.py`

```bash
fastapi dev app/main.py
```

**Meaning:** Start the FastAPI application in development mode.

Breaking it down:

### `fastapi`

Runs the FastAPI command-line interface.

### `dev`

Starts a development server.

Development mode is useful because it automatically reloads the server when application code changes.

### `app/main.py`

Tells FastAPI where our application code is located.

The path means:

```text
app/
└── main.py
```

When running locally, the server normally becomes available at:

```text
http://127.0.0.1:8000
```

---

## Useful Local URLs

### Health endpoint

```text
http://127.0.0.1:8000/health
```

Used to confirm that the application is running.

Expected response:

```json
{
  "status": "healthy"
}
```

---

### Swagger / API Documentation

```text
http://127.0.0.1:8000/docs
```

FastAPI automatically creates an interactive interface where API endpoints can be viewed and tested.

---

## Command Cheat Sheet

```bash
# Go to home directory
cd ~

# Create development projects folder
mkdir -p Projects

# Enter it
cd Projects

# Create project
mkdir clinical-document-api

# Enter project
cd clinical-document-api

# Open current directory in VS Code
code .

# Check Python version
python3 --version

# Create Python virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install FastAPI
pip install "fastapi[standard]"

# Create application directory
mkdir app

# Create Python package file
touch app/__init__.py

# Create FastAPI entry file
touch app/main.py

# Start FastAPI development server
fastapi dev app/main.py
```

---

## How This File Will Be Used

As new commands are introduced during the project, add them here with:

1. The command
2. What the command does
3. What each important flag or argument means
4. Why the command is needed in this project

Future sections will include commands for:

- Git
- Docker
- PostgreSQL
- AWS CLI
- Amazon ECR
- Amazon ECS
- Terraform
- testing
- CI/CD

### `python3 -m venv .venv`

```bash
python3 -m venv .venv
Meaning:
Python 3, run the built-in venv module and create the virtual environment inside the .venv folder.
Breaking it down:
python3 → runs Python 3
-m → tells Python to run a module as a program
venv → Python's built-in virtual environment module
.venv → the folder where the virtual environment will be created

### `source .venv/bin/activate`

```bash
source .venv/bin/activate
Meaning:
Run the virtual environment's activation script in the current terminal session.

An API is a way for one software program to communicate with another software program. API stands for Application Programming Interface. It's a' defined interface that allows different software applications to communicate by sending requests and receiving responses. In your project, the browser/Swagger is one program, and your FastAPI backend is another. They communicate through API endpoints like: POST /documents, GET /documents, GET /documents/1

FastAPI: A Python web framework used to build REST APIs. It maps HTTP requests to Python functions, validates request data, and converts Python responses into JSON.
FastAPI is a Python tool that turns your Python functions into web/API endpoints like the functions below the decorator.

Web framework: A library/framework that provides the structure and tools needed to build web applications or APIs, such as handling HTTP requests, routing URLs to functions, validating data, and generating responses.

touch <filename>: Creates an empty file if it does not already exist. If the file already exists, it updates the file timestamp without deleting its contents.

__init__.py: A special Python file used to mark a directory as a Python package, allowing modules inside that directory to be imported using package-style imports such as from app.models import Document, where app is the directory and models is the module name.

@app.get("/health"): A FastAPI route decorator. It registers the function below it as the handler for HTTP GET requests to /health.

Command-line tool (CLI): A program that is operated by typing commands in a terminal instead of using buttons or menus. Ex - python3 --version, where python3 is a Command-line program, fastapi dev app/main.py where fastapi is a Command-line program.

fastapi dev app/main.py: Starts the FastAPI application defined in app/main.py using the development server. Development mode automatically reloads the server when application code changes.

127.0.0.1 is the loopback IP address that refers to the current computer. When FastAPI runs locally, it acts as the server address for requests coming from the same machine.

Port: A numbered communication endpoint on a computer. The IP address identifies the machine, while the port identifies which application or service on that machine should receive the network request.

http://127.0.0.1:8000: The local address of the FastAPI development server. 127.0.0.1 refers to the current computer, and 8000 is the port on which the application is listening.

Swagger UI: An interactive web interface for viewing and testing API endpoints. FastAPI automatically generates it at /docs using the application's OpenAPI schema. One small distinction: Swagger UI is the interface, while OpenAPI is the API specification format underneath it.'

OpenAPI schema: A standardized machine-readable description of an API, including its endpoints, methods, request bodies, response formats, and validation rules. FastAPI generates it automatically, and Swagger UI uses it to build interactive API documentation.

psql client: The PostgreSQL command-line interface used to connect to a PostgreSQL server and run SQL commands against databases.
A useful analogy is:
Chrome → client for websites
psql   → client for PostgreSQL databases
The PostgreSQL server is the actual service storing the data; psql is just one way to interact with it.

ORM (Object-Relational Mapping): A technique that maps database tables to programming-language classes and rows to objects, allowing application code to interact with the database using objects instead of writing raw SQL for every operation.
Object-Relational Mapping:
Object → Python object/class
Relational → relational database like PostgreSQL
Mapping → connects the Python object to a database table
One important point: an ORM does not eliminate SQL underneath. SQLAlchemy still ultimately sends SQL to PostgreSQL; it just gives you a higher-level Python interface.

SQLAlchemy: Python database toolkit/ORM used to interact with relational databases.

psycopg2: A Python PostgreSQL database driver. It allows Python applications and libraries like SQLAlchemy to establish connections to PostgreSQL and send database commands.

SQLAlchemy = how I work with the database.
psycopg2 = how Python physically talks to PostgreSQL.

Factory: An object/function configured to create other objects. SessionLocal is a session factory; every call to SessionLocal() creates a new SQLAlchemy database session using the same configuration.

SQLAlchemy's Base and Pydantic's BaseModel serve different purposes:
BaseModel (from Pydantic):
- Used for API request/response schemas
- Validates and parses data coming into or going out of FastAPI
- Example: class DocumentCreate(BaseModel)
Base (created using SQLAlchemy's declarative_base()):'
- Used for database ORM models
- Tells SQLAlchemy that the class maps to a database table
- Example: class Document(Base)
So:
BaseModel -> API/data validation
Base      -> database table mapping

Docker: A platform for packaging applications and their dependencies into images and running those images as isolated containers

Docker image: A packaged blueprint containing the application, runtime, dependencies, and configuration needed to run it.

Docker container: A running instance of a Docker image.

pip: is Python’s package installer. It lets you install Python libraries/packages that your project needs.

pip freeze: lists the currently installed Python packages and their exact versions. Redirecting that output to requirements.txt creates a dependency file that another environment, such as Docker, can use to install the same packages.

Detached mode (-d) runs a Docker container in the background and immediately returns control of the terminal to the user.

AWS (Amazon Web Services) — A cloud platform that provides computing, storage, databases, networking, and other IT services over the internet.
Mental image: “Rent IT infrastructure from Amazon instead of owning servers.”

EC2 (Elastic Compute Cloud) — A virtual computer/server that you rent and run in AWS.
Mental image: “A computer in the cloud that I manage.”

ECR (Elastic Container Registry) — An AWS service used to store and manage Docker/container images.
Mental image: “A warehouse for Docker images.”

ECR repository = a storage location in AWS ECR where one or more versions/tags of a Docker image are stored.

ECR repository URI = the address AWS gives to an ECR repository. Docker uses this address when pushing or pulling images.

ECS (Elastic Container Service) — An AWS service that manages and runs containers.
Mental image: “The manager that tells containers when and how to run.”

Fargate — A serverless compute option for ECS that runs your containers without you managing EC2 servers.
Mental image: “AWS gives my container the CPU/RAM it needs; I don’t manage the machine.” You mainly provide Fargate with:
- your Docker image
- CPU/RAM requirements
- networking/configuration

RDS (Relational Database Service) — An AWS service for running managed relational databases such as PostgreSQL or MySQL.
Mental image: “PostgreSQL in AWS, with AWS managing much of the database server.”

AWS Region — A geographic area where AWS has data centers and where your AWS resources are created.
Example: us-east-1 = Northern Virginia.
Mental image: “The physical part of the world where my AWS resources live.”

S3 — Simple Storage Service is an Object/file storage in AWS. You can store things like images, PDFs, backups, logs, or uploaded documents. Mental image: “A giant cloud folder/bucket.”
In a more advanced version of your clinical-document project, actual document files could be stored in S3 while metadata stays in PostgreSQL.

CloudWatch - AWS’s monitoring and logging service. It collects things like application logs, errors, CPU usage, and alarms.
Mental image: “AWS dashboard + logbook for watching what my application is doing.”
Later, your ECS/Fargate FastAPI logs can appear in CloudWatch.

IAM — Identity and Access Management - Controls who can access AWS and what they are allowed to do.
Mental image: “AWS security guard + permission system.”

AWS CLI — A command-line tool used to create, configure, and manage AWS resources from a terminal.

AWS CLI profile = a named local configuration that tells the AWS CLI which AWS identity/credentials and region to use.
# Verify which AWS identity the CLI is currently using? Expected ARN should end with: user/clinical-api-dev
(.venv) swapnil@Animeshs-MacBook-Air clinical-document-api % aws sts get-caller-identity --profile clinical-api-dev
{
    "UserId": "AIDA3OVBPKOL65NYVITUL",
    "Account": "787391402903",
    "Arn": "arn:aws:iam::787391402903:user/clinical-api-dev"
}

Image digest = a unique hash that identifies the exact contents of a Docker image.

Docker tag = gives an existing Docker image another name, usually including the registry address where it will be pushed.
Docker tag did not duplicate the 374 MB image. It just added another name pointing to it.

Docker image tag = a label used to identify a particular version of an image. It usually comes after a colon.
So when we pushed: .../clinical-document-api:latest, the latest part is just the tag.

Pager = a terminal viewer that shows long command output one screen at a time.

Port mapping = connects a port on the host machine to a port inside a Docker container so the application inside the container can be accessed from outside it.

Persistence = data continues to exist after the operation that created it is finished.
