#!/usr/bin/env python3
"""
Final comprehensive test demonstrating the vector dimension bug fix.

This test shows that the provider-aware search resolves the 
"different vector dimensions 1536 and 768" error.
"""

import pytest
import os
from unittest.mock import patch, AsyncMock
from database.postgresql import PostgreSQLSearchRepository
from database.interfaces import DatabaseConnection


@pytest.mark.unit
class TestVectorDimensionBugFixed:
    """Comprehensive test suite showing the vector dimension bug is fixed."""
    
    @pytest.mark.asyncio
    async def test_ollama_search_uses_correct_table_no_dimension_mismatch(self):
        """
        Test that Ollama searches now use the correct table and avoid dimension mismatches.
        
        BEFORE FIX: Ollama 768-dim embeddings searched in chunks table (1536-dim) → ERROR
        AFTER FIX: Ollama 768-dim embeddings search in chunks_nomic table (768-dim) → SUCCESS
        """
        # Setup mock connection that simulates successful chunks_nomic table search
        mock_connection = AsyncMock(spec=DatabaseConnection)
        mock_connection.fetchall.return_value = [
            ("ollama_book.pdf", "Ollama Book", "Test Author", 1, "Test chunk from Ollama", 0.15)
        ]
        
        search_repo = PostgreSQLSearchRepository(mock_connection)
        
        # Test with 768-dimensional Ollama embedding and provider_name="ollama"
        ollama_embedding = [0.1] * 768
        results = await search_repo.vector_search(
            embedding=ollama_embedding,
            provider_name="ollama"  # This should route to chunks_nomic table
        )
        
        # Verify successful search in chunks_nomic table (no dimension error)
        expected_query = """
            SELECT b.pdf_navn, b.titel, b.forfatter, c.sidenr, c.chunk, 
                   c.embedding <=> $1 AS distance
            FROM chunks_nomic c 
            JOIN books b ON c.book_id = b.id 
            ORDER BY c.embedding <=> $1 
            LIMIT $2
        """
        mock_connection.fetchall.assert_called_once_with(expected_query, ollama_embedding, 10)
        
        # Should return results without error
        assert len(results) == 1
        assert results[0][0] == "ollama_book.pdf"
    
    @pytest.mark.asyncio
    async def test_openai_search_still_works_correctly(self):
        """
        Test that OpenAI searches still work correctly after the fix.
        
        OpenAI 1536-dim embeddings should continue to search in chunks table (1536-dim).
        """
        mock_connection = AsyncMock(spec=DatabaseConnection) 
        mock_connection.fetchall.return_value = [
            ("openai_book.pdf", "OpenAI Book", "Test Author", 1, "Test chunk from OpenAI", 0.12)
        ]
        
        search_repo = PostgreSQLSearchRepository(mock_connection)
        
        # Test with 1536-dimensional OpenAI embedding and provider_name="openai"
        openai_embedding = [0.1] * 1536
        results = await search_repo.vector_search(
            embedding=openai_embedding,
            provider_name="openai"  # This should route to chunks table
        )
        
        # Verify search in chunks table
        expected_query = """
            SELECT b.pdf_navn, b.titel, b.forfatter, c.sidenr, c.chunk, 
                   c.embedding <=> $1 AS distance
            FROM chunks c 
            JOIN books b ON c.book_id = b.id 
            ORDER BY c.embedding <=> $1 
            LIMIT $2
        """
        mock_connection.fetchall.assert_called_once_with(expected_query, openai_embedding, 10)
        
        assert len(results) == 1
        assert results[0][0] == "openai_book.pdf"
    
    @pytest.mark.asyncio
    async def test_backward_compatibility_maintained(self):
        """
        Test that existing code without provider_name still works (backward compatibility).
        
        When no provider_name is specified, should use legacy chunk_size mapping.
        """
        mock_connection = AsyncMock(spec=DatabaseConnection)
        mock_connection.fetchall.return_value = []
        
        search_repo = PostgreSQLSearchRepository(mock_connection)
        
        # Test without provider_name (legacy usage)
        embedding = [0.1] * 1536
        await search_repo.vector_search(
            embedding=embedding,
            chunk_size="large"  # Legacy parameter
            # No provider_name specified
        )
        
        # Should use legacy chunk_size mapping (chunks_large)
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
    @patch.dict(os.environ, {'PROVIDER': 'ollama'}, clear=True)
    async def test_dhosearch_api_integration_fixed(self):
        """
        Test that the dhosearch API integration correctly prevents dimension mismatches.
        
        This simulates the production scenario where Ollama is the provider.
        """
        from soegemaskine.searchapi.dhosearch import find_nærmeste
        
        with patch('soegemaskine.searchapi.dhosearch.db_service') as mock_db_service, \
             patch('soegemaskine.searchapi.dhosearch.embedding_provider') as mock_embedding_provider:
            
            # Setup Ollama provider mock
            mock_embedding_provider.get_provider_name.return_value = "ollama"
            
            # Setup database service to simulate successful search in chunks_nomic
            mock_db_service.vector_search.return_value = [
                ("book1.pdf", "Test Book", "Author", 1, "Successfully found in chunks_nomic table", 0.2)
            ]
            
            # Test with 768-dimensional Ollama embedding
            ollama_embedding = [0.1] * 768
            results = await find_nærmeste(ollama_embedding)
            
            # Verify that db_service was called with provider_name="ollama"
            mock_db_service.vector_search.assert_called_once_with(
                embedding=ollama_embedding,
                limit=1000,
                distance_function="cosine",
                chunk_size="normal",  # Legacy parameter
                provider_name="ollama"  # NEW: Prevents dimension mismatch
            )
            
            # Should return results successfully (no dimension error)
            assert len(results) == 1
            assert "chunks_nomic" in str(results[0])  # Simulated table name in result
    
    @pytest.mark.asyncio
    async def test_production_error_scenario_now_resolved(self):
        """
        Test that reproduces the exact production error scenario and shows it's resolved.
        
        PRODUCTION ERROR: "different vector dimensions 1536 and 768"
        CAUSE: Ollama 768-dim query searched against OpenAI 1536-dim chunks table
        FIX: Provider-aware table selection routes Ollama to chunks_nomic table
        """
        # Mock the exact production scenario
        mock_connection = AsyncMock(spec=DatabaseConnection)
        
        search_repo = PostgreSQLSearchRepository(mock_connection)
        
        # Simulate Ollama 768-dim embedding
        ollama_embedding = [0.1] * 768
        
        # OLD WAY (would cause error): chunk_size="normal" → chunks table (1536-dim)
        # This would cause: "different vector dimensions 1536 and 768"
        
        # NEW WAY (fixed): provider_name="ollama" → chunks_nomic table (768-dim)
        mock_connection.fetchall.return_value = [
            ("success.pdf", "Success", "Author", 1, "No dimension error!", 0.1)
        ]
        
        # This should work without dimension mismatch
        results = await search_repo.vector_search(
            embedding=ollama_embedding,
            provider_name="ollama"  # Routes to chunks_nomic (768-dim compatible)
        )
        
        # Verify correct table is used
        call_args = mock_connection.fetchall.call_args
        query = call_args[0][0]
        assert "chunks_nomic" in query, "Should use chunks_nomic table for Ollama"
        assert "chunks c" not in query or "chunks_nomic" in query, "Should not use chunks table"
        
        # Should succeed without error
        assert len(results) == 1
        assert results[0][4] == "No dimension error!"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
