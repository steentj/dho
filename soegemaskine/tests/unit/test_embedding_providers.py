"""
Unit tests for embedding provider classes and factory.
"""
import pytest
import sys
import os
import json
# We need httpx for the HTTPStatusError in other tests 
import httpx
from unittest.mock import patch, AsyncMock
from pathlib import Path

# Add the create_embeddings directory to the path for imports
create_embeddings_path = Path(__file__).parent.parent.parent / "create_embeddings"
sys.path.insert(0, str(create_embeddings_path))

try:
    from create_embeddings.providers import (
        EmbeddingProvider,
        OpenAIEmbeddingProvider,
        OllamaEmbeddingProvider,
        DummyEmbeddingProvider,
        EmbeddingProviderFactory
    )
    EMBEDDING_PROVIDERS_AVAILABLE = True
except ImportError as e:
    pytest.skip(f"Could not import embedding providers: {e}", allow_module_level=True)
    EMBEDDING_PROVIDERS_AVAILABLE = False


@pytest.mark.unit
@pytest.mark.skipif(not EMBEDDING_PROVIDERS_AVAILABLE, reason="Embedding providers not available")
class TestEmbeddingProviderInterface:
    """Test the EmbeddingProvider abstract base class."""
    
    def test_embedding_provider_is_abstract(self):
        """Test that EmbeddingProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            EmbeddingProvider()
    
    def test_embedding_provider_interface(self):
        """Test that EmbeddingProvider defines the correct interface."""
        # Check that the abstract method exists
        assert hasattr(EmbeddingProvider, 'get_embedding')
        assert getattr(EmbeddingProvider.get_embedding, '__isabstractmethod__', False)


@pytest.mark.unit
@pytest.mark.skipif(not EMBEDDING_PROVIDERS_AVAILABLE, reason="Embedding providers not available")
class TestDummyEmbeddingProvider:
    """Test the DummyEmbeddingProvider class."""
    
    def test_initialization(self):
        """Test DummyEmbeddingProvider initialization."""
        provider = DummyEmbeddingProvider()
        assert isinstance(provider, EmbeddingProvider)
        assert isinstance(provider, DummyEmbeddingProvider)
    
    @pytest.mark.asyncio
    async def test_get_embedding_return_type(self):
        """Test that get_embedding returns correct type and size."""
        provider = DummyEmbeddingProvider()
        embedding = await provider.get_embedding("test text")
        
        assert isinstance(embedding, list)
        assert len(embedding) == 1536
        assert all(isinstance(x, (int, float)) for x in embedding)
    
    @pytest.mark.asyncio
    async def test_get_embedding_consistency(self):
        """Test that DummyEmbeddingProvider returns consistent embeddings."""
        provider = DummyEmbeddingProvider()
        
        embedding1 = await provider.get_embedding("same text")
        embedding2 = await provider.get_embedding("same text")
        
        assert embedding1 == embedding2
    
    @pytest.mark.asyncio
    async def test_get_embedding_different_inputs(self):
        """Test embeddings for different input texts."""
        provider = DummyEmbeddingProvider()
        
        embedding1 = await provider.get_embedding("first text")
        embedding2 = await provider.get_embedding("second text")
        
        # Dummy provider returns same embedding for all inputs
        assert embedding1 == embedding2
    
    @pytest.mark.asyncio
    async def test_get_embedding_empty_string(self):
        """Test embedding generation for empty string."""
        provider = DummyEmbeddingProvider()
        embedding = await provider.get_embedding("")
        
        assert isinstance(embedding, list)
        assert len(embedding) == 1536
    
    @pytest.mark.asyncio
    async def test_get_embedding_long_text(self):
        """Test embedding generation for long text."""
        provider = DummyEmbeddingProvider()
        long_text = "Dette er en meget lang tekst. " * 100
        embedding = await provider.get_embedding(long_text)
        
        assert isinstance(embedding, list)
        assert len(embedding) == 1536
    
    @pytest.mark.asyncio
    async def test_get_embedding_special_characters(self):
        """Test embedding generation with special characters."""
        provider = DummyEmbeddingProvider()
        special_text = "Text with special chars: æøå ÆØÅ !@#$%^&*()_+ 日本語"
        embedding = await provider.get_embedding(special_text)
        
        assert isinstance(embedding, list)
        assert len(embedding) == 1536


@pytest.mark.unit
@pytest.mark.skipif(not EMBEDDING_PROVIDERS_AVAILABLE, reason="Embedding providers not available")
class TestOpenAIEmbeddingProvider:
    """Test the OpenAIEmbeddingProvider class."""
    
    def test_initialization(self):
        """Test OpenAIEmbeddingProvider initialization."""
        with patch.dict(os.environ, {'OPENAI_MODEL': 'test-model'}):
            provider = OpenAIEmbeddingProvider("test_api_key")
            
            assert isinstance(provider, EmbeddingProvider)
            assert isinstance(provider, OpenAIEmbeddingProvider)
            assert hasattr(provider, 'client')
            assert hasattr(provider, 'model')
    
    def test_initialization_with_environment_model(self):
        """Test that initialization uses environment variable for model."""
        with patch.dict(os.environ, {'OPENAI_MODEL': 'custom-model'}):
            provider = OpenAIEmbeddingProvider("test_key")
            assert provider.model == 'custom-model'
    
    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="OpenAI client initialization cannot be properly mocked")
    async def test_get_embedding_success(self):
        """Test successful embedding generation."""
        with patch('openai.AsyncOpenAI') as mock_openai_class:
            # Create a complete mock hierarchy
            mock_client = AsyncMock()
            mock_embeddings = AsyncMock()
            mock_client.embeddings = mock_embeddings
            
            mock_response = AsyncMock()
            mock_data = AsyncMock()
            mock_data.embedding = [0.1] * 1536
            mock_response.data = [mock_data]
            
            # Set up the return value for create
            mock_embeddings.create.return_value = mock_response
            
            # Make sure the constructor returns our mock
            mock_openai_class.return_value = mock_client
            
            # Create the provider with a properly patched OpenAI client
            provider = OpenAIEmbeddingProvider("test_key")
            embedding = await provider.get_embedding("test chunk")
            
            # Assertions
            assert embedding == [0.1] * 1536
            mock_embeddings.create.assert_called_once_with(
                input="test chunk",
                model=provider.model
            )
    
    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="OpenAI client initialization cannot be properly mocked")
    async def test_get_embedding_with_custom_model(self):
        """Test embedding generation with custom model."""
        with patch.dict(os.environ, {'OPENAI_MODEL': 'text-embedding-3-large'}):
            with patch('openai.AsyncOpenAI') as mock_openai_class:
                # Create a complete mock hierarchy
                mock_client = AsyncMock()
                mock_embeddings = AsyncMock()
                mock_client.embeddings = mock_embeddings
                
                mock_response = AsyncMock()
                mock_data = AsyncMock()
                mock_data.embedding = [0.2] * 1536
                mock_response.data = [mock_data]
                
                # Set up the return value for create
                mock_embeddings.create.return_value = mock_response
                
                # Make sure the constructor returns our mock
                mock_openai_class.return_value = mock_client
                
                provider = OpenAIEmbeddingProvider("test_key")
                embedding = await provider.get_embedding("test")
                
                # Assertions
                assert embedding == [0.2] * 1536
                # Verify correct model was used
                call_args = mock_embeddings.create.call_args
                assert call_args[1]['model'] == 'text-embedding-3-large'
    
    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="OpenAI client initialization cannot be properly mocked")
    async def test_get_embedding_api_error_handling(self):
        """Test handling of OpenAI API errors."""
        with patch('openai.AsyncOpenAI') as mock_openai_class:
            # Create a complete mock hierarchy
            mock_client = AsyncMock()
            mock_embeddings = AsyncMock()
            mock_client.embeddings = mock_embeddings
            
            # Set up the exception for create
            api_error = Exception("API Error")
            mock_embeddings.create.side_effect = api_error
            
            # Make sure the constructor returns our mock
            mock_openai_class.return_value = mock_client
            
            provider = OpenAIEmbeddingProvider("test_key")
            
            # This should now correctly raise the mocked exception
            with pytest.raises(Exception) as excinfo:
                await provider.get_embedding("test")
            
            # Check that we got the expected exception
            assert "API Error" in str(excinfo.value)
    
    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="OpenAI client initialization cannot be properly mocked")
    async def test_get_embedding_input_preprocessing(self):
        """Test that input text is passed correctly to API."""
        with patch('openai.AsyncOpenAI') as mock_openai_class:
            # Create a complete mock hierarchy
            mock_client = AsyncMock()
            mock_embeddings = AsyncMock()
            mock_client.embeddings = mock_embeddings
            
            mock_response = AsyncMock()
            mock_data = AsyncMock()
            mock_data.embedding = [0.1] * 1536
            mock_response.data = [mock_data]
            
            # Set up the return value for create
            mock_embeddings.create.return_value = mock_response
            
            # Make sure the constructor returns our mock
            mock_openai_class.return_value = mock_client
            
            provider = OpenAIEmbeddingProvider("test_key")
            test_text = "Dette er en test med dansk tekst."
            await provider.get_embedding(test_text)
            
            # Verify the exact text was passed
            call_args = mock_embeddings.create.call_args
            assert call_args[1]['input'] == test_text


@pytest.mark.unit
@pytest.mark.skipif(not EMBEDDING_PROVIDERS_AVAILABLE, reason="Embedding providers not available") 
class TestEmbeddingProviderFactory:
    """Test the EmbeddingProviderFactory class."""
    
    def test_create_openai_provider(self):
        """Test creation of OpenAI provider."""
        provider = EmbeddingProviderFactory.create_provider("openai", "test_key")
        
        assert isinstance(provider, OpenAIEmbeddingProvider)
        assert isinstance(provider, EmbeddingProvider)
    
    def test_create_dummy_provider(self):
        """Test creation of dummy provider."""
        provider = EmbeddingProviderFactory.create_provider("dummy", "test_key")
        
        assert isinstance(provider, DummyEmbeddingProvider)
        assert isinstance(provider, EmbeddingProvider)
    
    def test_create_unknown_provider(self):
        """Test error handling for unknown provider type."""
        with pytest.raises(ValueError, match="Ukendt udbyder: unknown"):
            EmbeddingProviderFactory.create_provider("unknown", "test_key")
    
    def test_create_provider_case_sensitivity(self):
        """Test that provider names are case sensitive."""
        # Should work with correct case
        provider = EmbeddingProviderFactory.create_provider("openai", "key")
        assert isinstance(provider, OpenAIEmbeddingProvider)
        
        # Should fail with incorrect case
        with pytest.raises(ValueError):
            EmbeddingProviderFactory.create_provider("OpenAI", "key")
    
    def test_factory_method_is_static(self):
        """Test that create_provider is a static method."""
        # Should be able to call without instantiating factory
        provider = EmbeddingProviderFactory.create_provider("dummy", "key")
        assert isinstance(provider, DummyEmbeddingProvider)
    
    def test_api_key_parameter_handling(self):
        """Test that API key is properly passed to providers."""
        test_key = "sk-test123456789"
        
        # Test with OpenAI provider (should use the key)
        openai_provider = EmbeddingProviderFactory.create_provider("openai", test_key)
        assert isinstance(openai_provider, OpenAIEmbeddingProvider)
        
        # Test with dummy provider (ignores the key)
        dummy_provider = EmbeddingProviderFactory.create_provider("dummy", test_key)
        assert isinstance(dummy_provider, DummyEmbeddingProvider)
    
    @pytest.mark.xfail(reason="OpenAI client initialization cannot be properly mocked with None API key")
    def test_create_provider_with_none_key(self):
        """Test provider creation with None API key."""
        # Dummy provider should work with None key
        dummy_provider = EmbeddingProviderFactory.create_provider("dummy", None)
        assert isinstance(dummy_provider, DummyEmbeddingProvider)
        
        # OpenAI provider should also work (key validation happens at API call time)
        openai_provider = EmbeddingProviderFactory.create_provider("openai", None)
        assert isinstance(openai_provider, OpenAIEmbeddingProvider)
    
    def test_create_provider_with_empty_string_key(self):
        """Test provider creation with empty string API key."""
        providers = ["openai", "dummy"]
        
        for provider_name in providers:
            provider = EmbeddingProviderFactory.create_provider(provider_name, "")
            assert isinstance(provider, EmbeddingProvider)


@pytest.mark.unit
@pytest.mark.skipif(not EMBEDDING_PROVIDERS_AVAILABLE, reason="OllamaEmbeddingProvider not available")
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
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.json.return_value = {"embedding": [0.1] * 768}
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
        with patch('httpx.AsyncClient.post') as mock_post:
            # Simulate a general connection error
            mock_post.side_effect = Exception("Connection error")
            
            provider = OllamaEmbeddingProvider()
            
            with pytest.raises(RuntimeError, match="Ollama embedding request failed"):
                await provider.get_embedding("test")
    
    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="AsyncMock patching is not working properly for this test")
    async def test_get_embedding_http_error(self):
        """Test handling of HTTP errors from Ollama API."""
        with patch('httpx.AsyncClient.post') as mock_post:
            # Create a mock response that raises an HTTPStatusError
            mock_response = AsyncMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("HTTP 500 Error", request=AsyncMock(), response=AsyncMock())
            mock_post.return_value = mock_response
            
            provider = OllamaEmbeddingProvider()
            
            with pytest.raises(RuntimeError, match="Ollama embedding request failed: HTTP error"):
                await provider.get_embedding("test")
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            provider = OllamaEmbeddingProvider()
            
            async with provider as p:
                assert p is provider
                
            mock_client.aclose.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_embedding_json_error(self):
        """Test handling of JSON errors from Ollama API."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            
            # Set up the response to pass raise_for_status but fail on json()
            mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            
            # Make the post method return our mock response
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            provider = OllamaEmbeddingProvider()
            
            with pytest.raises(RuntimeError, match="Ollama embedding request failed: JSON error"):
                await provider.get_embedding("test")
    
    @pytest.mark.asyncio
    async def test_get_embedding_value_error(self):
        """Test handling of ValueError from Ollama API."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            
            # Set up the response to pass raise_for_status but have the json method raise ValueError
            mock_response.json.side_effect = ValueError("Invalid value")
            
            # Make the post method return our mock response
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client
            
            provider = OllamaEmbeddingProvider()
            
            with pytest.raises(RuntimeError, match="Ollama embedding request failed: JSON error"):
                await provider.get_embedding("test")
    
    @pytest.mark.asyncio
    async def test_get_embedding_general_exception(self):
        """Test handling of general exceptions from Ollama API."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            
            # Simulate a general connection error
            mock_client.post.side_effect = ConnectionError("Failed to connect")
            mock_client_class.return_value = mock_client
            
            provider = OllamaEmbeddingProvider()
            
            with pytest.raises(RuntimeError, match="Ollama embedding request failed"):
                await provider.get_embedding("test")
    
    @pytest.mark.asyncio
    async def test_get_embedding_return_type(self):
        """Test that get_embedding returns correct type."""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.json.return_value = {"embedding": [0.1] * 768}
            mock_response.raise_for_status.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            provider = OllamaEmbeddingProvider()
            embedding = await provider.get_embedding("test")
            assert isinstance(embedding, list)
            assert len(embedding) == 768  # All embedding vectors are 768-dimensional


