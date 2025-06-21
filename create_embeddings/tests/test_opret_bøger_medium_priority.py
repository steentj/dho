"""
Medium priority tests for opret_bøger.py - core functionality tests.
"""
import pytest
import asyncio
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import aiohttp

# Add the src directory to the path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from create_embeddings.opret_bøger import (
        indlæs_urls,
        fetch_pdf,
        extract_text_by_page,
        parse_book,
        process_book,
        main,
        semaphore_guard
    )
    OPRET_BØGER_AVAILABLE = True
except ImportError as e:
    pytest.skip(f"Could not import opret_bøger modules: {e}", allow_module_level=True)
    OPRET_BØGER_AVAILABLE = False


@pytest.mark.unit
@pytest.mark.skipif(not OPRET_BØGER_AVAILABLE, reason="opret_bøger not available")
class TestOpretBøgerMediumPriority:
    """Medium priority tests for core opret_bøger functionality."""
    
    def test_indlæs_urls_with_valid_file(self):
        """Test loading URLs from a valid file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            tmp.write("https://example.com/book1.pdf\n")
            tmp.write("https://example.com/book2.pdf\n")
            tmp.write("\n")  # Empty line
            tmp.write("https://example.com/book3.pdf\n")
            tmp_path = tmp.name
        
        try:
            urls = indlæs_urls(tmp_path)
            assert len(urls) == 3
            assert "https://example.com/book1.pdf" in urls
            assert "https://example.com/book2.pdf" in urls
            assert "https://example.com/book3.pdf" in urls
        finally:
            os.unlink(tmp_path)
    
    def test_indlæs_urls_with_empty_lines(self):
        """Test loading URLs while ignoring empty lines."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            tmp.write("  \n")  # Whitespace only
            tmp.write("https://example.com/book1.pdf\n")
            tmp.write("   \t   \n")  # More whitespace
            tmp_path = tmp.name
        
        try:
            urls = indlæs_urls(tmp_path)
            assert len(urls) == 1
            assert urls[0] == "https://example.com/book1.pdf"
        finally:
            os.unlink(tmp_path)
    
    def test_indlæs_urls_file_not_found(self):
        """Test indlæs_urls with non-existent file."""
        with pytest.raises(FileNotFoundError):
            indlæs_urls("nonexistent_file.txt")    @pytest.mark.asyncio
    async def test_fetch_pdf_success(self):
        """Test successful PDF fetching."""
        # Mock PDF content
        mock_pdf_content = b"%PDF-1.4 mock content"
        
        # Mock the entire fetch_pdf function to avoid context manager issues
        with patch('create_embeddings.opret_bøger.fitz.open') as mock_fitz:
            mock_pdf_doc = Mock()
            mock_fitz.return_value = mock_pdf_doc
    
            # Create a test session
            mock_session = Mock()
            
            # Mock response object
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.read = AsyncMock(return_value=mock_pdf_content)
            
            # Create a proper async context manager
            class AsyncContextManager:
                async def __aenter__(self):
                    return mock_response
                async def __aexit__(self, exc_type, exc, tb):
                    return None
            
            # Set up session get to return our context manager
            mock_session.get = Mock(return_value=AsyncContextManager())
    
            result = await fetch_pdf("https://example.com/test.pdf", mock_session)
            
            assert result == mock_pdf_doc
            mock_fitz.assert_called_once_with(stream=mock_pdf_content, filetype="pdf")

    @pytest.mark.asyncio
    async def test_fetch_pdf_http_error(self):
        """Test PDF fetching with HTTP error."""
        # Create a test session
        mock_session = Mock()
        
        # Mock response with error status
        mock_response = AsyncMock()
        mock_response.status = 404
        
        # Create a proper async context manager
        class AsyncContextManager:
            async def __aenter__(self):
                return mock_response
            async def __aexit__(self, exc_type, exc, tb):
                return None
        
        # Set up session get to return our context manager
        mock_session.get = Mock(return_value=AsyncContextManager())
        
        result = await fetch_pdf("https://example.com/nonexistent.pdf", mock_session)
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_pdf_network_error(self):
        """Test PDF fetching with network error."""
        # Create a test session
        mock_session = Mock()
        
        # Create a context manager that raises an exception
        class ErrorContextManager:
            async def __aenter__(self):
                raise aiohttp.ClientError("Network error")
            async def __aexit__(self, exc_type, exc, tb):
                return None
        
        # Set up session get to return our error-raising context manager
        mock_session.get = Mock(return_value=ErrorContextManager())
        
        result = await fetch_pdf("https://example.com/test.pdf", mock_session)
        assert result is None
    
    def test_extract_text_by_page(self):
        """Test text extraction from PDF pages."""
        # Mock PDF document
        mock_pdf = Mock()
        mock_pdf.__len__ = Mock(return_value=2)  # 2 pages
        
        # Mock pages with text content
        mock_page1 = Mock()
        mock_page1.get_text.return_value = "Page 1 content with\xad\nsoft hyphen and-\nhard hyphen"
        
        mock_page2 = Mock()
        mock_page2.get_text.return_value = "Page 2 content with- \nspaced hyphen"
        
        mock_pdf.__getitem__ = Mock(side_effect=lambda i: [mock_page1, mock_page2][i])
        
        result = extract_text_by_page(mock_pdf)
        
        assert len(result) == 2
        assert result[1] == "Page 1 content withsoft hyphen andhard hyphen"
        assert result[2] == "Page 2 content withspaced hyphen"
    
    @pytest.mark.asyncio
    async def test_parse_book_with_metadata(self):
        """Test parsing a book with proper metadata."""
        # Mock PDF with metadata
        mock_pdf = Mock()
        mock_pdf.metadata = {"title": "Test Book", "author": "Test Author"}
        mock_pdf.__len__ = Mock(return_value=1)
        mock_pdf.close = Mock()
        
        # Mock text extraction
        with patch('create_embeddings.opret_bøger.extract_text_by_page') as mock_extract:
            mock_extract.return_value = {1: "Page 1 content"}
            
            # Mock chunking strategy
            mock_strategy = Mock()
            mock_strategy.chunk_text.return_value = ["Chunk 1", "Chunk 2"]
            
            # Mock embedding provider
            mock_embedding_provider = AsyncMock()
            mock_embedding_provider.get_embedding.side_effect = [
                [0.1, 0.2, 0.3],  # Chunk 1 embedding
                [0.4, 0.5, 0.6]   # Chunk 2 embedding
            ]
            
            result = await parse_book(
                mock_pdf, "https://example.com/test.pdf", 1000, 
                mock_embedding_provider, mock_strategy
            )
            
            assert result["pdf-url"] == "https://example.com/test.pdf"
            assert result["titel"] == "Test Book"
            assert result["forfatter"] == "Test Author"
            assert result["sider"] == 1
            assert len(result["chunks"]) == 2
            assert len(result["embeddings"]) == 2
            assert result["chunks"][0] == (1, "Chunk 1")
            assert result["chunks"][1] == (1, "Chunk 2")
            mock_pdf.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_parse_book_without_metadata(self):
        """Test parsing a book without metadata."""
        # Mock PDF without metadata
        mock_pdf = Mock()
        mock_pdf.metadata = None
        mock_pdf.__len__ = Mock(return_value=1)
        mock_pdf.close = Mock()
        
        # Mock text extraction
        with patch('create_embeddings.opret_bøger.extract_text_by_page') as mock_extract:
            mock_extract.return_value = {1: "Page content"}
            
            # Mock chunking strategy
            mock_strategy = Mock()
            mock_strategy.chunk_text.return_value = ["Single chunk"]
            
            # Mock embedding provider
            mock_embedding_provider = AsyncMock()
            mock_embedding_provider.get_embedding.return_value = [0.1, 0.2, 0.3]
            
            result = await parse_book(
                mock_pdf, "https://example.com/test.pdf", 1000,
                mock_embedding_provider, mock_strategy
            )
            
            assert result["titel"] == "Ukendt Titel"
            assert result["forfatter"] == "Ukendt Forfatter"
            mock_pdf.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_parse_book_filters_empty_chunks(self):
        """Test that parse_book filters out empty chunks."""
        # Mock PDF
        mock_pdf = Mock()
        mock_pdf.metadata = {"title": "Test Book", "author": "Test Author"}
        mock_pdf.__len__ = Mock(return_value=1)
        mock_pdf.close = Mock()
        
        # Mock text extraction
        with patch('create_embeddings.opret_bøger.extract_text_by_page') as mock_extract:
            mock_extract.return_value = {1: "Page content"}
            
            # Mock chunking strategy that returns empty chunks
            mock_strategy = Mock()
            mock_strategy.chunk_text.return_value = ["Valid chunk", "   ", "", "Another valid chunk"]
            
            # Mock embedding provider
            mock_embedding_provider = AsyncMock()
            mock_embedding_provider.get_embedding.side_effect = [
                [0.1, 0.2, 0.3],  # Valid chunk 1
                [0.4, 0.5, 0.6]   # Valid chunk 2
            ]
            
            result = await parse_book(
                mock_pdf, "https://example.com/test.pdf", 1000,
                mock_embedding_provider, mock_strategy
            )
            
            # Should only have 2 valid chunks, empty ones filtered out
            assert len(result["chunks"]) == 2
            assert len(result["embeddings"]) == 2
            assert result["chunks"][0] == (1, "Valid chunk")
            assert result["chunks"][1] == (1, "Another valid chunk")
    
    @pytest.mark.asyncio
    async def test_semaphore_guard(self):
        """Test semaphore guard functionality."""
        # Track execution order
        execution_order = []
        
        async def mock_coro(name, delay):
            execution_order.append(f"{name}_start")
            await asyncio.sleep(delay)
            execution_order.append(f"{name}_end")
        
        # Create semaphore that allows only 1 concurrent operation
        semaphore = asyncio.Semaphore(1)
        
        # Start two operations concurrently but semaphore should serialize them
        task1 = asyncio.create_task(semaphore_guard(mock_coro, semaphore, "task1", 0.1))
        task2 = asyncio.create_task(semaphore_guard(mock_coro, semaphore, "task2", 0.1))
        
        await asyncio.gather(task1, task2)
        
        # Due to semaphore, one task should complete before the other starts
        assert execution_order[0] in ["task1_start", "task2_start"]
        assert execution_order[1] in ["task1_end", "task2_end"]
        assert execution_order[2] in ["task1_start", "task2_start"]
        assert execution_order[3] in ["task1_end", "task2_end"]
        
        # The task that started first should also end first
        if execution_order[0] == "task1_start":
            assert execution_order[1] == "task1_end"
            assert execution_order[2] == "task2_start"
        else:
            assert execution_order[1] == "task2_end"
            assert execution_order[2] == "task1_start"


