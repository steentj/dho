"""
Test for the Ollama embedding provider bug.

This test reproduces the issue where response.json() returns a dict instead of a coroutine.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from create_embeddings.providers.embedding_providers import OllamaEmbeddingProvider


class TestOllamaEmbeddingBug:
    """Test the Ollama embedding provider bug."""
    
    @pytest.mark.asyncio
    async def test_ollama_embedding_with_dict_response_json(self):
        """
        Test that the fixed code handles response.json() returning a dict directly.
        
        This test simulates the actual scenario we were seeing in production,
        but now it should work correctly after our fix.
        """
        # Create provider
        provider = OllamaEmbeddingProvider(
            base_url="http://test-ollama:11434",
            model="test-model"
        )
        await provider.initialize()  # Initialize the client first
        
        # Create a mock response that behaves like the problematic one
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        
        # The previous bug: response.json() returns a dict directly, not a coroutine
        mock_response.json.return_value = {"embedding": [0.1, 0.2, 0.3]}  # Not awaitable, but should work now
        
        # Mock the HTTP client
        with patch.object(provider.client, 'post', return_value=mock_response) as mock_post:
            mock_post.return_value = mock_response
            
            # This should now work correctly with our fix
            result = await provider.get_embedding("test chunk")
            assert result == [0.1, 0.2, 0.3]
    
    @pytest.mark.asyncio 
    async def test_ollama_embedding_with_correct_async_response(self):
        """
        Test that shows how the fixed version should work.
        
        This test shows the expected behavior after the fix.
        """
        # Create provider
        provider = OllamaEmbeddingProvider(
            base_url="http://test-ollama:11434", 
            model="test-model"
        )
        await provider.initialize()  # Initialize the client first
        
        # Create a proper async mock response
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={"embedding": [0.1, 0.2, 0.3]})
        
        # Mock the HTTP client with proper async behavior
        with patch.object(provider.client, 'post', return_value=mock_response):
            # This should work correctly
            result = await provider.get_embedding("test chunk")
            assert result == [0.1, 0.2, 0.3]
    
    @pytest.mark.asyncio
    async def test_ollama_embedding_handles_non_awaitable_gracefully(self):
        """
        Test that the fixed code handles both awaitable and non-awaitable response.json().
        
        This tests the defensive fix we'll implement.
        """
        # Create provider
        provider = OllamaEmbeddingProvider(
            base_url="http://test-ollama:11434",
            model="test-model"
        )
        await provider.initialize()  # Initialize the client first
        
        # Create a mock response with non-awaitable json()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"embedding": [0.1, 0.2, 0.3]}  # Direct dict
        
        with patch.object(provider.client, 'post', return_value=mock_response):
            # After our fix, this should work even with non-awaitable json()
            result = await provider.get_embedding("test chunk")
            assert result == [0.1, 0.2, 0.3]