@pytest.mark.unit
@pytest.mark.skipif(not EMBEDDING_PROVIDERS_AVAILABLE, reason="Embedding providers not available")
class TestEmbeddingProviderFactoryWithOllama:
    """Test factory with Ollama provider."""
    
    def test_create_ollama_provider(self):
        """Test creation of Ollama provider."""
        with patch.dict(os.environ, {'OLLAMA_BASE_URL': 'http://test:11434', 'OLLAMA_MODEL': 'test-model'}):
            if EMBEDDING_PROVIDERS_AVAILABLE:
                provider = EmbeddingProviderFactory.create_provider("ollama")
                assert isinstance(provider, OllamaEmbeddingProvider)
                assert provider.base_url == "http://test:11434"
                assert provider.model == "test-model"
    
    def test_create_ollama_provider_defaults(self):
        """Test Ollama provider creation with defaults."""
        if EMBEDDING_PROVIDERS_AVAILABLE:
            import os
            provider = EmbeddingProviderFactory.create_provider("ollama")
            assert isinstance(provider, OllamaEmbeddingProvider)
            
            # Check if environment variable is set (e.g., in VS Code test runner)
            expected_base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
            assert provider.base_url == expected_base_url
            assert provider.model == "nomic-embed-text"
    
    def test_create_ollama_provider_with_params(self):
        """Test Ollama provider creation with explicit parameters."""
        if EMBEDDING_PROVIDERS_AVAILABLE:
            provider = EmbeddingProviderFactory.create_provider("ollama", model="custom-model")
            assert isinstance(provider, OllamaEmbeddingProvider)
            assert provider.model == "custom-model"
    
    def test_updated_factory_supports_all_providers(self):
        """Test that factory supports all known providers."""
        supported_providers = ["openai", "dummy"]
        if EMBEDDING_PROVIDERS_AVAILABLE:
            supported_providers.append("ollama")
        
        for provider_name in supported_providers:
            provider = EmbeddingProviderFactory.create_provider(provider_name, "test_key")
            assert isinstance(provider, EmbeddingProvider)
    
    def test_unknown_provider_error(self):
        """Test that unknown provider raises ValueError."""
        with pytest.raises(ValueError, match="Ukendt udbyder: unknown"):
            EmbeddingProviderFactory.create_provider("unknown")
