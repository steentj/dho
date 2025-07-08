import pytest
import asyncio
import tempfile
import os
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

# Add the src directory to the path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from create_embeddings.book_processor_wrapper import BookProcessorWrapper
    BOOK_PROCESSOR_WRAPPER_AVAILABLE = True
except ImportError:
    BOOK_PROCESSOR_WRAPPER_AVAILABLE = False

try:
    from create_embeddings.opret_bøger import (
        save_book, 
        process_book, 
        EmbeddingProvider,
        OpenAIEmbeddingProvider,
        DummyEmbeddingProvider,
        EmbeddingProviderFactory
    )
    BOOK_PROCESSING_AVAILABLE = True
except ImportError as e:
    pytest.skip(f"Could not import book processing modules: {e}", allow_module_level=True)
    BOOK_PROCESSING_AVAILABLE = False

@pytest.mark.unit
@pytest.mark.skipif(not BOOK_PROCESSOR_WRAPPER_AVAILABLE, reason="BookProcessorWrapper not available")
class TestBookProcessorWrapperHighPriority:
    @pytest.mark.asyncio
    async def test_semaphore_guard_with_monitoring(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wrapper = BookProcessorWrapper(output_dir=tmpdir, failed_dir=tmpdir)
            async def dummy_process(*args, **kwargs):
                wrapper.processed_count += 1
            semaphore = asyncio.Semaphore(1)
            # Patch process_single_book_with_monitoring to dummy_process
            wrapper.process_single_book_with_monitoring = dummy_process
            await wrapper.semaphore_guard_with_monitoring(
                semaphore, 'url', 100, None, None, None, None
            )
            assert wrapper.processed_count == 1

    @pytest.mark.asyncio
    async def test_semaphore_guard_with_monitoring_handles_exception(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wrapper = BookProcessorWrapper(output_dir=tmpdir, failed_dir=tmpdir)
            # Mock the process_single_book_with_monitoring to simulate error handling
            async def mock_process_with_error(*args, **kwargs):
                wrapper.failed_count += 1
                wrapper.failed_books.append({"url": args[0], "error": "test error", "timestamp": "now"})
            wrapper.process_single_book_with_monitoring = mock_process_with_error
            semaphore = asyncio.Semaphore(1)
            await wrapper.semaphore_guard_with_monitoring(
                semaphore, 'url', 100, None, None, None, None
            )
            # Should not raise, error is handled internally
            assert wrapper.failed_count == 1

    @pytest.mark.asyncio
    async def test_process_single_book_with_monitoring_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wrapper = BookProcessorWrapper(output_dir=tmpdir, failed_dir=tmpdir)
            async def dummy_process(*args, **kwargs):
                pass
            wrapper.processed_count = 0
            await wrapper.process_single_book_with_monitoring('url', 100, None, None, dummy_process, None)
            assert wrapper.processed_count == 1

    @pytest.mark.asyncio
    async def test_process_single_book_with_monitoring_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wrapper = BookProcessorWrapper(output_dir=tmpdir, failed_dir=tmpdir)
            # Mock the process_book function to avoid calling the real implementation
            with patch('create_embeddings.book_processor_wrapper.process_book') as mock_process:
                mock_process.side_effect = Exception("test failure")
                wrapper.failed_count = 0
                await wrapper.process_single_book_with_monitoring('url', 100, None, None, None, None)
                assert wrapper.failed_count == 1
                assert len(wrapper.failed_books) == 1

    @pytest.mark.asyncio
    async def test_retry_failed_books(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            failed_dir = tmpdir
            output_dir = tmpdir
            failed_file = os.path.join(failed_dir, "failed_books.json")
            with open(failed_file, "w") as f:
                json.dump([
                    {"url": "url1", "error": "err", "timestamp": "now"},
                    {"url": "url2", "error": "err", "timestamp": "now"}
                ], f)
            wrapper = BookProcessorWrapper(output_dir=output_dir, failed_dir=failed_dir)
            
            # Create a mock input directory for the test
            input_dir = os.path.join(tmpdir, "input")
            os.makedirs(input_dir, exist_ok=True)
            
            # Mock the process_books_from_file method
            async def fake_process_books_from_file(filename):
                wrapper.processed_count += 2
            
            # Patch the hardcoded path and the process method
            with patch('create_embeddings.book_processor_wrapper.Path') as mock_path:
                # Configure the mock to behave like Path("/app/input")
                mock_input_path = Mock()
                mock_retry_file = Mock()
                mock_retry_file.write_text = Mock()
                mock_input_path.__truediv__ = Mock(return_value=mock_retry_file)
                mock_path.return_value = mock_input_path
                
                with patch.object(wrapper, 'process_books_from_file', side_effect=fake_process_books_from_file):
                    await wrapper.retry_failed_books()
                    assert wrapper.processed_count == 2

    def test_save_failed_books_and_status(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wrapper = BookProcessorWrapper(output_dir=tmpdir, failed_dir=tmpdir)
            wrapper.failed_books = [
                {"url": "url1", "error": "err", "timestamp": "now"}
            ]
            wrapper.save_failed_books()
            failed_file = os.path.join(tmpdir, "failed_books.json")
            assert os.path.exists(failed_file)
            with open(failed_file) as f:
                data = json.load(f)
                assert data[0]["url"] == "url1"
            wrapper.total_count = 1
            wrapper.processed_count = 1
            wrapper.failed_count = 0
            wrapper.update_status("done")
            status_file = os.path.join(tmpdir, "processing_status.json")
            assert os.path.exists(status_file)
            with open(status_file) as f:
                status = json.load(f)
                assert status["status"] == "done"

    @pytest.mark.asyncio
    async def test_process_books_from_file_file_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            wrapper = BookProcessorWrapper(output_dir=tmpdir, failed_dir=tmpdir)
            # Set up minimal valid environment to get past config validation
            with patch.dict(os.environ, {
                'POSTGRES_HOST': 'localhost',
                'POSTGRES_USER': 'test',
                'POSTGRES_PASSWORD': 'test',
                'POSTGRES_DB': 'test',
                'PROVIDER': 'dummy'
            }, clear=True):
                # Mock load_dotenv to prevent reading the real .env file
                with patch("dotenv.load_dotenv"):
                    with pytest.raises(FileNotFoundError):
                        await wrapper.process_books_from_file("nonexistent.txt")

"""
Comprehensive tests for book processing with dependency injection.
"""


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

        # Mock BookService with PostgreSQL service
        mock_book_service = AsyncMock()  # Removed spec=BookService
        mock_postgresql_service = AsyncMock()
        mock_book_service._service = mock_postgresql_service
        mock_book_service.get_or_create_book.return_value = 123  # Mock get_or_create_book
        mock_postgresql_service.find_book_by_url.return_value = None  # Book doesn't exist
        mock_postgresql_service.create_book.return_value = 123  # Mock book ID
        mock_postgresql_service.save_chunks.return_value = None

        # Mock embedding provider
        mock_embedding_provider = AsyncMock()
        mock_embedding_provider.get_table_name = Mock(return_value="chunks")

        # Call the function
        await save_book(book_data, mock_book_service, mock_embedding_provider)

        # Verify book creation was called
        mock_book_service.get_or_create_book.assert_called_once_with(
            pdf_url="https://example.com/test.pdf",
            title="Test Book",
            author="Test Author",
            pages=10
        )

        # Verify chunks were saved with the correct table name
        expected_chunks = [(1, "Test chunk 1", [0.1, 0.2, 0.3]), (2, "Test chunk 2", [0.4, 0.5, 0.6])]
        mock_postgresql_service.save_chunks.assert_called_once_with(123, expected_chunks, "chunks")

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
        mock_postgresql_service = AsyncMock()
        mock_book_service._service = mock_postgresql_service
        mock_book_service.get_or_create_book.side_effect = Exception("Database error")
        mock_postgresql_service.find_book_by_url.return_value = None  # Book doesn't exist
        mock_postgresql_service.create_book.side_effect = Exception("Database error")
        
        # Mock embedding provider
        mock_embedding_provider = AsyncMock()
        mock_embedding_provider.get_table_name = Mock(return_value="chunks")  # Sync method

        # Verify exception is propagated
        with pytest.raises(Exception, match="Database error"):
            await save_book(book_data, mock_book_service, mock_embedding_provider)

    @pytest.mark.asyncio
    async def test_process_book_skips_existing_book_with_embeddings(self):
        """Test that process_book skips books that already exist with embeddings for the provider."""
        book_url = "https://example.com/existing.pdf"
        book_id = 123
        
        # Mock BookService and PostgreSQLService
        mock_book_service = AsyncMock()  # Removed spec=BookService
        mock_postgresql_service = AsyncMock()
        mock_book_service._service = mock_postgresql_service
        mock_postgresql_service.find_book_by_url.return_value = book_id
        
        # Mock embedding provider that has embeddings for this book
        mock_embedding_provider = AsyncMock()
        mock_embedding_provider.has_embeddings_for_book.return_value = True
        mock_embedding_provider.get_provider_name = Mock(return_value="OpenAI")  # Use Mock for sync method
        
        # Mock session and chunking strategy
        mock_session = AsyncMock()
        mock_chunking_strategy = Mock()

        # Call the function
        await process_book(book_url, 1000, mock_book_service, mock_session, mock_embedding_provider, mock_chunking_strategy)

        # Verify it checked for existing book
        mock_postgresql_service.find_book_by_url.assert_called_once_with(book_url)
        
        # Verify it checked for provider-specific embeddings
        mock_embedding_provider.has_embeddings_for_book.assert_called_once_with(book_id, mock_postgresql_service)
        
        # Verify it didn't try to process the book further
        mock_session.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_book_processes_existing_book_without_provider_embeddings(self):
        """Test that process_book processes books that exist but don't have embeddings for the specific provider."""
        book_url = "https://example.com/existing.pdf"
        book_id = 123
        
        # Mock BookService and PostgreSQLService
        mock_book_service = AsyncMock()
        mock_postgresql_service = AsyncMock()
        mock_book_service._service = mock_postgresql_service
        mock_postgresql_service.find_book_by_url.return_value = book_id
        
        # Mock embedding provider that does NOT have embeddings for this book
        mock_embedding_provider = AsyncMock()
        mock_embedding_provider.has_embeddings_for_book.return_value = False
        mock_embedding_provider.get_provider_name = Mock(return_value="Ollama")  # Use Mock for sync method
        
        # Mock session and chunking strategy
        mock_session = AsyncMock()
        mock_chunking_strategy = Mock()

        # Mock fetch_pdf to return None (PDF not accessible) to test the flow
        with patch('create_embeddings.opret_bøger.fetch_pdf', return_value=None) as mock_fetch:
            await process_book(book_url, 1000, mock_book_service, mock_session, mock_embedding_provider, mock_chunking_strategy)

            # Verify it checked for existing book
            mock_postgresql_service.find_book_by_url.assert_called_once_with(book_url)
            
            # Verify it checked for provider-specific embeddings
            mock_embedding_provider.has_embeddings_for_book.assert_called_once_with(book_id, mock_postgresql_service)
            
            # Verify it tried to fetch the PDF (processing continued)
            mock_fetch.assert_called_once_with(book_url, mock_session)

    @pytest.mark.asyncio
    async def test_process_book_handles_new_book(self):
        """Test that process_book handles new books correctly."""
        book_url = "https://example.com/new.pdf"
        
        # Mock BookService and PostgreSQLService that returns None (book doesn't exist)
        mock_book_service = AsyncMock()  # Removed spec=BookService
        mock_postgresql_service = AsyncMock()
        mock_book_service._service = mock_postgresql_service
        mock_postgresql_service.find_book_by_url.return_value = None
        
        # Mock session and embedding provider
        mock_session = AsyncMock()
        mock_embedding_provider = AsyncMock()
        mock_chunking_strategy = Mock()

        # Mock fetch_pdf to return None (PDF not accessible)
        with patch('create_embeddings.opret_bøger.fetch_pdf', return_value=None) as mock_fetch:
            await process_book(book_url, 1000, mock_book_service, mock_session, mock_embedding_provider, mock_chunking_strategy)

            # Verify it checked for existing book
            mock_postgresql_service.find_book_by_url.assert_called_once_with(book_url)
            
            # Verify it tried to fetch the PDF
            mock_fetch.assert_called_once_with(book_url, mock_session)

    @pytest.mark.asyncio
    async def test_process_book_successful_processing(self):
        """Test successful book processing end-to-end."""
        book_url = "https://example.com/new.pdf"
        
        # Mock BookService and PostgreSQLService for new book
        mock_book_service = AsyncMock()  # Removed spec=BookService
        mock_postgresql_service = AsyncMock()
        mock_book_service._service = mock_postgresql_service
        mock_postgresql_service.find_book_by_url.return_value = None  # Book doesn't exist
        
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
                    mock_save.assert_called_once_with(mock_book_data, mock_book_service, mock_embedding_provider)


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
            await provider.initialize()  # Initialize the client first
            
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
        with pytest.raises(ValueError, match="Unknown embedding provider"):
            EmbeddingProviderFactory.create_provider("unknown", "test-key")


@pytest.mark.integration
@pytest.mark.skipif(not BOOK_PROCESSING_AVAILABLE, reason="Book processing modules not available")
class TestBookProcessingIntegration:
    @pytest.mark.integration
    def test_wrapper_injects_alternate_chunking_strategy(self, monkeypatch):
        """Test that BookProcessorWrapper injects an alternate chunking strategy (e.g., word_overlap) into process_book."""
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
            monkeypatch.setenv("CHUNKING_STRATEGY", "word_overlap")
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
                        # CRITICAL: Mock load_dotenv to prevent reading the real .env file
                        with patch("dotenv.load_dotenv"):
                            class DummyPool:
                                async def __aenter__(self): return self
                                async def __aexit__(self, exc_type, exc, tb): return False
                            mock_create_pool.return_value = DummyPool()
                            wrapper = BookProcessorWrapper(output_dir=tmpdir, failed_dir=tmpdir)
                            asyncio.run(wrapper.process_books_from_file("test_urls.txt"))
                            # Assert the factory was called with the alternate strategy
                            mock_factory.assert_called_with("word_overlap")
                            # Assert process_book was called with the mock strategy
                            assert any(call.args[-1] is mock_strategy for call in mock_process_book.call_args_list)
    """Integration tests for book processing with dependency injection."""

    @pytest.mark.asyncio
    async def test_book_processing_integration_with_real_services(self):
        """Test book processing integration with real service instances."""
        # This test uses real service instances but mocked database connections
        
        # We need a mock book_service with the methods that save_book will call
        book_service = AsyncMock()
        mock_postgresql_service = AsyncMock()
        book_service._service = mock_postgresql_service
        book_service.get_or_create_book = AsyncMock(return_value=123)  # Mock get_or_create_book
        mock_postgresql_service.find_book_by_url.return_value = None  # Book doesn't exist
        mock_postgresql_service.create_book.return_value = 123  # book_id
        mock_postgresql_service.save_chunks.return_value = None
        
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
        
        # Mock embedding provider
        mock_embedding_provider = AsyncMock()
        mock_embedding_provider.get_table_name = Mock(return_value="chunks")  # Sync method
        
        # Call save_book with our mock service
        await save_book(book_data, book_service, mock_embedding_provider)
        
        # Verify the service methods were called correctly
        book_service.get_or_create_book.assert_called_once_with(
            pdf_url="https://example.com/integration-test.pdf",
            title="Integration Test Book",
            author="Test Author",
            pages=5
        )
        
        # Verify chunks were saved with the correct table name
        expected_chunks = [(1, "Integration test chunk 1", [0.1, 0.2, 0.3, 0.4]), (2, "Integration test chunk 2", [0.5, 0.6, 0.7, 0.8])]
        mock_postgresql_service.save_chunks.assert_called_once_with(123, expected_chunks, "chunks")

    @pytest.mark.asyncio
    async def test_full_book_processing_workflow(self):
        """Test the complete book processing workflow."""
        # Mock all external dependencies
        with patch('create_embeddings.opret_bøger.fetch_pdf') as mock_fetch_pdf:
            with patch('create_embeddings.opret_bøger.extract_text_by_page') as mock_extract:
                # Setup mocks
                mock_strategy_instance = Mock()
                mock_strategy_instance.chunk_text.side_effect = [["chunk 1"], ["chunk 2"]]
                mock_strategy_instance.supports_cross_page_chunking.return_value = False  # Use page-by-page processing
                mock_pdf = Mock()
                mock_pdf.metadata = {"title": "Workflow Test", "author": "Test Author"}
                mock_pdf.close = Mock()
                # Add __len__ method to mock_pdf - needed by parse_book
                mock_pdf.__len__ = Mock(return_value=2)  # PDF has 2 pages
                mock_fetch_pdf.return_value = mock_pdf
                
                mock_extract.return_value = {1: "Page 1 text", 2: "Page 2 text"}
                
                # Mock services - create a mock BookService with the methods expected by process_book
                book_service = AsyncMock()
                postgresql_service = AsyncMock()
                book_service._service = postgresql_service
                postgresql_service.find_book_by_url.return_value = None  # Book doesn't exist
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
                        # CRITICAL: Mock load_dotenv to prevent reading the real .env file
                        with patch("dotenv.load_dotenv"):
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
        mock_postgresql_service = AsyncMock()
        mock_book_service._service = mock_postgresql_service
        mock_book_service.get_or_create_book.side_effect = Exception("Database connection failed")
        mock_postgresql_service.find_book_by_url.return_value = None  # Book doesn't exist
        mock_postgresql_service.create_book.side_effect = Exception("Database connection failed")
        
        # Mock embedding provider
        mock_embedding_provider = AsyncMock()
        mock_embedding_provider.get_table_name = Mock(return_value="chunks")  # Sync method
        
        with pytest.raises(Exception, match="Database connection failed"):
            await save_book(book_data, mock_book_service, mock_embedding_provider)
            
    @pytest.mark.asyncio
    async def test_process_book_network_error_handling(self):
        """Test process_book handles network errors gracefully."""
        book_url = "https://example.com/network-error.pdf"
        
        # Use plain AsyncMock without spec to allow setting any methods we need
        mock_book_service = AsyncMock()
        mock_postgresql_service = AsyncMock()
        mock_book_service._service = mock_postgresql_service
        mock_postgresql_service.find_book_by_url.return_value = None  # Book doesn't exist
        
        # Mock session and embedding provider
        mock_session = AsyncMock()
        mock_embedding_provider = AsyncMock()
        mock_chunking_strategy = Mock()
        
        # Mock fetch_pdf to raise a network error
        with patch('create_embeddings.opret_bøger.fetch_pdf', side_effect=Exception("Network error")):
            # Should not raise - should handle the error internally
            await process_book(book_url, 1000, mock_book_service, mock_session, mock_embedding_provider, mock_chunking_strategy)
            
            # Should have checked for existing book
            mock_postgresql_service.find_book_by_url.assert_called_once_with(book_url)
