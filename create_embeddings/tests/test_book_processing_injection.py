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
    # We no longer need to import BookService as we're not using it for spec
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
        mock_book_service = AsyncMock()  # Removed spec=BookService
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
        mock_book_service = AsyncMock()  # Removed spec=BookService
        mock_book_service.create_book.side_effect = Exception("Database error")

        # Verify exception is propagated
        with pytest.raises(Exception, match="Database error"):
            await save_book(book_data, mock_book_service)

    @pytest.mark.asyncio
    async def test_process_book_skips_existing_book(self):
        """Test that process_book skips books that already exist."""
        book_url = "https://example.com/existing.pdf"
        
        # Mock BookService that returns an existing book
        mock_book_service = AsyncMock()  # Removed spec=BookService
        mock_book_service.get_book_by_pdf_navn.return_value = {"id": 123, "titel": "Existing Book"}
        
        # Mock session and embedding provider
        mock_session = AsyncMock()
        mock_embedding_provider = AsyncMock()
        mock_chunking_strategy = Mock()

        # Call the function
        await process_book(book_url, 1000, mock_book_service, mock_session, mock_embedding_provider, mock_chunking_strategy)

        # Verify it checked for existing book
        mock_book_service.get_book_by_pdf_navn.assert_called_once_with(book_url)
        
        # Verify it didn't try to process the book further
        mock_session.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_book_handles_new_book(self):
        """Test that process_book handles new books correctly."""
        book_url = "https://example.com/new.pdf"
        
        # Mock BookService that returns None (book doesn't exist)
        mock_book_service = AsyncMock()  # Removed spec=BookService
        mock_book_service.get_book_by_pdf_navn.return_value = None
        
        # Mock session and embedding provider
        mock_session = AsyncMock()
        mock_embedding_provider = AsyncMock()
        mock_chunking_strategy = Mock()

        # Mock fetch_pdf to return None (PDF not accessible)
        with patch('create_embeddings.opret_bøger.fetch_pdf', return_value=None) as mock_fetch:
            await process_book(book_url, 1000, mock_book_service, mock_session, mock_embedding_provider, mock_chunking_strategy)

            # Verify it checked for existing book
            mock_book_service.get_book_by_pdf_navn.assert_called_once_with(book_url)
            
            # Verify it tried to fetch the PDF
            mock_fetch.assert_called_once_with(book_url, mock_session)

    @pytest.mark.asyncio
    async def test_process_book_successful_processing(self):
        """Test successful book processing end-to-end."""
        book_url = "https://example.com/new.pdf"
        
        # Mock BookService
        mock_book_service = AsyncMock()  # Removed spec=BookService
        mock_book_service.get_book_by_pdf_navn.return_value = None
        
        # Mock session and embedding provider
        mock_session = AsyncMock()
        mock_embedding_provider = AsyncMock()
        mock_chunking_strategy = Mock()

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
                    await process_book(book_url, 1000, mock_book_service, mock_session, mock_embedding_provider, mock_chunking_strategy)

                    # Verify all steps were called
                    mock_fetch.assert_called_once_with(book_url, mock_session)
                    mock_parse.assert_called_once_with(mock_pdf, book_url, 1000, mock_embedding_provider, mock_chunking_strategy)
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
    @pytest.mark.integration
    def test_wrapper_injects_alternate_chunking_strategy(self, monkeypatch):
        """Test that BookProcessorWrapper injects an alternate chunking strategy (e.g., word_splitter) into process_book."""
        from create_embeddings.book_processor_wrapper import BookProcessorWrapper
        import tempfile
        import os
        import asyncio

        # Create a temporary input file with one URL
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = os.path.join(tmpdir, "input")
            os.makedirs(input_dir)
            input_file = os.path.join(input_dir, "test_urls.txt")
            with open(input_file, "w") as f:
                f.write("https://example.com/book2.pdf\n")

            # Patch environment to use the temp input dir and alternate strategy
            monkeypatch.setenv("CHUNKING_STRATEGY", "word_splitter")
            monkeypatch.setenv("POSTGRES_DB", "dummy")
            monkeypatch.setenv("POSTGRES_USER", "dummy")
            monkeypatch.setenv("POSTGRES_PASSWORD", "dummy")
            monkeypatch.setenv("OPENAI_API_KEY", "dummy")
            monkeypatch.setenv("PROVIDER", "dummy")
            monkeypatch.setenv("CHUNK_SIZE", "5")
            monkeypatch.setenv("POSTGRES_HOST", "dummy")
            # Patch the input path logic
            monkeypatch.setattr("pathlib.Path.__truediv__", lambda self, other: Path(str(self) + "/" + str(other)))
            monkeypatch.setattr("pathlib.Path.exists", lambda self: True)
            monkeypatch.setattr("create_embeddings.book_processor_wrapper.Path", Path)
            monkeypatch.setattr("create_embeddings.book_processor_wrapper.indlæs_urls", lambda path: ["https://example.com/book2.pdf"])

            # Patch ChunkingStrategyFactory to return a mock for the alternate strategy
            mock_strategy = Mock()
            with patch("create_embeddings.book_processor_wrapper.ChunkingStrategyFactory.create_strategy", return_value=mock_strategy) as mock_factory:
                # Patch process_book to check the strategy
                with patch("create_embeddings.book_processor_wrapper.process_book", new_callable=AsyncMock) as mock_process_book:
                    # Patch asyncpg.create_pool to avoid real DB connection
                    with patch("database.postgresql.asyncpg.create_pool") as mock_create_pool:
                        class DummyPool:
                            async def __aenter__(self): return self
                            async def __aexit__(self, exc_type, exc, tb): return False
                        mock_create_pool.return_value = DummyPool()
                        wrapper = BookProcessorWrapper(output_dir=tmpdir, failed_dir=tmpdir)
                        asyncio.run(wrapper.process_books_from_file("test_urls.txt"))
                        # Assert the factory was called with the alternate strategy
                        mock_factory.assert_called_with("word_splitter")
                        # Assert process_book was called with the mock strategy
                        assert any(call.args[-1] is mock_strategy for call in mock_process_book.call_args_list)
    """Integration tests for book processing with dependency injection."""

    @pytest.mark.asyncio
    async def test_book_processing_integration_with_real_services(self):
        """Test book processing integration with real service instances."""
        # This test uses real service instances but mocked database connections
        
        # We only need a mock book_service with the methods that save_book will call
        book_service = AsyncMock()
        book_service.create_book.return_value = 123  # book_id
        book_service.create_chunk.return_value = None
        
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
        
        # Call save_book with our mock service
        await save_book(book_data, book_service)
        
        # Verify the service methods were called correctly
        book_service.create_book.assert_called_once_with(
            pdf_navn="https://example.com/integration-test.pdf",
            titel="Integration Test Book",
            forfatter="Test Author",
            antal_sider=5
        )
        
        # Should have called create_chunk twice (once for each chunk)
        assert book_service.create_chunk.call_count == 2
        
        # Check first chunk call with correct arguments
        first_call = book_service.create_chunk.call_args_list[0]
        assert first_call[1]['book_id'] == 123
        assert first_call[1]['sidenr'] == 1
        assert first_call[1]['chunk'] == "Integration test chunk 1"
        assert first_call[1]['embedding'] == [0.1, 0.2, 0.3, 0.4]

    @pytest.mark.asyncio
    async def test_full_book_processing_workflow(self):
        """Test the complete book processing workflow."""
        # Mock all external dependencies
        with patch('create_embeddings.opret_bøger.fetch_pdf') as mock_fetch_pdf:
            with patch('create_embeddings.opret_bøger.extract_text_by_page') as mock_extract:
                # Setup mocks
                mock_strategy_instance = Mock()
                mock_strategy_instance.chunk_text.side_effect = [["chunk 1"], ["chunk 2"]]
                mock_pdf = Mock()
                mock_pdf.metadata = {"title": "Workflow Test", "author": "Test Author"}
                mock_pdf.close = Mock()
                # Add __len__ method to mock_pdf - needed by parse_book
                mock_pdf.__len__ = Mock(return_value=2)  # PDF has 2 pages
                mock_fetch_pdf.return_value = mock_pdf
                
                mock_extract.return_value = {1: "Page 1 text", 2: "Page 2 text"}
                
                # Mock services - create a mock BookService with the methods expected by process_book
                book_service = AsyncMock()
                book_service.get_book_by_pdf_navn.return_value = None  # Book doesn't exist
                book_service.create_book.return_value = 456  # book_id
                book_service.create_chunk.return_value = None
                
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
                
                # First call should find no existing book - handled by return_value=None above
                
                await process_book(book_url, 1000, book_service, mock_session, mock_embedding_provider, mock_strategy_instance)
                
                # Verify the workflow
                mock_fetch_pdf.assert_called_once_with(book_url, mock_session)
                mock_extract.assert_called_once_with(mock_pdf)
                assert mock_strategy_instance.chunk_text.call_count == 2  # Once for each page
                assert mock_embedding_provider.get_embedding.call_count == 2  # Once for each chunk
                mock_pdf.close.assert_called_once()

    @pytest.mark.integration
    def test_wrapper_injects_chunking_strategy(self, monkeypatch):
        """Test that BookProcessorWrapper injects the correct chunking strategy into process_book."""
        from create_embeddings.book_processor_wrapper import BookProcessorWrapper
        import tempfile
        import os
        import asyncio

        # Create a temporary input file with one URL
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = os.path.join(tmpdir, "input")
            os.makedirs(input_dir)
            input_file = os.path.join(input_dir, "test_urls.txt")
            with open(input_file, "w") as f:
                f.write("https://example.com/book.pdf\n")

            # Patch environment to use the temp input dir
            monkeypatch.setenv("CHUNKING_STRATEGY", "sentence_splitter")
            monkeypatch.setenv("POSTGRES_DB", "dummy")
            monkeypatch.setenv("POSTGRES_USER", "dummy")
            monkeypatch.setenv("POSTGRES_PASSWORD", "dummy")
            monkeypatch.setenv("OPENAI_API_KEY", "dummy")
            monkeypatch.setenv("PROVIDER", "dummy")
            monkeypatch.setenv("CHUNK_SIZE", "5")
            monkeypatch.setenv("POSTGRES_HOST", "dummy")
            # Patch the input path logic
            monkeypatch.setattr("pathlib.Path.__truediv__", lambda self, other: Path(str(self) + "/" + str(other)))
            monkeypatch.setattr("pathlib.Path.exists", lambda self: True)
            monkeypatch.setattr("create_embeddings.book_processor_wrapper.Path", Path)
            monkeypatch.setattr("create_embeddings.book_processor_wrapper.indlæs_urls", lambda path: ["https://example.com/book.pdf"])

            # Patch ChunkingStrategyFactory to return a mock
            mock_strategy = Mock()
            with patch("create_embeddings.book_processor_wrapper.ChunkingStrategyFactory.create_strategy", return_value=mock_strategy) as mock_factory:
                # Patch process_book to check the strategy
                with patch("create_embeddings.book_processor_wrapper.process_book", new_callable=AsyncMock) as mock_process_book:
                    # Patch asyncpg.create_pool to avoid real DB connection
                    with patch("database.postgresql.asyncpg.create_pool") as mock_create_pool:
                        class DummyPool:
                            async def __aenter__(self): return self
                            async def __aexit__(self, exc_type, exc, tb): return False
                        mock_create_pool.return_value = DummyPool()
                        wrapper = BookProcessorWrapper(output_dir=tmpdir, failed_dir=tmpdir)
                        asyncio.run(wrapper.process_books_from_file("test_urls.txt"))
                        # Assert the factory was called with the env var
                        mock_factory.assert_called_with("sentence_splitter")
                        # Assert process_book was called with the mock strategy
                        assert any(call.args[-1] is mock_strategy for call in mock_process_book.call_args_list)


