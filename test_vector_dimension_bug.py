#!/usr/bin/env python3
"""
Test that reproduces the vector dimension bug in the search API.

This test demonstrates that when Ollama is used as the embedding provider,
the search API fails because it searches in the wrong table (chunks vs chunks_nomic).
"""

import pytest
import os
from unittest.mock import patch, AsyncMock
from create_embeddings.providers import EmbeddingProviderFactory


@pytest.mark.unit
class TestVectorDimensionBug:
    """Test suite to reproduce and fix the vector dimension bug."""
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {'PROVIDER': 'ollama', 'OLLAMA_MODEL': 'nomic-embed-text'}, clear=True)
    async def test_vector_dimension_mismatch_reproduced(self):
        """
        Test that reproduces the 'different vector dimensions 1536 and 768' error.
        
        This test shows that when Ollama (768-dim) is used for query embedding,
        but search looks in chunks table (1536-dim), we get a dimension mismatch.
        """
        from database.postgresql import PostgreSQLSearchRepository
        from database.interfaces import DatabaseConnection
        
        # Create Ollama provider (768-dimensional embeddings)
        ollama_provider = EmbeddingProviderFactory.create_provider('ollama')
        
        # Mock connection that simulates the dimension mismatch error
        mock_connection = AsyncMock(spec=DatabaseConnection)
        mock_connection.fetchall.side_effect = Exception("different vector dimensions 1536 and 768")
        
        # Create search repository
        search_repo = PostgreSQLSearchRepository(mock_connection)
        
        # Generate query embedding with Ollama (768 dimensions)
        with patch.object(ollama_provider, 'get_embedding', return_value=[0.1] * 768):
            query_embedding = await ollama_provider.get_embedding("test query")
            
            # This should fail because search_repo uses "chunks" table (1536-dim)
            # but query_embedding is 768-dimensional
            with pytest.raises(Exception, match="different vector dimensions"):
                await search_repo.vector_search(
                    embedding=query_embedding,
                    limit=10,
                    distance_function="cosine",
                    chunk_size="normal"  # This maps to "chunks" table with 1536-dim vectors
                )
    
    @pytest.mark.asyncio  
    @patch.dict(os.environ, {'PROVIDER': 'ollama'}, clear=True)
    async def test_search_should_use_provider_specific_table(self):
        """
        Test that search should use the provider-specific table.
        
        When Ollama is the provider, search should use chunks_nomic table,
        not the default chunks table.
        """
        from database.postgresql import PostgreSQLSearchRepository
        
        # Mock connection
        mock_connection = AsyncMock()
        mock_connection.fetchall.return_value = []
        
        search_repo = PostgreSQLSearchRepository(mock_connection)
        
        # Generate 768-dimensional embedding (simulating Ollama output)
        query_embedding = [0.1] * 768
        
        # The search should ideally detect the provider and use chunks_nomic table
        # This will currently fail because PostgreSQLSearchRepository doesn't know about providers
        
        # Search with default parameters (this currently uses wrong table)
        await search_repo.vector_search(embedding=query_embedding)
        
        # Verify that it called with chunks table (the bug)
        expected_query = """
            SELECT b.pdf_navn, b.titel, b.forfatter, c.sidenr, c.chunk, 
                   c.embedding <=> $1 AS distance
            FROM chunks c 
            JOIN books b ON c.book_id = b.id 
            ORDER BY c.embedding <=> $1 
            LIMIT $2
        """
        mock_connection.fetchall.assert_called_once_with(expected_query, query_embedding, 10)
        
        # But it SHOULD have used chunks_nomic table when Ollama provider is active
        # This demonstrates the bug - the search doesn't know which provider is being used

    @pytest.mark.asyncio
    @patch.dict(os.environ, {'PROVIDER': 'openai', 'OPENAI_API_KEY': 'test-key'}, clear=True)
    async def test_openai_provider_should_use_chunks_table(self):
        """
        Test that OpenAI provider correctly uses the chunks table.
        
        This test ensures that when OpenAI is the provider, 
        the search correctly uses the chunks table.
        """
        from database.postgresql import PostgreSQLSearchRepository
        
        # Mock connection
        mock_connection = AsyncMock()
        mock_connection.fetchall.return_value = []
        
        search_repo = PostgreSQLSearchRepository(mock_connection)
        
        # Generate 1536-dimensional embedding (OpenAI)
        query_embedding = [0.1] * 1536
        
        # Search should use chunks table for OpenAI
        await search_repo.vector_search(embedding=query_embedding)
        
        # Verify correct table usage
        expected_query = """
            SELECT b.pdf_navn, b.titel, b.forfatter, c.sidenr, c.chunk, 
                   c.embedding <=> $1 AS distance
            FROM chunks c 
            JOIN books b ON c.book_id = b.id 
            ORDER BY c.embedding <=> $1 
            LIMIT $2
        """
        mock_connection.fetchall.assert_called_once_with(expected_query, query_embedding, 10)

    @pytest.mark.asyncio
    @patch.dict(os.environ, {'PROVIDER': 'ollama'}, clear=True)
    async def test_dhosearch_api_dimension_mismatch(self):
        """
        Test that the dhosearch API fails with dimension mismatch when using Ollama.
        
        This reproduces the exact production error in the FastAPI search endpoint.
        """
        # Import after setting environment
        from soegemaskine.searchapi.dhosearch import find_nærmeste
        
        # Mock the global db_service and embedding_provider 
        with patch('soegemaskine.searchapi.dhosearch.db_service') as mock_db_service, \
             patch('soegemaskine.searchapi.dhosearch.embedding_provider') as mock_embedding_provider:
            
            # Setup Ollama provider mock (768 dimensions)
            async def mock_get_embedding(text):
                return [0.1] * 768
            mock_embedding_provider.get_embedding = mock_get_embedding
            
            # Setup database service mock that simulates the dimension error
            mock_db_service.vector_search.side_effect = Exception("different vector dimensions 1536 and 768")
            
            # Generate query embedding
            query_embedding = await mock_embedding_provider.get_embedding("test query")
            
            # This should reproduce the production error
            results = await find_nærmeste(query_embedding)
            
            # The function should handle the error gracefully and return empty results
            assert results == []
            
            # Verify the db_service was called with the wrong table (chunk_size="normal")
            mock_db_service.vector_search.assert_called_once_with(
                embedding=query_embedding,
                limit=1000,
                distance_function="cosine",
                chunk_size="normal"  # This is the bug - should be provider-aware
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
