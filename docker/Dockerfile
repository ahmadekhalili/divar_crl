FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy fastapi_app requirements and install
COPY ../fastapi_app/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy fastapi_app
COPY ../fastapi_app ./fastapi_app

# Copy divar_crl module
COPY ../divar_crl ./divar_crl

# Copy central_logging.py
COPY ../central_logging.py ./

# Expose port
EXPOSE 8001
