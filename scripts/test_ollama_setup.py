#!/usr/bin/env python3
"""Test script to verify Ollama setup and model functionality."""
import asyncio
import httpx
import os
import sys
import time
from typing import Dict, Any

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "nomic-embed-text")
MAX_RETRIES = 10
RETRY_DELAY = 5

async def check_ollama_health() -> bool:
    """Check if Ollama service is healthy."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.head(OLLAMA_URL)
            return response.status_code == 200
    except httpx.RequestError:
        return False

async def pull_model() -> bool:
    """Pull the nomic-embed-text model."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/pull",
                json={"name": MODEL_NAME}
            )
            return response.status_code == 200
    except httpx.RequestError as e:
        print(f"Error pulling model: {e}")
        return False

async def test_embedding() -> Dict[str, Any]:
    """Test model by generating an embedding for a sample text."""
    test_text = "This is a test of the embedding model."
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/embeddings",
                json={
                    "model": MODEL_NAME,
                    "prompt": test_text
                }
            )
            return response.json()
    except httpx.RequestError as e:
        print(f"Error generating embedding: {e}")
        return {}

async def main():
    """Main execution function."""
    print("Starting Ollama setup test...")
    
    # Wait for Ollama to be healthy
    for i in range(MAX_RETRIES):
        if await check_ollama_health():
            print("✓ Ollama service is healthy")
            break
        print(f"Waiting for Ollama service to be ready (attempt {i+1}/{MAX_RETRIES})...")
        time.sleep(RETRY_DELAY)
    else:
        print("✗ Ollama service is not responding")
        sys.exit(1)

    # Pull model
    print(f"\nPulling {MODEL_NAME} model...")
    if await pull_model():
        print(f"✓ Successfully pulled {MODEL_NAME} model")
    else:
        print(f"✗ Failed to pull {MODEL_NAME} model")
        sys.exit(1)

    # Test embedding generation
    print("\nTesting embedding generation...")
    result = await test_embedding()
    if result and 'embedding' in result:
        print("✓ Successfully generated test embedding")
        print(f"Embedding dimension: {len(result['embedding'])}")
    else:
        print("✗ Failed to generate test embedding")
        sys.exit(1)

    print("\n✓ All tests passed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
