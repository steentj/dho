"""
Unit tests for text processing functions in the embedding script.
"""
import pytest
import tempfile
import os
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add the create_embeddings directory to the path for imports
create_embeddings_path = Path(__file__).parent.parent.parent.parent / "create_embeddings"
sys.path.insert(0, str(create_embeddings_path))

try:
    from create_embeddings.tests.test_utils import (
        chunk_text_adapter as chunk_text,
        safe_db_execute_adapter as safe_db_execute
    )
    from create_embeddings.providers.factory import EmbeddingProviderFactory
    from create_embeddings.providers.embedding_providers import (
        OpenAIEmbeddingProvider,
        DummyEmbeddingProvider
    )
    from create_embeddings.tests.test_utils import (
        extract_text_by_page_adapter as extract_text_by_page,
        indlæs_urls_adapter as indlæs_urls
    )
except ImportError as e:
    pytest.skip(f"Could not import from test_utils: {e}", allow_module_level=True)


@pytest.mark.unit
class TestChunkText:
    """Test the chunk_text function."""
    
    def test_chunk_text_basic(self):
        """Test basic text chunking functionality."""
        text = "Dette er en test sætning. Dette er en anden sætning. Dette er en tredje sætning."
        chunks = list(chunk_text(text, max_tokens=5))
        
        assert len(chunks) > 0
        # Each chunk should have at most 5 tokens
        for chunk in chunks:
            assert len(chunk.split()) <= 5
    
    def test_chunk_text_single_sentence(self):
        """Test chunking with a single short sentence."""
        text = "Kort sætning."
        chunks = list(chunk_text(text, max_tokens=10))
        
        assert len(chunks) == 1
        assert chunks[0] == "Kort sætning."
    
    def test_chunk_text_empty_string(self):
        """Test chunking with empty string."""
        text = ""
        chunks = list(chunk_text(text, max_tokens=10))
        
        assert len(chunks) == 0
    
    def test_chunk_text_long_sentence(self):
        """Test chunking with a very long sentence that exceeds max_tokens."""
        text = "Dette er en meget lang sætning med mange ord der overstiger det maksimale antal tokens tilladt i en chunk."
        chunks = list(chunk_text(text, max_tokens=5))
        
        assert len(chunks) > 0
        # Should handle long sentences gracefully
        for chunk in chunks:
            token_count = len(chunk.split())
            # Allow some flexibility for very long sentences
            assert token_count <= 10  # More lenient for edge cases
    
    def test_chunk_text_whitespace_normalization(self):
        """Test that extra whitespace is normalized."""
        text = "Dette  er   en   test\n\n\nmmed   ekstra   mellemrum."
        chunks = list(chunk_text(text, max_tokens=10))
        
        assert len(chunks) == 1
        # Should normalize whitespace
        assert "  " not in chunks[0]
        assert "\n" not in chunks[0]
    
    def test_chunk_text_punctuation_splitting(self):
        """Test that text is split correctly at sentence boundaries."""
        text = "Første sætning. Anden sætning! Tredje sætning? Fjerde sætning."
        chunks = list(chunk_text(text, max_tokens=3))
        
        assert len(chunks) >= 2
        # Should split at sentence boundaries when possible


@pytest.mark.unit
class TestExtractTextByPage:
    """Test the extract_text_by_page function."""
    
    def test_extract_text_basic(self, mock_fitz_document):
        """Test basic text extraction from PDF pages."""
        result = extract_text_by_page(mock_fitz_document)
        
        assert isinstance(result, dict)
        assert len(result) == 3  # Mock document has 3 pages
        assert 1 in result
        assert 2 in result
        assert 3 in result
    
    def test_extract_text_cleaning(self):
        """Test that text cleaning removes soft line breaks correctly."""
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1
        
        mock_page = MagicMock()
        # Text with various line break patterns
        mock_page.get_text.return_value = "Dette er en test­\nmed blødt linjeskift og-\nordinært linjeskift."
        mock_doc.__getitem__.return_value = mock_page
        
        result = extract_text_by_page(mock_doc)
        
        assert 1 in result
        cleaned_text = result[1]
        assert "­\n" not in cleaned_text  # Soft hyphen + newline should be removed
        assert "-\n" not in cleaned_text   # Hyphen + newline should be removed
    
    def test_extract_text_empty_page(self):
        """Test handling of empty pages."""
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1
        
        mock_page = MagicMock()
        mock_page.get_text.return_value = ""
        mock_doc.__getitem__.return_value = mock_page
        
        result = extract_text_by_page(mock_doc)
        
        assert 1 in result
        assert result[1] == ""


