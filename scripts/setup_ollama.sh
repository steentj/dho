#!/bin/bash

# Script to set up Ollama with the nomic-embed-text model
# This script should be run after docker-compose is up

# Constants
CONTAINER_NAME="dho-ollama"
MODEL_NAME="nomic-embed-text"
MAX_RETRIES=5
RETRY_DELAY=10

echo "Setting up Ollama with $MODEL_NAME model..."

# Function to check if Ollama container is healthy
check_health() {
    docker exec $CONTAINER_NAME curl -sf "http://localhost:11434/api/health" > /dev/null 2>&1
    return $?
}

# Wait for Ollama to be healthy
echo "Waiting for Ollama service to be healthy..."
retries=0
while [ $retries -lt $MAX_RETRIES ]; do
    if check_health; then
        echo "Ollama service is healthy!"
        break
    fi
    echo "Waiting for Ollama to be ready... (attempt $((retries + 1))/$MAX_RETRIES)"
    sleep $RETRY_DELAY
    retries=$((retries + 1))
done

if [ $retries -eq $MAX_RETRIES ]; then
    echo "Error: Ollama service did not become healthy in time"
    exit 1
fi

# Pull the model
echo "Pulling $MODEL_NAME model..."
docker exec $CONTAINER_NAME ollama pull $MODEL_NAME

if [ $? -eq 0 ]; then
    echo "✅ Successfully pulled $MODEL_NAME model"
    echo "Ollama setup complete!"
else
    echo "❌ Failed to pull $MODEL_NAME model"
    exit 1
fi