@pytest.mark.unit 
@pytest.mark.skipif(not OPRET_BØGER_AVAILABLE, reason="opret_bøger not available")
class TestMainFunctionAndConfiguration:
    """Test the main function and configuration handling."""
    
    @pytest.mark.asyncio
    async def test_main_missing_database_url(self):
        """Test main function with missing DATABASE_URL."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('create_embeddings.opret_bøger.logging') as mock_logging:
                with patch('create_embeddings.opret_bøger.load_dotenv'):
                    result = await main()
                    assert result is None  # Function returns None when DATABASE_URL is missing
                    mock_logging.error.assert_called_with("DATABASE_URL environment variable is required")
    
    @pytest.mark.asyncio 
    async def test_main_with_valid_config(self):
        """Test main function with valid configuration."""
        # Mock environment variables
        env_vars = {
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'OPENAI_API_KEY': 'test-key',
            'PROVIDER': 'dummy',
            'CHUNK_SIZE': '500',
            'URL_FILE': 'test_urls.txt',
            'CHUNKING_STRATEGY': 'sentence_splitter'
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test URL file
            url_file_path = os.path.join(tmpdir, 'test_urls.txt')
            with open(url_file_path, 'w') as f:
                f.write("https://example.com/test.pdf\n")
            
            with patch.dict('os.environ', env_vars):
                with patch('create_embeddings.opret_bøger.load_dotenv'):
                    with patch('create_embeddings.opret_bøger.os.path.dirname', return_value=tmpdir):
                        with patch('create_embeddings.opret_bøger.os.path.abspath', return_value=os.path.join(tmpdir, 'fake_script.py')):
                            with patch('create_embeddings.opret_bøger.PostgreSQLService') as mock_db_service_class:
                                with patch('create_embeddings.opret_bøger.BookService') as mock_book_service_class:
                                    with patch('create_embeddings.opret_bøger.setup_logging'):
                                        with patch('aiohttp.ClientSession') as mock_session:
                                            # Mock database service
                                            mock_db_service = AsyncMock()
                                            mock_db_service_class.return_value = mock_db_service
                                            
                                            # Mock book service  
                                            mock_book_service = AsyncMock()
                                            mock_book_service_class.return_value = mock_book_service
                                            
                                            # Mock session context manager
                                            mock_session_instance = AsyncMock()
                                            mock_context_manager = AsyncMock()
                                            mock_context_manager.__aenter__ = AsyncMock(return_value=mock_session_instance)
                                            mock_context_manager.__aexit__ = AsyncMock(return_value=None)
                                            mock_session.return_value = mock_context_manager
                                            
                                            # Mock asyncio.gather to avoid actual processing
                                            with patch('asyncio.gather', new_callable=AsyncMock) as mock_gather:
                                                await main()
                                                
                                                # Verify database service was connected and disconnected
                                                mock_db_service.connect.assert_called_once()
                                                mock_db_service.disconnect.assert_called_once()
                                                
                                                # Verify tasks were created and gathered
                                                mock_gather.assert_called_once()


@pytest.mark.integration
@pytest.mark.skipif(not OPRET_BØGER_AVAILABLE, reason="opret_bøger not available")
class TestOpretBøgerIntegration:
    """Integration tests for opret_bøger workflow."""
    
    @pytest.mark.asyncio
    async def test_process_book_integration_workflow(self):
        """Test the complete process_book workflow integration."""
        book_url = "https://example.com/integration-test.pdf"
        
        # Mock book service
        mock_book_service = AsyncMock()
        mock_book_service.get_book_by_pdf_navn.return_value = None  # Book doesn't exist
        
        # Mock session and PDF fetching
        mock_session = AsyncMock()
        
        # Mock embedding provider
        mock_embedding_provider = AsyncMock()
        mock_embedding_provider.get_embedding.return_value = [0.1, 0.2, 0.3]
        
        # Mock chunking strategy
        mock_chunking_strategy = Mock()
        
        # Mock the complete workflow
        with patch('create_embeddings.opret_bøger.fetch_pdf') as mock_fetch:
            with patch('create_embeddings.opret_bøger.parse_book') as mock_parse:
                with patch('create_embeddings.opret_bøger.save_book') as mock_save:
                    # Setup mock returns
                    mock_pdf = Mock()
                    mock_fetch.return_value = mock_pdf
                    
                    mock_book_data = {
                        "pdf-url": book_url,
                        "titel": "Integration Test Book",
                        "forfatter": "Test Author",
                        "sider": 1,
                        "chunks": [(1, "Test chunk")],
                        "embeddings": [[0.1, 0.2, 0.3]]
                    }
                    mock_parse.return_value = mock_book_data
                    
                    # Execute the workflow
                    await process_book(
                        book_url, 1000, mock_book_service, mock_session,
                        mock_embedding_provider, mock_chunking_strategy
                    )
                    
                    # Verify the complete workflow was executed
                    mock_book_service.get_book_by_pdf_navn.assert_called_once_with(book_url)
                    mock_fetch.assert_called_once_with(book_url, mock_session)
                    mock_parse.assert_called_once_with(
                        mock_pdf, book_url, 1000, mock_embedding_provider, mock_chunking_strategy
                    )
                    mock_save.assert_called_once_with(mock_book_data, mock_book_service)
    
    @pytest.mark.asyncio
    async def test_process_book_skips_existing_book_integration(self):
        """Test that process_book properly skips existing books."""
        book_url = "https://example.com/existing-book.pdf"
        
        # Mock book service that returns existing book
        mock_book_service = AsyncMock()
        existing_book = {"id": 123, "title": "Existing Book"}
        mock_book_service.get_book_by_pdf_navn.return_value = existing_book
        
        # Mock other dependencies (should not be called)
        mock_session = AsyncMock()
        mock_embedding_provider = AsyncMock()
        mock_chunking_strategy = Mock()
        
        with patch('create_embeddings.opret_bøger.fetch_pdf') as mock_fetch:
            await process_book(
                book_url, 1000, mock_book_service, mock_session,
                mock_embedding_provider, mock_chunking_strategy
            )
            
            # Verify book existence was checked
            mock_book_service.get_book_by_pdf_navn.assert_called_once_with(book_url)
            
            # Verify PDF fetching was skipped
            mock_fetch.assert_not_called()
