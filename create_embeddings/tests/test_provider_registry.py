"""
Tests for the new EmbeddingProviderRegistry functionality.

This module tests the registry pattern implementation for embedding providers,
including registration, discovery, environment-based defaults, and consistent error handling.
"""

import pytest
import os
from unittest.mock import patch
from create_embeddings.providers import (
    EmbeddingProviderRegistry, 
    EmbeddingProvider, 
    DummyEmbeddingProvider,
    OpenAIEmbeddingProvider,
    OllamaEmbeddingProvider
)


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock embedding provider for testing registry functionality."""
    
    def __init__(self, **kwargs):
        self.kwargs = kwargs
    
    async def get_embedding(self, chunk: str) -> list:
        return [0.1, 0.2, 0.3]
    
    async def has_embeddings_for_book(self, book_id: int, db_service) -> bool:
        return False
    
    def get_table_name(self) -> str:
        return "mock_embeddings"
    
    def get_provider_name(self) -> str:
        return "mock"


@pytest.mark.unit
class TestEmbeddingProviderRegistry:
    """Test the EmbeddingProviderRegistry class."""
    
    def test_registry_has_all_providers(self):
        """Test that registry contains all expected providers."""
        available = EmbeddingProviderRegistry.get_available_providers()
        expected = ["openai", "ollama", "dummy"]
        
        for provider in expected:
            assert provider in available
    
    def test_create_openai_provider(self):
        """Test creation of OpenAI provider through registry."""
        provider = EmbeddingProviderRegistry.create_provider("openai", api_key="test-key")
        assert isinstance(provider, OpenAIEmbeddingProvider)
    
    def test_create_ollama_provider(self):
        """Test creation of Ollama provider through registry."""
        with patch.dict(os.environ, {'OLLAMA_BASE_URL': 'http://test:11434', 'OLLAMA_MODEL': 'test-model'}):
            provider = EmbeddingProviderRegistry.create_provider("ollama")
            assert isinstance(provider, OllamaEmbeddingProvider)
            assert provider.base_url == "http://test:11434"
            assert provider.model == "test-model"
    
    def test_create_dummy_provider(self):
        """Test creation of dummy provider through registry."""
        provider = EmbeddingProviderRegistry.create_provider("dummy")
        assert isinstance(provider, DummyEmbeddingProvider)
    
    def test_create_provider_with_kwargs(self):
        """Test that kwargs are passed to provider constructors."""
        # Register a mock provider temporarily
        original_providers = EmbeddingProviderRegistry._providers.copy()
        try:
            EmbeddingProviderRegistry.register_provider("mock", MockEmbeddingProvider)
            
            provider = EmbeddingProviderRegistry.create_provider("mock", test_param="test_value")
            assert isinstance(provider, MockEmbeddingProvider)
            # The registry passes api_key and model as None, plus our test_param
            expected_kwargs = {"api_key": None, "model": None, "test_param": "test_value"}
            assert provider.kwargs == expected_kwargs
        finally:
            # Restore original providers
            EmbeddingProviderRegistry._providers = original_providers
    
    @patch.dict('os.environ', {'PROVIDER': 'dummy'})
    def test_environment_default_provider(self):
        """Test that environment variable sets default provider."""
        provider = EmbeddingProviderRegistry.create_provider()
        assert isinstance(provider, DummyEmbeddingProvider)
    
    @patch.dict('os.environ', {}, clear=True)
    def test_default_provider_when_no_env(self):
        """Test default provider when no environment variable is set."""
        provider = EmbeddingProviderRegistry.create_provider()
        assert isinstance(provider, DummyEmbeddingProvider)  # Should default to dummy
    
    def test_unknown_provider_error(self):
        """Test consistent error message for unknown provider."""
        with pytest.raises(ValueError, match="Unknown embedding provider: unknown_provider"):
            EmbeddingProviderRegistry.create_provider("unknown_provider")
    
    def test_register_provider(self):
        """Test registering a new provider."""
        # Store original state
        original_providers = EmbeddingProviderRegistry._providers.copy()
        original_count = len(EmbeddingProviderRegistry.get_available_providers())
        
        try:
            # Register new provider
            EmbeddingProviderRegistry.register_provider("test", MockEmbeddingProvider)
            
            # Verify registration
            available = EmbeddingProviderRegistry.get_available_providers()
            assert len(available) == original_count + 1
            assert "test" in available
            
            # Test creation
            provider = EmbeddingProviderRegistry.create_provider("test")
            assert isinstance(provider, MockEmbeddingProvider)
            
        finally:
            # Restore original state
            EmbeddingProviderRegistry._providers = original_providers
    
    def test_get_available_providers_returns_list(self):
        """Test that get_available_providers returns a list."""
        available = EmbeddingProviderRegistry.get_available_providers()
        assert isinstance(available, list)
        assert len(available) > 0


@pytest.mark.unit
class TestProviderRegistryBackwardCompatibility:
    """Test backward compatibility with existing EmbeddingProviderFactory."""
    
    def test_factory_delegates_to_registry(self):
        """Test that old factory methods delegate to new registry."""
        from create_embeddings.providers import EmbeddingProviderFactory
        
        # Both should create the same type
        factory_provider = EmbeddingProviderFactory.create_provider("dummy")
        registry_provider = EmbeddingProviderRegistry.create_provider("dummy")
        
        assert isinstance(factory_provider, type(registry_provider))
        assert isinstance(factory_provider, DummyEmbeddingProvider)
    
    def test_factory_error_consistency(self):
        """Test that factory and registry produce consistent errors."""
        from create_embeddings.providers import EmbeddingProviderFactory
        
        # Both should raise the same error
        with pytest.raises(ValueError, match="Unknown embedding provider: unknown"):
            EmbeddingProviderFactory.create_provider("unknown")
        
        with pytest.raises(ValueError, match="Unknown embedding provider: unknown"):
            EmbeddingProviderRegistry.create_provider("unknown")


@pytest.mark.unit
class TestProviderRegistryIntegration:
    """Integration tests for provider registry functionality."""
    
    def test_registry_state_isolation(self):
        """Test that registry modifications don't affect other tests."""
        # Get original state
        original_count = len(EmbeddingProviderRegistry._providers)
        
        # Register a temporary provider
        EmbeddingProviderRegistry.register_provider("temp", MockEmbeddingProvider)
        assert len(EmbeddingProviderRegistry._providers) == original_count + 1
        
        # Remove temporary provider
        del EmbeddingProviderRegistry._providers["temp"]
        assert len(EmbeddingProviderRegistry._providers) == original_count
    
    @patch.dict('os.environ', {'PROVIDER': 'ollama', 'OLLAMA_BASE_URL': 'http://custom:11434'})
    def test_full_environment_integration(self):
        """Test full integration with environment variables."""
        provider = EmbeddingProviderRegistry.create_provider()
        
        assert isinstance(provider, OllamaEmbeddingProvider)
        assert provider.base_url == "http://custom:11434"
    
    def test_provider_interface_compliance(self):
        """Test that all registered providers implement the correct interface."""
        for provider_name in EmbeddingProviderRegistry.get_available_providers():
            provider = EmbeddingProviderRegistry.create_provider(provider_name, api_key="test")
            assert isinstance(provider, EmbeddingProvider)
            
            # Test that all required methods exist
            assert hasattr(provider, 'get_embedding')
            assert hasattr(provider, 'has_embeddings_for_book')
            assert hasattr(provider, 'get_table_name')
            assert hasattr(provider, 'get_provider_name')
