"""
Tests for enhanced provider interface with consistent context manager support.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from create_embeddings.providers import (
    EmbeddingProviderRegistry,
    OpenAIEmbeddingProvider,
    OllamaEmbeddingProvider,
    DummyEmbeddingProvider
)


@pytest.mark.asyncio
class TestEnhancedProviderInterface:
    """Test the enhanced provider interface with lifecycle methods."""
    
    async def test_openai_lifecycle(self):
        """Test OpenAI provider lifecycle methods."""
        provider = OpenAIEmbeddingProvider("test-key")
        
        # Pre-initialize checks
        assert provider.client is None
        
        # Test initialization
        await provider.initialize()
        assert provider.client is not None
        assert provider.api_key == "test-key"
        
        # Test cleanup
        await provider.cleanup()
        assert provider.client is None
    
    async def test_ollama_lifecycle(self):
        """Test Ollama provider lifecycle methods."""
        provider = OllamaEmbeddingProvider()
        
        # Pre-initialize checks
        assert provider.client is None
        
        # Test initialization
        await provider.initialize()
        assert provider.client is not None
        assert provider.base_url == "http://localhost:11434"
        
        # Test cleanup
        await provider.cleanup()
        assert provider.client is None
    
    async def test_dummy_lifecycle(self):
        """Test dummy provider lifecycle methods."""
        provider = DummyEmbeddingProvider()
        
        # Lifecycle methods should be no-ops but not fail
        await provider.initialize()
        await provider.cleanup()
        
        assert provider.embedding_dimension == 1536
    
    async def test_context_manager_openai(self):
        """Test OpenAI provider context manager."""
        async with OpenAIEmbeddingProvider("test-key") as provider:
            assert provider.client is not None
            assert provider.api_key == "test-key"
        
        assert provider.client is None
    
    async def test_context_manager_ollama(self):
        """Test Ollama provider context manager."""
        async with OllamaEmbeddingProvider() as provider:
            assert provider.client is not None
            assert provider.base_url == "http://localhost:11434"
        
        assert provider.client is None
    
    async def test_context_manager_dummy(self):
        """Test dummy provider context manager."""
        async with DummyEmbeddingProvider() as provider:
            # Should work without errors even though no real initialization needed
            assert provider.embedding_dimension == 1536
    
    async def test_error_handling_in_context(self):
        """Test error handling within context manager."""
        with pytest.raises(ValueError):
            async with OpenAIEmbeddingProvider("test-key") as provider:
                # Simulate an error
                raise ValueError("Test error")
        
        # Should still cleanup
        assert provider.client is None
    
    @patch('httpx.AsyncClient')
    async def test_ollama_client_cleanup(self, mock_client):
        """Test that Ollama client is properly cleaned up."""
        mock_aclose = AsyncMock()
        mock_client.return_value.aclose = mock_aclose
        
        async with OllamaEmbeddingProvider() as provider:
            assert provider.client is not None
        
        # Verify aclose was called
        mock_aclose.assert_called_once()
    
    async def test_provider_interface_methods(self):
        """Test that all providers implement required interface methods."""
        for provider_name in EmbeddingProviderRegistry.get_available_providers():
            if provider_name == "openai":
                provider = EmbeddingProviderRegistry.create_provider(provider_name, api_key="test-key")
            else:
                provider = EmbeddingProviderRegistry.create_provider(provider_name)
            
            # Verify all required methods exist
            assert hasattr(provider, "initialize")
            assert hasattr(provider, "cleanup")
            assert hasattr(provider, "get_embedding")
            assert hasattr(provider, "has_embeddings_for_book")
            assert hasattr(provider, "get_table_name")
            assert hasattr(provider, "get_provider_name")
            assert hasattr(provider, "__aenter__")
            assert hasattr(provider, "__aexit__")
            
            # Verify method signatures
            assert asyncio.iscoroutinefunction(provider.initialize)
            assert asyncio.iscoroutinefunction(provider.cleanup)
            assert asyncio.iscoroutinefunction(provider.get_embedding)
            assert asyncio.iscoroutinefunction(provider.has_embeddings_for_book)
            
            # Test basic provider identification
            assert provider.get_provider_name() == provider_name
            assert isinstance(provider.get_table_name(), str)


@pytest.mark.asyncio
class TestProviderResourceManagement:
    """Test proper resource management in providers."""
    
    async def test_openai_client_reuse(self):
        """Test that OpenAI client is reused between calls."""
        provider = OpenAIEmbeddingProvider("test-key")
        
        # First initialization
        await provider.initialize()
        original_client = provider.client
        
        # Second initialization should reuse client
        await provider.initialize()
        assert provider.client is original_client
        
        await provider.cleanup()
    
    async def test_ollama_client_reuse(self):
        """Test that Ollama client is reused between calls."""
        provider = OllamaEmbeddingProvider()
        
        # First initialization
        await provider.initialize()
        original_client = provider.client
        
        # Second initialization should reuse client
        await provider.initialize()
        assert provider.client is original_client
        
        await provider.cleanup()
    
    @patch('httpx.AsyncClient')
    async def test_concurrent_embedding_requests(self, mock_client):
        """Test concurrent embedding requests handle client correctly."""
        # Setup mock aclose method
        mock_aclose = AsyncMock()
        mock_client.return_value.aclose = mock_aclose

        mock_post = AsyncMock()
        mock_client.return_value.post = mock_post
        # Mock response object with json method
        mock_response = AsyncMock()
        mock_response.json = lambda: {"embedding": [0.1, 0.2, 0.3]}
        mock_response.raise_for_status = AsyncMock()
        mock_post.return_value = mock_response

        provider = OllamaEmbeddingProvider()
        
        # Run multiple embedding requests concurrently
        async with provider:
            tasks = [
                provider.get_embedding("test1"),
                provider.get_embedding("test2"),
                provider.get_embedding("test3")
            ]
            await asyncio.gather(*tasks)
        
        # Client should have been created once and cleaned up
        mock_client.assert_called_once()
        mock_aclose.assert_called_once()
        assert provider.client is None
    
    async def test_cleanup_idempotency(self):
        """Test that cleanup can be called multiple times safely."""
        providers = [
            OpenAIEmbeddingProvider("test-key"),
            OllamaEmbeddingProvider()
            # DummyEmbeddingProvider doesn't have a client attribute
        ]
        
        for provider in providers:
            await provider.initialize()
            
            # Multiple cleanups should not error
            await provider.cleanup()
            await provider.cleanup()
            await provider.cleanup()
            
            # Provider should be in clean state
            assert provider.client is None
        
        # Test DummyEmbeddingProvider separately since it has no client
        dummy = DummyEmbeddingProvider()
        await dummy.initialize()
        await dummy.cleanup()  # Should not raise errors
        await dummy.cleanup()  # Multiple cleanups should work
        assert hasattr(dummy, "embedding_dimension")
