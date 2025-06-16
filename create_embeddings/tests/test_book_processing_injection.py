"""
Comprehensive tests for book processing with dependency injection.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
import sys
from pathlib import Path

# Add the src directory to the path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from create_embeddings.opret_bøger import (
        save_book, 
        process_book, 
        EmbeddingProvider,
        OpenAIEmbeddingProvider,
        DummyEmbeddingProvider,
        EmbeddingProviderFactory
    )
    from database import BookService, PostgreSQLService
    BOOK_PROCESSING_AVAILABLE = True
except ImportError as e:
    pytest.skip(f"Could not import book processing modules: {e}", allow_module_level=True)
    BOOK_PROCESSING_AVAILABLE = False


@pytest.mark.unit
@pytest.mark.skipif(not BOOK_PROCESSING_AVAILABLE, reason="Book processing modules not available")
class TestBookProcessingWithInjection:
    """Test book processing functions using dependency injection."""

    @pytest.mark.asyncio
    async def test_save_book_with_dependency_injection(self):
        """Test saving a book using dependency injection."""
        # Mock book data
        book_data = {
            "pdf-url": "https://example.com/test.pdf",
            "titel": "Test Book",
            "forfatter": "Test Author",
            "sider": 10,
            "chunks": [
                (1, "Test chunk 1"),
                (2, "Test chunk 2")
            ],
            "embeddings": [
                [0.1, 0.2, 0.3],
                [0.4, 0.5, 0.6]
            ]
        }

        # Mock BookService
        mock_book_service = AsyncMock(spec=BookService)
        mock_book_service.create_book.return_value = 123  # Mock book ID
        mock_book_service.create_chunk.return_value = None

        # Call the function
        await save_book(book_data, mock_book_service)

        # Verify book creation was called
        mock_book_service.create_book.assert_called_once_with(
            pdf_navn="https://example.com/test.pdf",
            titel="Test Book",
            forfatter="Test Author",
            antal_sider=10
        )

        # Verify chunk creation was called for each chunk
        assert mock_book_service.create_chunk.call_count == 2
        
        # Check first chunk call
        first_call = mock_book_service.create_chunk.call_args_list[0]
        assert first_call[1]['book_id'] == 123
        assert first_call[1]['sidenr'] == 1
        assert first_call[1]['chunk'] == "Test chunk 1"
        assert first_call[1]['embedding'] == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_save_book_handles_service_errors(self):
        """Test that save_book handles BookService errors properly."""
        book_data = {
            "pdf-url": "https://example.com/test.pdf",
            "titel": "Test Book",
            "forfatter": "Test Author",
            "sider": 10,
            "chunks": [(1, "Test chunk")],
            "embeddings": [[0.1, 0.2, 0.3]]
        }

        # Mock BookService that raises an exception
        mock_book_service = AsyncMock(spec=BookService)
        mock_book_service.create_book.side_effect = Exception("Database error")

        # Verify exception is propagated
        with pytest.raises(Exception, match="Database error"):
            await save_book(book_data, mock_book_service)

    @pytest.mark.asyncio
    async def test_process_book_skips_existing_book(self):
        """Test that process_book skips books that already exist."""
        book_url = "https://example.com/existing.pdf"
        
        # Mock BookService that returns an existing book
        mock_book_service = AsyncMock(spec=BookService)
        mock_book_service.get_book_by_pdf_navn.return_value = {"id": 123, "titel": "Existing Book"}
        
        # Mock session and embedding provider
        mock_session = AsyncMock()
        mock_embedding_provider = AsyncMock()

        # Call the function
        await process_book(book_url, 1000, mock_book_service, mock_session, mock_embedding_provider)

        # Verify it checked for existing book
        mock_book_service.get_book_by_pdf_navn.assert_called_once_with(book_url)
        
        # Verify it didn't try to process the book further
        mock_session.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_book_handles_new_book(self):
        """Test that process_book handles new books correctly."""
        book_url = "https://example.com/new.pdf"
        
        # Mock BookService that returns None (book doesn't exist)
        mock_book_service = AsyncMock(spec=BookService)
        mock_book_service.get_book_by_pdf_navn.return_value = None
        
        # Mock session and embedding provider
        mock_session = AsyncMock()
        mock_embedding_provider = AsyncMock()

        # Mock fetch_pdf to return None (PDF not accessible)
        with patch('create_embeddings.opret_bøger.fetch_pdf', return_value=None) as mock_fetch:
            await process_book(book_url, 1000, mock_book_service, mock_session, mock_embedding_provider)

            # Verify it checked for existing book
            mock_book_service.get_book_by_pdf_navn.assert_called_once_with(book_url)
            
            # Verify it tried to fetch the PDF
            mock_fetch.assert_called_once_with(book_url, mock_session)

    @pytest.mark.asyncio
    async def test_process_book_successful_processing(self):
        """Test successful book processing end-to-end."""
        book_url = "https://example.com/new.pdf"
        
        # Mock BookService
        mock_book_service = AsyncMock(spec=BookService)
        mock_book_service.get_book_by_pdf_navn.return_value = None
        
        # Mock session and embedding provider
        mock_session = AsyncMock()
        mock_embedding_provider = AsyncMock()

        # Mock PDF document
        mock_pdf = Mock()
        mock_pdf.metadata = {"title": "Test Book", "author": "Test Author"}
        
        # Mock book data returned from parse_book
        mock_book_data = {
            "pdf-url": book_url,
            "titel": "Test Book",
            "forfatter": "Test Author",
            "sider": 5,
            "chunks": [(1, "Test chunk")],
            "embeddings": [[0.1, 0.2, 0.3]]
        }

        with patch('create_embeddings.opret_bøger.fetch_pdf', return_value=mock_pdf) as mock_fetch:
            with patch('create_embeddings.opret_bøger.parse_book', return_value=mock_book_data) as mock_parse:
                with patch('create_embeddings.opret_bøger.save_book') as mock_save:
                    await process_book(book_url, 1000, mock_book_service, mock_session, mock_embedding_provider)

                    # Verify all steps were called
                    mock_fetch.assert_called_once_with(book_url, mock_session)
                    mock_parse.assert_called_once_with(mock_pdf, book_url, 1000, mock_embedding_provider)
                    mock_save.assert_called_once_with(mock_book_data, mock_book_service)


@pytest.mark.unit
@pytest.mark.skipif(not BOOK_PROCESSING_AVAILABLE, reason="Book processing modules not available")
class TestEmbeddingProviders:
    """Test embedding provider implementations."""

    def test_embedding_provider_interface(self):
        """Test that EmbeddingProvider is an abstract base class."""
        with pytest.raises(TypeError):
            EmbeddingProvider()

    def test_dummy_embedding_provider(self):
        """Test DummyEmbeddingProvider implementation."""
        provider = DummyEmbeddingProvider()
        assert isinstance(provider, EmbeddingProvider)

    @pytest.mark.asyncio
    async def test_dummy_embedding_provider_get_embedding(self):
        """Test DummyEmbeddingProvider.get_embedding method."""
        provider = DummyEmbeddingProvider()
        embedding = await provider.get_embedding("test text")
        
        assert isinstance(embedding, list)
        assert len(embedding) == 1536
        assert all(isinstance(x, float) for x in embedding)

    def test_openai_embedding_provider_initialization(self):
        """Test OpenAIEmbeddingProvider initialization."""
        with patch.dict('os.environ', {'OPENAI_MODEL': 'text-embedding-3-small'}):
            provider = OpenAIEmbeddingProvider("test-api-key")
            assert isinstance(provider, EmbeddingProvider)
            assert provider.model == 'text-embedding-3-small'

    @pytest.mark.asyncio
    async def test_openai_embedding_provider_get_embedding(self):
        """Test OpenAIEmbeddingProvider.get_embedding method."""
        with patch.dict('os.environ', {'OPENAI_MODEL': 'text-embedding-3-small'}):
            provider = OpenAIEmbeddingProvider("test-api-key")
            
            # Mock the OpenAI client response
            mock_response = Mock()
            mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]
            provider.client.embeddings.create = AsyncMock(return_value=mock_response)
            
            embedding = await provider.get_embedding("test text")
            
            assert embedding == [0.1, 0.2, 0.3]
            provider.client.embeddings.create.assert_called_once_with(
                input="test text", 
                model='text-embedding-3-small'
            )

    def test_embedding_provider_factory_openai(self):
        """Test EmbeddingProviderFactory creates OpenAI provider."""
        provider = EmbeddingProviderFactory.create_provider("openai", "test-key")
        assert isinstance(provider, OpenAIEmbeddingProvider)

    def test_embedding_provider_factory_dummy(self):
        """Test EmbeddingProviderFactory creates dummy provider."""
        provider = EmbeddingProviderFactory.create_provider("dummy", "any-key")
        assert isinstance(provider, DummyEmbeddingProvider)

    def test_embedding_provider_factory_unknown(self):
        """Test EmbeddingProviderFactory raises error for unknown provider."""
        with pytest.raises(ValueError, match="Ukendt udbyder"):
            EmbeddingProviderFactory.create_provider("unknown", "test-key")


@pytest.mark.integration
@pytest.mark.skipif(not BOOK_PROCESSING_AVAILABLE, reason="Book processing modules not available")
class TestBookProcessingIntegration:
    """Integration tests for book processing with dependency injection."""

    @pytest.mark.asyncio
    async def test_book_processing_integration_with_real_services(self):
        """Test book processing integration with real service instances."""
        # This test uses real service instances but mocked database connections
        
        # Create real service instances with mocked database
        mock_db_service = AsyncMock(spec=PostgreSQLService)
        book_service = BookService(mock_db_service)
        
        # Mock database responses
        mock_db_service.execute.return_value = 123  # book_id
        mock_db_service.execute_many.return_value = None
        
        # Test data
        book_data = {
            "pdf-url": "https://example.com/integration-test.pdf",
            "titel": "Integration Test Book",
            "forfatter": "Test Author",
            "sider": 5,
            "chunks": [
                (1, "Integration test chunk 1"),
                (2, "Integration test chunk 2")
            ],
            "embeddings": [
                [0.1, 0.2, 0.3, 0.4],
                [0.5, 0.6, 0.7, 0.8]
            ]
        }
        
        # Call save_book with real service
        await save_book(book_data, book_service)
        
        # Verify interactions with the database service
        assert mock_db_service.execute.called
        # Should have called execute once for book creation
        book_creation_calls = [call for call in mock_db_service.execute.call_args_list 
                              if 'INSERT INTO books' in str(call)]
        assert len(book_creation_calls) == 1

    @pytest.mark.asyncio
    async def test_full_book_processing_workflow(self):
        """Test the complete book processing workflow."""
        # Mock all external dependencies
        with patch('create_embeddings.opret_bøger.fetch_pdf') as mock_fetch_pdf:
            with patch('create_embeddings.opret_bøger.extract_text_by_page') as mock_extract:
                with patch('create_embeddings.opret_bøger.chunk_text') as mock_chunk:
                    
                    # Setup mocks
                    mock_pdf = Mock()
                    mock_pdf.metadata = {"title": "Workflow Test", "author": "Test Author"}
                    mock_pdf.close = Mock()
                    mock_fetch_pdf.return_value = mock_pdf
                    
                    mock_extract.return_value = {1: "Page 1 text", 2: "Page 2 text"}
                    mock_chunk.side_effect = [["chunk 1"], ["chunk 2"]]
                    
                    # Mock services
                    mock_db_service = AsyncMock(spec=PostgreSQLService)
                    book_service = BookService(mock_db_service)
                    mock_db_service.execute.return_value = 456  # book_id
                    
                    # Mock embedding provider
                    mock_embedding_provider = AsyncMock()
                    mock_embedding_provider.get_embedding.side_effect = [
                        [0.1, 0.2, 0.3],  # First chunk embedding
                        [0.4, 0.5, 0.6]   # Second chunk embedding
                    ]
                    
                    # Mock session
                    mock_session = AsyncMock()
                    
                    # Test the workflow
                    book_url = "https://example.com/workflow-test.pdf"
                    
                    # First call should find no existing book
                    mock_db_service.fetch_one.return_value = None
                    
                    await process_book(book_url, 1000, book_service, mock_session, mock_embedding_provider)
                    
                    # Verify the workflow
                    mock_fetch_pdf.assert_called_once_with(book_url, mock_session)
                    mock_extract.assert_called_once_with(mock_pdf)
                    assert mock_chunk.call_count == 2  # Once for each page
                    assert mock_embedding_provider.get_embedding.call_count == 2  # Once for each chunk
                    mock_pdf.close.assert_called_once()


@pytest.mark.unit
class TestBookProcessingErrorHandling:
    """Test error handling in book processing functions."""
    
    @pytest.mark.asyncio
    async def test_save_book_database_error_handling(self):
        """Test save_book handles database errors gracefully."""
        book_data = {
            "pdf-url": "https://example.com/error-test.pdf",
            "titel": "Error Test Book",
            "forfatter": "Test Author", 
            "sider": 1,
            "chunks": [(1, "test chunk")],
            "embeddings": [[0.1, 0.2, 0.3]]
        }
        
        # Mock BookService that fails on create_book
        mock_book_service = AsyncMock(spec=BookService)
        mock_book_service.create_book.side_effect = Exception("Database connection failed")
        
        with pytest.raises(Exception, match="Database connection failed"):
            await save_book(book_data, mock_book_service)
            
    @pytest.mark.asyncio
    async def test_process_book_network_error_handling(self):
        """Test process_book handles network errors gracefully."""
        book_url = "https://example.com/network-error.pdf"
        
        # Mock BookService 
        mock_book_service = AsyncMock(spec=BookService)
        mock_book_service.get_book_by_pdf_navn.return_value = None
        
        # Mock session and embedding provider
        mock_session = AsyncMock()
        mock_embedding_provider = AsyncMock()
        
        # Mock fetch_pdf to raise a network error
        with patch('create_embeddings.opret_bøger.fetch_pdf', side_effect=Exception("Network error")):
            # Should not raise - should handle the error internally
            await process_book(book_url, 1000, mock_book_service, mock_session, mock_embedding_provider)
            
            # Should have checked for existing book
            mock_book_service.get_book_by_pdf_navn.assert_called_once_with(book_url)
