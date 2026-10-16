# Python environment of the project. Same Python version as the dev machine.
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first so Docker can reuse this layer
# when only the code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# The code is not copied into the image: docker-compose mounts the project
# folder at /app, so edits on Windows show up in the container immediately
# (and .env never ends up inside an image).
