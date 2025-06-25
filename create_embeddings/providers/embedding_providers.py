"""
Embedding provider implementations.
"""

import os
from abc import ABC, abstractmethod
from openai import AsyncOpenAI


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
    """Dummy embedding provider for testing."""
    
    async def get_embedding(self, chunk: str) -> list:
        """
        Generate dummy embedding for testing.
        
        Args:
            chunk: Text to generate embedding for (unused)
            
        Returns:
            List of 1536 dummy float values
        """
        return [i / 10000 for i in range(1536)]
