"""
Integration tests for Phase 4: BookService Enhancement with metadata reuse.
"""

import pytest
from unittest.mock import AsyncMock
from contextlib import asynccontextmanager
from database.postgresql_service import BookService
from create_embeddings.opret_bøger import save_book
from create_embeddings.providers.embedding_providers import DummyEmbeddingProvider


@pytest.mark.integration
class TestBookServiceEnhancementIntegration:
    """Integration tests for the enhanced BookService with get_or_create_book."""

    @pytest.fixture
    def mock_postgresql_service(self):
        """Create a mock PostgreSQL service."""
        service = AsyncMock()
        
        # Mock the transaction method to return a proper async context manager
        @asynccontextmanager
        async def mock_transaction():
            yield
        
        service.transaction = mock_transaction
        return service

    @pytest.fixture
    def book_service(self, mock_postgresql_service):
        """Create a BookService with mocked PostgreSQL service."""
        return BookService(mock_postgresql_service)

    @pytest.fixture
    def embedding_provider(self):
        """Create a dummy embedding provider for testing."""
        return DummyEmbeddingProvider()

    @pytest.mark.asyncio
    async def test_save_book_with_metadata_reuse_new_book(self, book_service, mock_postgresql_service, embedding_provider):
        """Test save_book with get_or_create_book for a new book."""
        # Setup - book doesn't exist yet
        mock_postgresql_service.find_book_by_url.return_value = None
        mock_postgresql_service.create_book.return_value = 123
        
        book_data = {
            "pdf-url": "https://example.com/new-book.pdf",
            "titel": "New Book Title",
            "forfatter": "New Author",
            "sider": 150,
            "chunks": [(1, "Test chunk 1"), (2, "Test chunk 2")],
            "embeddings": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        }
        
        # Call save_book (which now uses get_or_create_book internally)
        await save_book(book_data, book_service, embedding_provider)
        
        # Verify the enhanced workflow
        mock_postgresql_service.find_book_by_url.assert_called_once_with("https://example.com/new-book.pdf")
        mock_postgresql_service.create_book.assert_called_once_with(
            "https://example.com/new-book.pdf",
            "New Book Title",
            "New Author",
            150
        )
        mock_postgresql_service.save_chunks.assert_called_once()
        
        # Verify chunks were saved with correct table name
        call_args = mock_postgresql_service.save_chunks.call_args
        assert call_args[0][0] == 123  # book_id
        assert call_args[0][2] == "chunks"  # table_name from DummyEmbeddingProvider

    @pytest.mark.asyncio
    async def test_save_book_with_metadata_reuse_existing_book(self, book_service, mock_postgresql_service, embedding_provider):
        """Test save_book with get_or_create_book for an existing book - metadata should be reused."""
        # Setup - book already exists with ID 456
        mock_postgresql_service.find_book_by_url.return_value = 456
        
        book_data = {
            "pdf-url": "https://example.com/existing-book.pdf",
            "titel": "Updated Title",  # This should be ignored since book exists
            "forfatter": "Updated Author",  # This should be ignored since book exists
            "sider": 999,  # This should be ignored since book exists
            "chunks": [(1, "New chunk from different provider")],
            "embeddings": [[0.7, 0.8, 0.9]]
        }
        
        # Call save_book (which now uses get_or_create_book internally)
        await save_book(book_data, book_service, embedding_provider)
        
        # Verify metadata reuse workflow
        mock_postgresql_service.find_book_by_url.assert_called_once_with("https://example.com/existing-book.pdf")
        mock_postgresql_service.create_book.assert_not_called()  # Should not create since book exists
        mock_postgresql_service.save_chunks.assert_called_once()
        
        # Verify chunks were saved with existing book ID
        call_args = mock_postgresql_service.save_chunks.call_args
        assert call_args[0][0] == 456  # existing book_id
        assert call_args[0][2] == "chunks"  # table_name

    @pytest.mark.asyncio
    async def test_multiple_providers_same_book_metadata_reuse(self, book_service, mock_postgresql_service):
        """Test processing same book with multiple providers - metadata should be reused."""
        
        # Create different providers
        openai_provider = DummyEmbeddingProvider()  # Use dummy for testing
        openai_provider.get_table_name = lambda: "chunks"
        openai_provider.get_provider_name = lambda: "openai"
        
        ollama_provider = DummyEmbeddingProvider()  # Use dummy for testing  
        ollama_provider.get_table_name = lambda: "chunks_nomic"
        ollama_provider.get_provider_name = lambda: "ollama"
        
        # Setup - book exists after first provider creates it
        mock_postgresql_service.find_book_by_url.side_effect = [None, 789, 789]  # Not found, then found twice
        mock_postgresql_service.create_book.return_value = 789
        
        book_data = {
            "pdf-url": "https://example.com/multi-provider-book.pdf",
            "titel": "Multi-Provider Book",
            "forfatter": "Test Author",
            "sider": 200,
            "chunks": [(1, "Shared chunk content")],
            "embeddings": [[0.1, 0.2, 0.3]]
        }
        
        # Process with OpenAI provider first (creates book)
        await save_book(book_data, book_service, openai_provider)
        
        # Process with Ollama provider second (reuses existing book metadata)
        book_data_updated = book_data.copy()
        book_data_updated["titel"] = "Different Title"  # Should be ignored
        book_data_updated["forfatter"] = "Different Author"  # Should be ignored
        await save_book(book_data_updated, book_service, ollama_provider)
        
        # Verify workflow
        assert mock_postgresql_service.find_book_by_url.call_count == 2
        mock_postgresql_service.create_book.assert_called_once()  # Only called once for the first provider
        assert mock_postgresql_service.save_chunks.call_count == 2  # Called for both providers
        
        # Verify each provider used its own table
        save_chunks_calls = mock_postgresql_service.save_chunks.call_args_list
        assert save_chunks_calls[0][0][2] == "chunks"  # OpenAI table
        assert save_chunks_calls[1][0][2] == "chunks_nomic"  # Ollama table

    @pytest.mark.asyncio
    async def test_backwards_compatibility_with_existing_workflow(self, book_service, mock_postgresql_service, embedding_provider):
        """Test that existing workflows continue to work unchanged."""
        # This test ensures that the Phase 4 enhancement doesn't break existing code
        
        # Setup for a typical existing workflow
        mock_postgresql_service.find_book_by_url.return_value = None
        mock_postgresql_service.create_book.return_value = 999
        
        # Book data in the exact format used by existing opret_bøger.py
        book_data = {
            "pdf-url": "https://legacy.example.com/book.pdf",
            "titel": "Legacy Book",
            "forfatter": "Legacy Author", 
            "sider": 42,
            "chunks": [(1, "Legacy chunk 1"), (2, "Legacy chunk 2")],
            "embeddings": [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
        }
        
        # Call save_book exactly as existing code would
        await save_book(book_data, book_service, embedding_provider)
        
        # Verify everything works exactly as before
        mock_postgresql_service.find_book_by_url.assert_called_once()
        mock_postgresql_service.create_book.assert_called_once_with(
            "https://legacy.example.com/book.pdf",
            "Legacy Book",
            "Legacy Author",
            42
        )
        mock_postgresql_service.save_chunks.assert_called_once()
        
        # Verify correct chunk data format
        call_args = mock_postgresql_service.save_chunks.call_args
        chunks_arg = call_args[0][1]
        assert chunks_arg == [(1, "Legacy chunk 1", [1.0, 2.0, 3.0]), (2, "Legacy chunk 2", [4.0, 5.0, 6.0])]
