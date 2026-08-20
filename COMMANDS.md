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

FastAPI: A Python web framework used to build REST APIs. It maps HTTP requests to Python functions, validates request data, and converts Python responses into JSON.

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