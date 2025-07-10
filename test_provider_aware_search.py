#!/usr/bin/env python3
"""
Test that the provider-aware search repository works correctly.

This test verifies that the updated PostgreSQLSearchRepository correctly
selects tables based on the provider_name parameter.
"""

import pytest
from unittest.mock import AsyncMock
from database.postgresql import PostgreSQLSearchRepository
from database.interfaces import DatabaseConnection


@pytest.mark.unit
class TestProviderAwareSearch:
    """Test suite for provider-aware search functionality."""
    
    @pytest.fixture
    def mock_connection(self):
        """Create a mock database connection."""
        return AsyncMock(spec=DatabaseConnection)
    
    @pytest.fixture
    def search_repository(self, mock_connection):
        """Create a search repository with mocked connection."""
        return PostgreSQLSearchRepository(mock_connection)
    
    @pytest.mark.asyncio
    async def test_ollama_provider_uses_chunks_nomic_table(self, search_repository, mock_connection):
        """Test that Ollama provider uses chunks_nomic table."""
        embedding = [0.1] * 768  # 768-dimensional Ollama embedding
        mock_connection.fetchall.return_value = []
        
        await search_repository.vector_search(
            embedding=embedding,
            provider_name="ollama"
        )
        
        # Verify it uses chunks_nomic table
        expected_query = """
            SELECT b.pdf_navn, b.titel, b.forfatter, c.sidenr, c.chunk, 
                   c.embedding <=> $1 AS distance
            FROM chunks_nomic c 
            JOIN books b ON c.book_id = b.id 
            ORDER BY c.embedding <=> $1 
            LIMIT $2
        """
        mock_connection.fetchall.assert_called_once_with(expected_query, embedding, 10)
    
    @pytest.mark.asyncio
    async def test_openai_provider_uses_chunks_table(self, search_repository, mock_connection):
        """Test that OpenAI provider uses chunks table."""
        embedding = [0.1] * 1536  # 1536-dimensional OpenAI embedding
        mock_connection.fetchall.return_value = []
        
        await search_repository.vector_search(
            embedding=embedding,
            provider_name="openai"
        )
        
        # Verify it uses chunks table
        expected_query = """
            SELECT b.pdf_navn, b.titel, b.forfatter, c.sidenr, c.chunk, 
                   c.embedding <=> $1 AS distance
            FROM chunks c 
            JOIN books b ON c.book_id = b.id 
            ORDER BY c.embedding <=> $1 
            LIMIT $2
        """
        mock_connection.fetchall.assert_called_once_with(expected_query, embedding, 10)
    
    @pytest.mark.asyncio
    async def test_dummy_provider_uses_chunks_table(self, search_repository, mock_connection):
        """Test that dummy provider uses chunks table."""
        embedding = [0.1] * 1536  # 1536-dimensional dummy embedding
        mock_connection.fetchall.return_value = []
        
        await search_repository.vector_search(
            embedding=embedding,
            provider_name="dummy"
        )
        
        # Verify it uses chunks table (same as OpenAI)
        expected_query = """
            SELECT b.pdf_navn, b.titel, b.forfatter, c.sidenr, c.chunk, 
                   c.embedding <=> $1 AS distance
            FROM chunks c 
            JOIN books b ON c.book_id = b.id 
            ORDER BY c.embedding <=> $1 
            LIMIT $2
        """
        mock_connection.fetchall.assert_called_once_with(expected_query, embedding, 10)
    
    @pytest.mark.asyncio
    async def test_unknown_provider_defaults_to_chunks_table(self, search_repository, mock_connection):
        """Test that unknown provider defaults to chunks table."""
        embedding = [0.1] * 512  # Some other dimension
        mock_connection.fetchall.return_value = []
        
        await search_repository.vector_search(
            embedding=embedding,
            provider_name="unknown_provider"
        )
        
        # Verify it defaults to chunks table
        expected_query = """
            SELECT b.pdf_navn, b.titel, b.forfatter, c.sidenr, c.chunk, 
                   c.embedding <=> $1 AS distance
            FROM chunks c 
            JOIN books b ON c.book_id = b.id 
            ORDER BY c.embedding <=> $1 
            LIMIT $2
        """
        mock_connection.fetchall.assert_called_once_with(expected_query, embedding, 10)
    
    @pytest.mark.asyncio
    async def test_backward_compatibility_no_provider_uses_chunk_size(self, search_repository, mock_connection):
        """Test backward compatibility - when no provider specified, use chunk_size mapping."""
        embedding = [0.1] * 1536
        mock_connection.fetchall.return_value = []
        
        # Test with different chunk sizes to ensure backward compatibility
        await search_repository.vector_search(
            embedding=embedding,
            chunk_size="large"  # No provider_name specified
        )
        
        # Verify it uses chunks_large table (legacy behavior)
        expected_query = """
            SELECT b.pdf_navn, b.titel, b.forfatter, c.sidenr, c.chunk, 
                   c.embedding <=> $1 AS distance
            FROM chunks_large c 
            JOIN books b ON c.book_id = b.id 
            ORDER BY c.embedding <=> $1 
            LIMIT $2
        """
        mock_connection.fetchall.assert_called_once_with(expected_query, embedding, 10)
    
    @pytest.mark.asyncio
    async def test_provider_overrides_chunk_size(self, search_repository, mock_connection):
        """Test that provider_name overrides chunk_size when both are specified."""
        embedding = [0.1] * 768
        mock_connection.fetchall.return_value = []
        
        # Provider should override chunk_size
        await search_repository.vector_search(
            embedding=embedding,
            chunk_size="large",  # This should be ignored
            provider_name="ollama"  # This should take precedence
        )
        
        # Verify it uses chunks_nomic (from provider) not chunks_large (from chunk_size)
        expected_query = """
            SELECT b.pdf_navn, b.titel, b.forfatter, c.sidenr, c.chunk, 
                   c.embedding <=> $1 AS distance
            FROM chunks_nomic c 
            JOIN books b ON c.book_id = b.id 
            ORDER BY c.embedding <=> $1 
            LIMIT $2
        """
        mock_connection.fetchall.assert_called_once_with(expected_query, embedding, 10)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
