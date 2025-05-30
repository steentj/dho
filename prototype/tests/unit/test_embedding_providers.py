"""
Unit tests for embedding provider classes and factory.
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os
from pathlib import Path

# Add the create_embeddings directory to the path for imports
create_embeddings_path = Path(__file__).parent.parent.parent.parent / "create_embeddings"
sys.path.insert(0, str(create_embeddings_path))

try:
    from opret_bøger import (
        EmbeddingProvider,
        OpenAIEmbeddingProvider,
        DummyEmbeddingProvider,
        EmbeddingProviderFactory
    )
    EMBEDDING_PROVIDERS_AVAILABLE = True
except ImportError as e:
    pytest.skip(f"Could not import from opret_bøger: {e}", allow_module_level=True)
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
    async def test_get_embedding_success(self):
        """Test successful embedding generation."""
        with patch('opret_bøger.AsyncOpenAI') as mock_openai_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.data = [AsyncMock()]
            mock_response.data[0].embedding = [0.1] * 1536
            mock_client.embeddings.create.return_value = mock_response
            mock_openai_class.return_value = mock_client
            
            provider = OpenAIEmbeddingProvider("test_key")
            embedding = await provider.get_embedding("test chunk")
            
            assert embedding == [0.1] * 1536
            mock_client.embeddings.create.assert_called_once_with(
                input="test chunk",
                model=provider.model
            )
    
    @pytest.mark.asyncio
    async def test_get_embedding_with_custom_model(self):
        """Test embedding generation with custom model."""
        with patch.dict(os.environ, {'OPENAI_MODEL': 'text-embedding-3-large'}):
            with patch('opret_bøger.AsyncOpenAI') as mock_openai_class:
                mock_client = AsyncMock()
                mock_response = AsyncMock()
                mock_response.data = [AsyncMock()]
                mock_response.data[0].embedding = [0.2] * 1536
                mock_client.embeddings.create.return_value = mock_response
                mock_openai_class.return_value = mock_client
                
                provider = OpenAIEmbeddingProvider("test_key")
                embedding = await provider.get_embedding("test")
                
                assert embedding == [0.2] * 1536
                # Verify correct model was used
                call_args = mock_client.embeddings.create.call_args
                assert call_args[1]['model'] == 'text-embedding-3-large'
    
    @pytest.mark.asyncio
    async def test_get_embedding_api_error_handling(self):
        """Test handling of OpenAI API errors."""
        with patch('opret_bøger.AsyncOpenAI') as mock_openai_class:
            mock_client = AsyncMock()
            mock_client.embeddings.create.side_effect = Exception("API Error")
            mock_openai_class.return_value = mock_client
            
            provider = OpenAIEmbeddingProvider("test_key")
            
            with pytest.raises(Exception, match="API Error"):
                await provider.get_embedding("test")
    
    @pytest.mark.asyncio
    async def test_get_embedding_input_preprocessing(self):
        """Test that input text is passed correctly to API."""
        with patch('opret_bøger.AsyncOpenAI') as mock_openai_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.data = [AsyncMock()]
            mock_response.data[0].embedding = [0.1] * 1536
            mock_client.embeddings.create.return_value = mock_response
            mock_openai_class.return_value = mock_client
            
            provider = OpenAIEmbeddingProvider("test_key")
            test_text = "Dette er en test med dansk tekst."
            await provider.get_embedding(test_text)
            
            # Verify the exact text was passed
            call_args = mock_client.embeddings.create.call_args
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
        with pytest.raises(ValueError, match="Unknown provider: unknown"):
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
class TestEmbeddingProviderIntegration:
    """Integration tests for embedding providers."""
    
    @pytest.mark.asyncio
    async def test_provider_interface_compliance(self):
        """Test that all providers comply with the interface."""
        # Test dummy provider
        dummy = DummyEmbeddingProvider()
        dummy_embedding = await dummy.get_embedding("test")
        
        assert hasattr(dummy, 'get_embedding')
        assert callable(dummy.get_embedding)
        assert isinstance(dummy_embedding, list)
        assert len(dummy_embedding) == 1536
    
    def test_factory_produces_correct_interfaces(self):
        """Test that factory produces objects with correct interfaces."""
        providers = [
            ("dummy", DummyEmbeddingProvider),
            ("openai", OpenAIEmbeddingProvider)
        ]
        
        for provider_name, expected_class in providers:
            provider = EmbeddingProviderFactory.create_provider(provider_name, "test")
            assert isinstance(provider, expected_class)
            assert isinstance(provider, EmbeddingProvider)
            assert hasattr(provider, 'get_embedding')
            assert callable(provider.get_embedding)
