"""
Unit tests for embedding provider classes and factory.
"""
import pytest
from unittest.mock import patch, AsyncMock
import os
import sys
from pathlib import Path

# Add both the create_embeddings and providers directories to the path
create_embeddings_path = Path(__file__).parent.parent
providers_path = create_embeddings_path / "providers"
sys.path.insert(0, str(create_embeddings_path))
sys.path.insert(0, str(providers_path))

try:
    from providers.embedding_providers import (
        EmbeddingProvider,
        DummyEmbeddingProvider,
        OllamaEmbeddingProvider
    )
    from providers.factory import EmbeddingProviderFactory
    PROVIDERS_AVAILABLE = True
except ImportError as e:
    pytest.skip(f"Could not import providers: {e}", allow_module_level=True)
    PROVIDERS_AVAILABLE = False


@pytest.mark.unit
@pytest.mark.skipif(not PROVIDERS_AVAILABLE, reason="Providers not available")
class TestOllamaEmbeddingProvider:
    """Test the OllamaEmbeddingProvider class."""
    
    def test_initialization(self):
        """Test OllamaEmbeddingProvider initialization."""
        provider = OllamaEmbeddingProvider("http://localhost:11434", "nomic-embed-text")
        assert isinstance(provider, EmbeddingProvider)
        assert isinstance(provider, OllamaEmbeddingProvider)
        assert provider.base_url == "http://localhost:11434"
        assert provider.model == "nomic-embed-text"
        assert hasattr(provider, 'client')
    
    def test_initialization_with_defaults(self):
        """Test OllamaEmbeddingProvider initialization with defaults."""
        with patch.dict(os.environ, {'OLLAMA_BASE_URL': 'http://test:11434', 'OLLAMA_MODEL': 'test-model'}):
            provider = OllamaEmbeddingProvider()
            assert provider.base_url == "http://test:11434"
            assert provider.model == "test-model"
    
    def test_initialization_url_stripping(self):
        """Test that trailing slashes are stripped from base URL."""
        provider = OllamaEmbeddingProvider("http://localhost:11434/", "test-model")
        assert provider.base_url == "http://localhost:11434"
    
    @pytest.mark.asyncio
    async def test_get_embedding_success(self):
        """Test successful embedding generation."""
        with patch('providers.embedding_providers.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value={"embedding": [0.1] * 768})
            mock_response.raise_for_status.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            provider = OllamaEmbeddingProvider()
            embedding = await provider.get_embedding("test chunk")
            
            # Check the actual base_url used by the provider to determine expected URL
            expected_url = f"{provider.base_url}/api/embeddings"
            
            assert embedding == [0.1] * 768
            mock_client.post.assert_called_once_with(
                expected_url,
                json={"model": "nomic-embed-text", "prompt": "test chunk"}
            )
    
    @pytest.mark.asyncio
    async def test_get_embedding_api_error(self):
        """Test handling of Ollama API errors."""
        with patch('providers.embedding_providers.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = Exception("Connection error")
            mock_client_class.return_value = mock_client
            
            provider = OllamaEmbeddingProvider()
            
            with pytest.raises(RuntimeError, match="Ollama embedding request failed"):
                await provider.get_embedding("test")
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        with patch('providers.embedding_providers.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            provider = OllamaEmbeddingProvider()
            
            async with provider as p:
                assert p is provider
                
            mock_client.aclose.assert_called_once()


@pytest.mark.unit
@pytest.mark.skipif(not PROVIDERS_AVAILABLE, reason="Providers not available")
class TestEmbeddingProviderFactoryWithOllama:
    """Test factory with Ollama provider."""
    
    def test_create_ollama_provider(self):
        """Test creation of Ollama provider."""
        with patch.dict(os.environ, {'OLLAMA_BASE_URL': 'http://test:11434', 'OLLAMA_MODEL': 'test-model'}):
            provider = EmbeddingProviderFactory.create_provider("ollama")
            assert isinstance(provider, OllamaEmbeddingProvider)
            assert provider.base_url == "http://test:11434"
            assert provider.model == "test-model"
    
    def test_create_ollama_provider_defaults(self):
        """Test Ollama provider creation with defaults."""
        import os
        provider = EmbeddingProviderFactory.create_provider("ollama")
        assert isinstance(provider, OllamaEmbeddingProvider)
        
        # Check if environment variable is set (e.g., in VS Code test runner)
        expected_base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        assert provider.base_url == expected_base_url
        assert provider.model == "nomic-embed-text"
    
    def test_create_ollama_provider_with_params(self):
        """Test Ollama provider creation with explicit parameters."""
        provider = EmbeddingProviderFactory.create_provider("ollama", model="custom-model")
        assert isinstance(provider, OllamaEmbeddingProvider)
        assert provider.model == "custom-model"
    
    def test_updated_factory_supports_all_providers(self):
        """Test that factory supports all known providers."""
        supported_providers = ["openai", "dummy", "ollama"]
        
        for provider_name in supported_providers:
            provider = EmbeddingProviderFactory.create_provider(provider_name, "test_key")
            assert isinstance(provider, EmbeddingProvider)
    
    def test_unknown_provider_error(self):
        """Test that unknown provider raises ValueError."""
        with pytest.raises(ValueError, match="Ukendt udbyder: unknown"):
            EmbeddingProviderFactory.create_provider("unknown")


@pytest.mark.unit
@pytest.mark.skipif(not PROVIDERS_AVAILABLE, reason="Providers not available")
class TestDummyEmbeddingProvider:
    """Test the DummyEmbeddingProvider class for regression."""
    
    @pytest.mark.asyncio
    async def test_get_embedding_return_type(self):
        """Test that get_embedding returns correct type and size."""
        provider = DummyEmbeddingProvider()
        embedding = await provider.get_embedding("test text")

        assert isinstance(embedding, list)
        assert len(embedding) == 1536  # Match embedding_providers.py DummyEmbeddingProvider
        assert all(isinstance(x, (int, float)) for x in embedding)
