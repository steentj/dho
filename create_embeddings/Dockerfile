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
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the EXISTING opret_bøger.py and our wrapper
COPY opret_bøger.py .
COPY book_processor_wrapper.py .
COPY logging_config.py .

# Create directories
RUN mkdir -p /app/input /app/output /app/failed

# Set up non-root user
RUN useradd -m -u 1000 bookuser && chown -R bookuser:bookuser /app
USER bookuser

ENTRYPOINT ["python", "book_processor_wrapper.py"]
