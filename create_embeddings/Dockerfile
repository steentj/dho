FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for PyMuPDF and network debugging tools
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    iputils-ping \
    dnsutils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY create_embeddings/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire create_embeddings package structure
COPY create_embeddings/__init__.py ./create_embeddings/
COPY create_embeddings/opret_bøger.py ./create_embeddings/
COPY create_embeddings/book_processor_wrapper.py ./create_embeddings/
COPY create_embeddings/logging_config.py ./create_embeddings/
COPY create_embeddings/chunking.py ./create_embeddings/
COPY create_embeddings/providers/ ./create_embeddings/providers/

# Copy the database module for dependency injection
COPY database/ ./database/

# Copy the main wrapper script to app root for easy execution
COPY create_embeddings/book_processor_wrapper.py .

# Create directories
RUN mkdir -p /app/input /app/output /app/failed

# Set up non-root user
RUN useradd -m -u 1000 bookuser && chown -R bookuser:bookuser /app
USER bookuser

ENTRYPOINT ["python", "book_processor_wrapper.py"]