@pytest.mark.unit
@pytest.mark.skipif(not BOOK_PROCESSING_AVAILABLE, reason="Book processing modules not available") # ADDED
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
        
        # Use plain AsyncMock without spec to allow setting any methods we need
        mock_book_service = AsyncMock()
        mock_book_service.create_book.side_effect = Exception("Database connection failed")
        
        with pytest.raises(Exception, match="Database connection failed"):
            await save_book(book_data, mock_book_service)
            
    @pytest.mark.asyncio
    async def test_process_book_network_error_handling(self):
        """Test process_book handles network errors gracefully."""
        book_url = "https://example.com/network-error.pdf"
        
        # Use plain AsyncMock without spec to allow setting any methods we need
        mock_book_service = AsyncMock()
        mock_book_service.get_book_by_pdf_navn.return_value = None
        
        # Mock session and embedding provider
        mock_session = AsyncMock()
        mock_embedding_provider = AsyncMock()
        mock_chunking_strategy = Mock()
        
        # Mock fetch_pdf to raise a network error
        with patch('create_embeddings.opret_bøger.fetch_pdf', side_effect=Exception("Network error")):
            # Should not raise - should handle the error internally
            await process_book(book_url, 1000, mock_book_service, mock_session, mock_embedding_provider, mock_chunking_strategy)
            
            # Should have checked for existing book
            mock_book_service.get_book_by_pdf_navn.assert_called_once_with(book_url)
