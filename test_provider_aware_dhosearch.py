#!/usr/bin/env python3
"""
Test that the updated dhosearch.py correctly uses provider-aware search.

This test verifies that the search API now correctly selects the right table
based on the active embedding provider.
"""

import pytest
import os
from unittest.mock import patch


@pytest.mark.unit
class TestProviderAwareSearchAPI:
    """Test suite for provider-aware search API."""
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {'PROVIDER': 'ollama'}, clear=True)
    async def test_dhosearch_uses_ollama_provider_table(self):
        """Test that dhosearch uses chunks_nomic table when Ollama is the provider."""
        # Import after setting environment
        from soegemaskine.searchapi.dhosearch import find_nærmeste
        
        # Mock the global services
        with patch('soegemaskine.searchapi.dhosearch.db_service') as mock_db_service, \
             patch('soegemaskine.searchapi.dhosearch.embedding_provider') as mock_embedding_provider:
            
            # Setup Ollama provider mock
            mock_embedding_provider.get_provider_name.return_value = "ollama"
            
            # Setup database service mock
            mock_db_service.vector_search.return_value = []
            
            # Test the search function
            query_embedding = [0.1] * 768  # 768-dimensional Ollama embedding
            results = await find_nærmeste(query_embedding)
            
            # Verify correct parameters passed to db_service
            mock_db_service.vector_search.assert_called_once_with(
                embedding=query_embedding,
                limit=1000,
                distance_function="cosine",
                chunk_size="normal",  # Legacy parameter
                provider_name="ollama"  # NEW: Provider-aware parameter
            )
            
            assert results == []
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {'PROVIDER': 'openai', 'OPENAI_API_KEY': 'test-key'}, clear=True)
    async def test_dhosearch_uses_openai_provider_table(self):
        """Test that dhosearch uses chunks table when OpenAI is the provider."""
        from soegemaskine.searchapi.dhosearch import find_nærmeste
        
        with patch('soegemaskine.searchapi.dhosearch.db_service') as mock_db_service, \
             patch('soegemaskine.searchapi.dhosearch.embedding_provider') as mock_embedding_provider:
            
            # Setup OpenAI provider mock
            mock_embedding_provider.get_provider_name.return_value = "openai"
            
            # Setup database service mock
            mock_db_service.vector_search.return_value = []
            
            # Test the search function
            query_embedding = [0.1] * 1536  # 1536-dimensional OpenAI embedding
            results = await find_nærmeste(query_embedding)
            
            # Verify correct parameters passed to db_service
            mock_db_service.vector_search.assert_called_once_with(
                embedding=query_embedding,
                limit=1000,
                distance_function="cosine",
                chunk_size="normal",
                provider_name="openai"  # Provider-aware parameter
            )
            
            assert results == []
    
    @pytest.mark.asyncio
    async def test_dhosearch_handles_no_provider_gracefully(self):
        """Test that dhosearch handles missing provider gracefully (backward compatibility)."""
        from soegemaskine.searchapi.dhosearch import find_nærmeste
        
        with patch('soegemaskine.searchapi.dhosearch.db_service') as mock_db_service, \
             patch('soegemaskine.searchapi.dhosearch.embedding_provider', None):
            
            # Setup database service mock
            mock_db_service.vector_search.return_value = []
            
            # Test the search function with no provider
            query_embedding = [0.1] * 1536
            results = await find_nærmeste(query_embedding)
            
            # Verify that provider_name is None for backward compatibility
            mock_db_service.vector_search.assert_called_once_with(
                embedding=query_embedding,
                limit=1000,
                distance_function="cosine",
                chunk_size="normal",
                provider_name=None  # Should be None when no provider available
            )
            
            assert results == []
    
    @pytest.mark.asyncio
    async def test_dhosearch_handles_provider_without_get_provider_name(self):
        """Test that dhosearch handles providers without get_provider_name method."""
        from soegemaskine.searchapi.dhosearch import find_nærmeste
        
        with patch('soegemaskine.searchapi.dhosearch.db_service') as mock_db_service, \
             patch('soegemaskine.searchapi.dhosearch.embedding_provider') as mock_embedding_provider:
            
            # Setup provider mock without get_provider_name method
            mock_embedding_provider.get_provider_name = None  # Simulate missing method
            
            # Setup database service mock
            mock_db_service.vector_search.return_value = []
            
            # Test the search function
            query_embedding = [0.1] * 1536
            results = await find_nærmeste(query_embedding)
            
            # Verify that provider_name is None when method is missing
            mock_db_service.vector_search.assert_called_once_with(
                embedding=query_embedding,
                limit=1000,
                distance_function="cosine",
                chunk_size="normal",
                provider_name=None
            )
            
            assert results == []
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {'DISTANCE_THRESHOLD': '0.3'}, clear=True)
    async def test_dhosearch_filters_results_correctly(self):
        """Test that dhosearch correctly filters results regardless of provider."""
        from soegemaskine.searchapi.dhosearch import find_nærmeste
        
        with patch('soegemaskine.searchapi.dhosearch.db_service') as mock_db_service, \
             patch('soegemaskine.searchapi.dhosearch.embedding_provider') as mock_embedding_provider:
            
            # Setup provider mock
            mock_embedding_provider.get_provider_name.return_value = "ollama"
            
            # Setup database service mock with test results
            mock_results = [
                ("book1.pdf", "Title1", "Author1", 1, "This is a long enough chunk text", 0.2),  # Should pass
                ("book2.pdf", "Title2", "Author2", 2, "Short", 0.1),  # Should fail (too short)
                ("book3.pdf", "Title3", "Author3", 3, "Another long chunk text here", 0.4),  # Should fail (distance too high)
                ("book4.pdf", "Title4", "Author4", 4, "Good chunk with acceptable distance", 0.25),  # Should pass
            ]
            mock_db_service.vector_search.return_value = mock_results
            
            # Test the search function
            query_embedding = [0.1] * 768
            results = await find_nærmeste(query_embedding)
            
            # Should only return 2 results that pass both filters
            assert len(results) == 2
            assert results[0][0] == "book1.pdf"  # distance 0.2 <= 0.3 and text long enough
            assert results[1][0] == "book4.pdf"  # distance 0.25 <= 0.3 and text long enough


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
