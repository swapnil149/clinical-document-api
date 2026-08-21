# Start with a lightweight environment containing Python 3.12. 
# Create /app as the working directory. 
# Copy my dependency list into it and install those dependencies.
# Copy my FastAPI source code into the image. 
# When a container starts, run the FastAPI server on port 8000.

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
# pip is Python’s package installer. It lets you install Python libraries/packages that your project needs.
# --no-cache-dir tells pip not to keep downloaded package caches afterward.

COPY ./app ./app
# Notice why you get /app/app. The first /app comes from: WORKDIR /app and the second app is your actual Python package directory.

CMD ["fastapi", "run", "app/main.py", "--port", "8000"]