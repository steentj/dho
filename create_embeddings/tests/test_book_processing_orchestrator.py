"""
Tests for book processing orchestrator module.

This module tests the application orchestration layer that coordinates the complete
book processing workflow, including dependency injection setup and resource management.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from create_embeddings.book_processing_orchestrator import (
    BookProcessingOrchestrator, 
    BookProcessingApplication
)


class TestBookProcessingOrchestrator:
    """Test the BookProcessingOrchestrator class."""
    
    def test_orchestrator_initialization(self):
        """Test that orchestrator initializes with correct parameters."""
        orchestrator = BookProcessingOrchestrator(
            database_url="postgresql://test",
            provider_name="dummy",
            api_key="test-key",
            chunking_strategy_name="sentence_splitter",
            chunk_size=1000,
            concurrency_limit=3
        )
        
        assert orchestrator.database_url == "postgresql://test"
        assert orchestrator.provider_name == "dummy"
        assert orchestrator.api_key == "test-key"
        assert orchestrator.chunking_strategy_name == "sentence_splitter"
        assert orchestrator.chunk_size == 1000
        assert orchestrator.concurrency_limit == 3
        assert orchestrator.embedding_provider is None
        assert orchestrator.chunking_strategy is None
        assert orchestrator.book_service is None
    
    @pytest.mark.asyncio
    async def test_setup_dependencies(self):
        """Test dependency setup using factories."""
        orchestrator = BookProcessingOrchestrator(
            database_url="postgresql://test",
            provider_name="dummy",
            api_key="test-key",
            chunking_strategy_name="sentence_splitter",
            chunk_size=1000
        )
        
        mock_embedding_provider = MagicMock()
        mock_chunking_strategy = MagicMock()
        mock_book_service = AsyncMock()
        
        with patch("create_embeddings.book_processing_orchestrator.EmbeddingProviderFactory.create_provider") as mock_provider_factory:
            with patch("create_embeddings.book_processing_orchestrator.ChunkingStrategyFactory.create_strategy") as mock_strategy_factory:
                with patch("create_embeddings.book_processing_orchestrator.create_postgresql_pool_service") as mock_service_factory:
                    
                    mock_provider_factory.return_value = mock_embedding_provider
                    mock_strategy_factory.return_value = mock_chunking_strategy
                    mock_service_factory.return_value = mock_book_service
                    
                    await orchestrator.setup_dependencies()
                    
                    # Verify factory calls
                    mock_provider_factory.assert_called_once_with("dummy", "test-key")
                    mock_strategy_factory.assert_called_once_with("sentence_splitter")
                    mock_service_factory.assert_called_once()
                    
                    # Verify dependencies are set
                    assert orchestrator.embedding_provider == mock_embedding_provider
                    assert orchestrator.chunking_strategy == mock_chunking_strategy
                    assert orchestrator.book_service == mock_book_service
    
    @pytest.mark.asyncio
    async def test_cleanup_resources(self):
        """Test that cleanup properly disconnects services."""
        orchestrator = BookProcessingOrchestrator(
            database_url="postgresql://test",
            provider_name="dummy",
            api_key="test-key",
            chunking_strategy_name="sentence_splitter",
            chunk_size=1000
        )
        
        mock_book_service = AsyncMock()
        orchestrator.book_service = mock_book_service
        
        await orchestrator.cleanup_resources()
        
        mock_book_service.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_resources_handles_none_service(self):
        """Test cleanup handles None service gracefully."""
        orchestrator = BookProcessingOrchestrator(
            database_url="postgresql://test",
            provider_name="dummy",
            api_key="test-key",
            chunking_strategy_name="sentence_splitter",
            chunk_size=1000
        )
        
        # Should not raise exception
        await orchestrator.cleanup_resources()
    
    @pytest.mark.asyncio
    async def test_process_books_from_urls_empty_list(self):
        """Test processing empty URL list."""
        orchestrator = BookProcessingOrchestrator(
            database_url="postgresql://test",
            provider_name="dummy",
            api_key="test-key",
            chunking_strategy_name="sentence_splitter",
            chunk_size=1000
        )
        
        # Should handle empty list gracefully
        await orchestrator.process_books_from_urls([])
    
    @pytest.mark.asyncio
    async def test_process_books_from_urls_with_books(self):
        """Test processing URLs with mocked dependencies."""
        orchestrator = BookProcessingOrchestrator(
            database_url="postgresql://test",
            provider_name="dummy",
            api_key="test-key",
            chunking_strategy_name="sentence_splitter",
            chunk_size=1000,
            concurrency_limit=2
        )
        
        # Setup mock dependencies
        orchestrator.embedding_provider = MagicMock()
        orchestrator.chunking_strategy = MagicMock()
        orchestrator.book_service = AsyncMock()
        
        book_urls = ["http://example.com/book1.pdf", "http://example.com/book2.pdf"]
        
        with patch("create_embeddings.book_processing_orchestrator.BookProcessingPipeline") as mock_pipeline_class:
            mock_pipeline = AsyncMock()
            mock_pipeline_class.return_value = mock_pipeline
            
            # Mock the HTTP session context
            with patch("create_embeddings.book_processing_orchestrator.aiohttp.ClientSession") as mock_session_class:
                mock_session = AsyncMock()
                mock_session_class.return_value.__aenter__.return_value = mock_session
                
                await orchestrator.process_books_from_urls(book_urls)
                
                # Verify pipeline was created with correct dependencies
                mock_pipeline_class.assert_called_with(
                    book_service=orchestrator.book_service,
                    embedding_provider=orchestrator.embedding_provider,
                    chunking_strategy=orchestrator.chunking_strategy
                )
                
                # Verify process_book_from_url was called for each URL
                assert mock_pipeline.process_book_from_url.call_count == 2


class TestBookProcessingApplication:
    """Test the BookProcessingApplication class."""
    
    def test_load_urls_from_file(self, tmp_path):
        """Test loading URLs from file."""
        # Create temporary file with URLs
        url_file = tmp_path / "test_urls.txt"
        url_file.write_text("http://example.com/book1.pdf\nhttp://example.com/book2.pdf\n\n# Comment line\n")
        
        urls = BookProcessingApplication.load_urls_from_file(str(url_file))
        
        assert urls == ["http://example.com/book1.pdf", "http://example.com/book2.pdf", "# Comment line"]
    
    def test_load_urls_from_file_nonexistent(self):
        """Test loading URLs from non-existent file raises exception."""
        with pytest.raises(FileNotFoundError):
            BookProcessingApplication.load_urls_from_file("nonexistent.txt")
    
    @pytest.mark.asyncio
    async def test_run_book_processing_success(self, tmp_path):
        """Test successful book processing application run."""
        # Create temporary URL file
        url_file = tmp_path / "test_urls.txt"
        url_file.write_text("http://example.com/book1.pdf\n")
        
        with patch("create_embeddings.book_processing_orchestrator.BookProcessingOrchestrator") as mock_orchestrator_class:
            mock_orchestrator = AsyncMock()
            mock_orchestrator_class.return_value = mock_orchestrator
            
            await BookProcessingApplication.run_book_processing(
                database_url="postgresql://test",
                provider_name="dummy",
                api_key="test-key",
                chunking_strategy_name="sentence_splitter",
                chunk_size=1000,
                url_file_path=str(url_file),
                concurrency_limit=5
            )
            
            # Verify orchestrator was created with correct parameters
            mock_orchestrator_class.assert_called_once_with(
                database_url="postgresql://test",
                provider_name="dummy",
                api_key="test-key",
                chunking_strategy_name="sentence_splitter",
                chunk_size=1000,
                concurrency_limit=5
            )
            
            # Verify orchestrator workflow was executed
            mock_orchestrator.setup_dependencies.assert_called_once()
            mock_orchestrator.process_books_from_urls.assert_called_once_with(["http://example.com/book1.pdf"])
            mock_orchestrator.cleanup_resources.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_book_processing_empty_url_file(self, tmp_path):
        """Test book processing with empty URL file."""
        # Create empty URL file
        url_file = tmp_path / "empty_urls.txt"
        url_file.write_text("")
        
        with patch("create_embeddings.book_processing_orchestrator.BookProcessingOrchestrator") as mock_orchestrator_class:
            mock_orchestrator = AsyncMock()
            mock_orchestrator_class.return_value = mock_orchestrator
            
            await BookProcessingApplication.run_book_processing(
                database_url="postgresql://test",
                provider_name="dummy",
                api_key="test-key",
                chunking_strategy_name="sentence_splitter",
                chunk_size=1000,
                url_file_path=str(url_file),
                concurrency_limit=5
            )
            
            # Verify no processing was attempted
            mock_orchestrator.setup_dependencies.assert_not_called()
            mock_orchestrator.process_books_from_urls.assert_not_called()
            mock_orchestrator.cleanup_resources.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_run_book_processing_cleanup_on_exception(self, tmp_path):
        """Test that cleanup is called even if processing fails."""
        url_file = tmp_path / "test_urls.txt"
        url_file.write_text("http://example.com/book1.pdf\n")
        
        with patch("create_embeddings.book_processing_orchestrator.BookProcessingOrchestrator") as mock_orchestrator_class:
            mock_orchestrator = AsyncMock()
            mock_orchestrator_class.return_value = mock_orchestrator
            
            # Make setup_dependencies fail
            mock_orchestrator.setup_dependencies.side_effect = Exception("Setup failed")
            
            with pytest.raises(Exception, match="Setup failed"):
                await BookProcessingApplication.run_book_processing(
                    database_url="postgresql://test",
                    provider_name="dummy",
                    api_key="test-key",
                    chunking_strategy_name="sentence_splitter",
                    chunk_size=1000,
                    url_file_path=str(url_file),
                    concurrency_limit=5
                )
            
            # Verify cleanup was still called
            mock_orchestrator.cleanup_resources.assert_called_once()
