#!/usr/bin/env python3
"""
Test to verify the defensive fix for chunk_text data type issues.
This test validates that the fix prevents the "expected str, got list" error.
"""

import pytest
from create_embeddings.book_processing_pipeline import BookProcessingPipeline
from create_embeddings.book_service_interface import IBookService


class MockBookService(IBookService):
    """Mock BookService for testing defensive fix"""
    
    def __init__(self):
        self.saved_books = []
        self.saved_chunks = []
    
    async def save_book_with_chunks(self, book, table_name: str) -> int:
        """Mock save_book_with_chunks that captures the data for inspection"""
        self.saved_books.append(book)
        
        # Extract chunks to verify data types
        for (page_num, chunk_text), embedding in zip(book["chunks"], book["embeddings"]):
            self.saved_chunks.append({
                "page_num": page_num,
                "chunk_text": chunk_text,
                "chunk_text_type": type(chunk_text),
                "embedding": embedding
            })
        
        return 123  # Mock book ID
    
    async def book_exists_with_provider(self, pdf_url: str, provider_name: str) -> bool:
        return False  # For test purposes, assume book doesn't exist


class MockEmbeddingProvider:
    """Mock embedding provider for testing"""
    
    async def get_embedding(self, text: str):
        """Mock get_embedding method"""
        return [0.1] * 768
    
    async def has_embeddings_for_book(self, book_id: int, db_service) -> bool:
        """Mock implementation for abstract method."""
        return False
    
    def get_table_name(self):
        return "chunks_test"
    
    def get_provider_name(self):
        return "test_provider"


async def save_book_with_pipeline(book, book_service, embedding_provider):
    """Helper function that uses the pipeline to save a book - replacement for the old save_book function"""
    pipeline = BookProcessingPipeline(
        book_service=book_service,
        embedding_provider=embedding_provider,
        chunking_strategy=None  # Not needed for direct save test
    )
    
    # Use the pipeline's internal save method that contains the defensive fix
    await pipeline._save_book_data(book)


class TestDefensiveFix:
    """Test the defensive fix for chunk_text data type issues."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock book service for testing."""
        return MockBookService()

    @pytest.fixture
    def mock_embedding_provider(self):
        """Create a mock embedding provider for testing."""
        return MockEmbeddingProvider()

    @pytest.mark.asyncio
    async def test_normal_string_chunk_text(self, mock_service, mock_embedding_provider):
        """Test that normal string chunk_text works as expected."""
        book = {
            "pdf-url": "test-url",
            "titel": "Test Book",
            "forfatter": "Test Author",
            "sider": 1,
            "chunks": [(1, "Normal string chunk")],  # ✅ Normal case
            "embeddings": [[0.1] * 768]
        }
        
        await save_book_with_pipeline(book, mock_service, mock_embedding_provider)
        
        # Verify the chunk text is passed as string
        assert len(mock_service.saved_chunks) == 1
        chunk = mock_service.saved_chunks[0]
        assert isinstance(chunk["chunk_text"], str)
        assert chunk["chunk_text"] == "Normal string chunk"

    @pytest.mark.asyncio
    async def test_list_chunk_text_defensive_fix(self, mock_service, mock_embedding_provider):
        """Test that list chunk_text is converted to string (defensive fix)."""
        book = {
            "pdf-url": "test-url-2",
            "titel": "Test Book 2",
            "forfatter": "Test Author",
            "sider": 1,
            "chunks": [(1, ["This", "is", "a", "list"])],  # 🔥 Bug case - list!
            "embeddings": [[0.1] * 768]
        }
        
        await save_book_with_pipeline(book, mock_service, mock_embedding_provider)
        
        # Check that list chunk_text was converted to string
        assert len(mock_service.saved_chunks) == 1
        chunk = mock_service.saved_chunks[0]
        assert isinstance(chunk["chunk_text"], str)
        assert chunk["chunk_text"] == "This is a list"  # List should be joined with spaces

    @pytest.mark.asyncio
    async def test_integer_chunk_text_defensive_fix(self, mock_service, mock_embedding_provider):
        """Test that integer chunk_text is converted to string."""
        book = {
            "pdf-url": "test-url-3",
            "titel": "Test Book 3",
            "forfatter": "Test Author",
            "sider": 1,
            "chunks": [(1, 12345)],  # Edge case - integer
            "embeddings": [[0.1] * 768]
        }
        
        await save_book_with_pipeline(book, mock_service, mock_embedding_provider)
        
        # Check that integer chunk_text was converted to string
        assert len(mock_service.saved_chunks) == 1
        chunk = mock_service.saved_chunks[0]
        assert isinstance(chunk["chunk_text"], str)
        assert chunk["chunk_text"] == "12345"

    @pytest.mark.asyncio
    async def test_empty_list_chunk_text(self, mock_service, mock_embedding_provider):
        """Test that empty list chunk_text is handled gracefully."""
        book = {
            "pdf-url": "test-url-4",
            "titel": "Test Book 4",
            "forfatter": "Test Author",
            "sider": 1,
            "chunks": [(1, [])],  # Edge case - empty list
            "embeddings": [[0.1] * 768]
        }
        
        await save_book_with_pipeline(book, mock_service, mock_embedding_provider)
        
        # Check that empty list becomes empty string
        assert len(mock_service.saved_chunks) == 1
        chunk = mock_service.saved_chunks[0]
        assert isinstance(chunk["chunk_text"], str)
        assert chunk["chunk_text"] == ""  # Empty list joins to empty string

    @pytest.mark.asyncio
    async def test_multiple_chunks_mixed_types(self, mock_service, mock_embedding_provider):
        """Test multiple chunks with mixed data types."""
        book = {
            "pdf-url": "test-url-5",
            "titel": "Test Book 5",
            "forfatter": "Test Author",
            "sider": 3,
            "chunks": [
                (1, "Normal string"),  # Normal
                (2, ["List", "of", "words"]),  # List (bug case)
                (3, "Another normal string")  # Normal
            ],
            "embeddings": [[0.1] * 768, [0.2] * 768, [0.3] * 768]
        }
        
        await save_book_with_pipeline(book, mock_service, mock_embedding_provider)
        
        # Check all chunks are properly converted
        assert len(mock_service.saved_chunks) == 3
        
        # Check first chunk (normal string)
        chunk1 = mock_service.saved_chunks[0]
        assert isinstance(chunk1["chunk_text"], str)
        assert chunk1["chunk_text"] == "Normal string"
        
        # Check second chunk (was list, should be converted)
        chunk2 = mock_service.saved_chunks[1]
        assert isinstance(chunk2["chunk_text"], str)
        assert chunk2["chunk_text"] == "List of words"
        
        # Check third chunk (normal string)
        chunk3 = mock_service.saved_chunks[2]
        assert isinstance(chunk3["chunk_text"], str)
        assert chunk3["chunk_text"] == "Another normal string"


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