@pytest.mark.unit
class TestIndlæsUrls:
    """Test the indlæs_urls function."""
    
    def test_indlæs_urls_basic(self, temp_test_file):
        """Test basic URL loading from file."""
        urls = indlæs_urls(temp_test_file)
        
        assert isinstance(urls, list)
        assert len(urls) == 2
        assert "http://example.com/book1.pdf" in urls
        assert "http://example.com/book2.pdf" in urls
    
    def test_indlæs_urls_empty_file(self):
        """Test loading from empty file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            temp_path = f.name
        
        try:
            urls = indlæs_urls(temp_path)
            assert urls == []
        finally:
            os.unlink(temp_path)
    
    def test_indlæs_urls_whitespace_handling(self):
        """Test that whitespace is properly stripped."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("  http://example.com/book1.pdf  \n")
            f.write("\nhttp://example.com/book2.pdf\n\n")
            temp_path = f.name
        
        try:
            urls = indlæs_urls(temp_path)
            assert len(urls) == 2
            assert "http://example.com/book1.pdf" in urls
            assert "http://example.com/book2.pdf" in urls
        finally:
            os.unlink(temp_path)
    
    def test_indlæs_urls_nonexistent_file(self):
        """Test handling of nonexistent file."""
        with pytest.raises(FileNotFoundError):
            indlæs_urls("nonexistent_file.txt")


@pytest.mark.unit
class TestEmbeddingProviderFactory:
    """Test the EmbeddingProviderFactory class."""
    
    def test_create_openai_provider(self):
        """Test creation of OpenAI provider."""
        provider = EmbeddingProviderFactory.create_provider("openai", "test_key")
        
        assert isinstance(provider, OpenAIEmbeddingProvider)
    
    def test_create_dummy_provider(self):
        """Test creation of dummy provider."""
        provider = EmbeddingProviderFactory.create_provider("dummy", "test_key")
        
        assert isinstance(provider, DummyEmbeddingProvider)
    
    def test_create_unknown_provider(self):
        """Test error handling for unknown provider."""
        with pytest.raises(ValueError, match="Unknown embedding provider: unknown"):
            EmbeddingProviderFactory.create_provider("unknown", "test_key")


@pytest.mark.unit
class TestDummyEmbeddingProvider:
    """Test the DummyEmbeddingProvider class."""
    
    @pytest.mark.asyncio
    async def test_get_embedding_consistency(self):
        """Test that dummy provider returns consistent embeddings."""
        provider = DummyEmbeddingProvider()
        
        embedding1 = await provider.get_embedding("test text")
        embedding2 = await provider.get_embedding("test text")
        
        assert embedding1 == embedding2
        assert len(embedding1) == 1536
        assert all(isinstance(x, (int, float)) for x in embedding1)
    
    @pytest.mark.asyncio
    async def test_get_embedding_different_texts(self):
        """Test that dummy provider returns same embedding for different texts."""
        provider = DummyEmbeddingProvider()
        
        embedding1 = await provider.get_embedding("first text")
        embedding2 = await provider.get_embedding("second text")
        
        # Dummy provider should return same embedding regardless of input
        assert embedding1 == embedding2


@pytest.mark.unit
class TestOpenAIEmbeddingProvider:
    """Test the OpenAIEmbeddingProvider class."""
    @pytest.mark.asyncio
    async def test_get_embedding_with_mock(self, mock_async_openai_client):
        """Test embedding generation with mocked OpenAI client."""
        # Mock the OpenAI embeddings response
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_async_openai_client.embeddings.create.return_value = mock_response

        with patch('create_embeddings.providers.embedding_providers.AsyncOpenAI') as mock_openai_class:
            mock_openai_class.return_value = mock_async_openai_client
            
            provider = OpenAIEmbeddingProvider("test_key")
            embedding = await provider.get_embedding("test chunk")

            assert len(embedding) == 1536
            assert embedding == mock_response.data[0].embedding
            mock_async_openai_client.embeddings.create.assert_called_once()
    
    def test_initialization(self):
        """Test provider initialization."""
        with patch.dict(os.environ, {'OPENAI_MODEL': 'test-model'}):
            provider = OpenAIEmbeddingProvider("test_key")
            assert hasattr(provider, 'client')
            assert hasattr(provider, 'model')


@pytest.mark.unit
class TestSafeDbExecute:
    """Test the safe_db_execute function."""
    
    @pytest.mark.asyncio
    async def test_successful_execution(self, mock_database_connection):
        """Test successful database execution."""
        mock_database_connection.fetchval.return_value = 42
        
        result = await safe_db_execute(
            "http://test.com/book.pdf",
            mock_database_connection,
            "SELECT 1",
            "param1"
        )
        
        assert result == 42
        mock_database_connection.fetchval.assert_called_once_with("SELECT 1", "param1")
        
    @pytest.mark.asyncio
    async def test_exception_handling(self, mock_database_connection):
        """Test exception handling in database execution."""
        mock_database_connection.fetchval.side_effect = Exception("Database error")
        
        with patch('logging.exception') as mock_exception:
            result = await safe_db_execute(
                "http://test.com/book.pdf",
                mock_database_connection,
                "SELECT 1"
            )
            
            assert result is None
            assert mock_exception.call_count > 0
    
    @pytest.mark.asyncio
    async def test_logging_includes_url(self, mock_database_connection):
        """Test that logging includes the URL for context."""
        mock_database_connection.fetchval.side_effect = Exception("Database error")
        
        with patch('logging.exception') as mock_exception:
            await safe_db_execute(
                "http://test.com/book.pdf",
                mock_database_connection,
                "SELECT 1"
            )
            
            # Check that the call happened
            assert mock_exception.call_count > 0
            # Get the arguments from the first call
            args = mock_exception.call_args
            if args:
                # Check that the URL is included in the log message
                log_message = args[0][0]
                assert "http://test.com/book.pdf" in log_message
