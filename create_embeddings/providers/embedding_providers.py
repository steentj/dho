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
    
    @abstractmethod
    async def has_embeddings_for_book(self, book_id: int, db_service) -> bool:
        """
        Check if embeddings already exist for a book with this provider.
        
        Args:
            book_id: The database ID of the book
            db_service: Database service for checking embeddings
            
        Returns:
            True if embeddings exist, False otherwise
        """
        pass
    
    @abstractmethod
    def get_table_name(self) -> str:
        """
        Get the database table name used by this provider.
        
        Returns:
            Table name for storing embeddings
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the name/identifier of this provider.
        
        Returns:
            Provider name for logging and identification
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
    
    async def has_embeddings_for_book(self, book_id: int, db_service) -> bool:
        """
        Check if OpenAI embeddings already exist for a book.
        
        Args:
            book_id: The database ID of the book
            db_service: Database service for checking embeddings
            
        Returns:
            True if embeddings exist in chunks table, False otherwise
        """
        try:
            # Check if chunks exist for this book in the OpenAI table
            query = "SELECT COUNT(*) as count FROM chunks WHERE book_id = $1"
            result = await db_service.execute_query(query, [book_id])
            count = result[0]['count'] if result else 0
            return count > 0
        except Exception:
            # If there's any error checking, assume no embeddings exist
            return False
    
    def get_table_name(self) -> str:
        """Get the database table name for OpenAI embeddings."""
        return "chunks"
    
    def get_provider_name(self) -> str:
        """Get the provider name for OpenAI."""
        return "openai"


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
    
    async def has_embeddings_for_book(self, book_id: int, db_service) -> bool:
        """
        Check if dummy embeddings already exist for a book.
        
        Args:
            book_id: The database ID of the book
            db_service: Database service for checking embeddings
            
        Returns:
            True if embeddings exist in chunks table, False otherwise
        """
        try:
            # Check if chunks exist for this book in the chunks table
            query = "SELECT COUNT(*) as count FROM chunks WHERE book_id = $1"
            result = await db_service.execute_query(query, [book_id])
            count = result[0]['count'] if result else 0
            return count > 0
        except Exception:
            # If there's any error checking, assume no embeddings exist
            return False
    
    def get_table_name(self) -> str:
        """Get the database table name for dummy embeddings."""
        return "chunks"  # Use same table as OpenAI for testing
    
    def get_provider_name(self) -> str:
        """Get the provider name for dummy provider."""
        return "dummy"


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
    
    async def has_embeddings_for_book(self, book_id: int, db_service) -> bool:
        """
        Check if Ollama embeddings already exist for a book.
        
        Args:
            book_id: The database ID of the book
            db_service: Database service for checking embeddings
            
        Returns:
            True if embeddings exist in chunks_nomic table, False otherwise
        """
        try:
            # Check if chunks exist for this book in the Ollama table
            query = "SELECT COUNT(*) as count FROM chunks_nomic WHERE book_id = $1"
            result = await db_service.execute_query(query, [book_id])
            count = result[0]['count'] if result else 0
            return count > 0
        except Exception:
            # If there's any error checking (e.g., table doesn't exist), assume no embeddings
            return False
    
    def get_table_name(self) -> str:
        """Get the database table name for Ollama embeddings."""
        return "chunks_nomic"
    
    def get_provider_name(self) -> str:
        """Get the provider name for Ollama."""
        return "ollama"

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close HTTP client."""
        await self.client.aclose()
