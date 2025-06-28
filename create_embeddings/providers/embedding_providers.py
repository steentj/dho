"""
Embedding provider implementations.
"""

import os
import json
from abc import ABC, abstractmethod
from typing import List
from openai import AsyncOpenAI
import httpx


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""
    
    @abstractmethod
    async def get_embedding(self, chunk: str) -> list:
        """
        Generate embedding for a text chunk.
        
        Args:
            chunk: Text to generate embedding for
            
        Returns:
            List of floats representing the embedding vector
        """
        pass


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider implementation."""
    
    def __init__(self, api_key: str, model: str = None):
        """
        Initialize OpenAI embedding provider.
        
        Args:
            api_key: OpenAI API key
            model: Model to use (defaults to OPENAI_MODEL env var or text-embedding-3-small)
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model or os.getenv("OPENAI_MODEL", "text-embedding-3-small")

    async def get_embedding(self, chunk: str) -> list:
        """
        Generate embedding using OpenAI API.
        
        Args:
            chunk: Text to generate embedding for
            
        Returns:
            List of floats representing the embedding vector
        """
        response = await self.client.embeddings.create(input=chunk, model=self.model)
        return response.data[0].embedding


class DummyEmbeddingProvider(EmbeddingProvider):
    """Dummy embedding provider that returns fixed embedding vectors for testing."""

    async def get_embedding(self, chunk: str) -> List[float]:
        """Get dummy embedding vector.
        
        Args:
            chunk: Text to generate embedding for (not used)
            
        Returns:
            List of floats representing the embedding vector
        """
        # Generate deterministic dummy embeddings with 1536 dimensions
        return [float(i)/10000 for i in range(1536)]


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Ollama embedding provider for local models."""
    
    def __init__(self, base_url: str = None, model: str = None):
        """
        Initialize Ollama embedding provider.
        
        Args:
            base_url: Ollama server URL (defaults to OLLAMA_BASE_URL env var or http://ollama:11434)
            model: Model name (defaults to OLLAMA_MODEL env var or nomic-embed-text)
        """
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")).rstrip('/')
        self.model = model or os.getenv("OLLAMA_MODEL", "nomic-embed-text")
        self.client = httpx.AsyncClient(timeout=30.0)

    async def get_embedding(self, chunk: str) -> List[float]:
        """
        Generate embedding using Ollama API.
        
        Args:
            chunk: Text to generate embedding for
            
        Returns:
            List of floats representing the embedding vector
            
        Raises:
            RuntimeError: If the Ollama API request fails
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": chunk
                }
            )
            response.raise_for_status()
            result = await response.json()
            return result["embedding"]
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Ollama embedding request failed: HTTP error: {e}")
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            raise RuntimeError(f"Ollama embedding request failed: JSON error: {e}")
        except Exception as e:
            raise RuntimeError(f"Ollama embedding request failed: {e}")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close HTTP client."""
        await self.client.aclose()
