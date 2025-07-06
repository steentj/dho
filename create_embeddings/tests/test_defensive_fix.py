#!/usr/bin/env python3
"""
Test to verify the defensive fix for chunk_text data type issues.
This test validates that the fix prevents the "expected str, got list" error.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from create_embeddings.opret_bøger import _save_book_with_repository


class TestDefensiveFix:
    """Test the defensive fix for chunk_text data type issues."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock book service for testing."""
        service = MagicMock()
        service.get_or_create_book = AsyncMock(return_value=123)
        service.save_chunks = AsyncMock()
        
        # Mock the _service attribute (for line 125 in _save_book_with_repository)
        service._service = MagicMock()
        service._service.save_chunks = AsyncMock()
        
        return service

    @pytest.mark.asyncio
    async def test_normal_string_chunk_text(self, mock_service):
        """Test that normal string chunk_text works as expected."""
        book = {
            "pdf-url": "test-url",
            "titel": "Test Book",
            "forfatter": "Test Author",
            "sider": 1,
            "chunks": [(1, "Normal string chunk")],  # ✅ Normal case
            "embeddings": [[0.1] * 768]
        }
        
        await _save_book_with_repository(book, mock_service, "chunks_nomic")
        
        # Verify the service was called correctly
        mock_service.get_or_create_book.assert_called_once()
        mock_service._service.save_chunks.assert_called_once()
        
        # Check that chunk_text is passed as string
        call_args = mock_service._service.save_chunks.call_args
        chunks_with_embeddings = call_args[0][1]  # Second argument
        assert len(chunks_with_embeddings) == 1
        page_num, chunk_text, embedding = chunks_with_embeddings[0]
        assert isinstance(chunk_text, str)
        assert chunk_text == "Normal string chunk"

    @pytest.mark.asyncio
    async def test_list_chunk_text_defensive_fix(self, mock_service):
        """Test that list chunk_text is converted to string (defensive fix)."""
        book = {
            "pdf-url": "test-url-2",
            "titel": "Test Book 2",
            "forfatter": "Test Author",
            "sider": 1,
            "chunks": [(1, ["This", "is", "a", "list"])],  # 🔥 Bug case - list!
            "embeddings": [[0.1] * 768]
        }
        
        await _save_book_with_repository(book, mock_service, "chunks_nomic")
        
        # Verify the service was called
        mock_service._service.save_chunks.assert_called_once()
        
        # Check that list chunk_text was converted to string
        call_args = mock_service._service.save_chunks.call_args
        chunks_with_embeddings = call_args[0][1]
        assert len(chunks_with_embeddings) == 1
        page_num, chunk_text, embedding = chunks_with_embeddings[0]
        assert isinstance(chunk_text, str)
        assert chunk_text == "This is a list"  # List should be joined with spaces

    @pytest.mark.asyncio
    async def test_integer_chunk_text_defensive_fix(self, mock_service):
        """Test that integer chunk_text is converted to string."""
        book = {
            "pdf-url": "test-url-3",
            "titel": "Test Book 3",
            "forfatter": "Test Author",
            "sider": 1,
            "chunks": [(1, 12345)],  # Edge case - integer
            "embeddings": [[0.1] * 768]
        }
        
        await _save_book_with_repository(book, mock_service, "chunks_nomic")
        
        # Verify the service was called
        mock_service._service.save_chunks.assert_called_once()
        
        # Check that integer chunk_text was converted to string
        call_args = mock_service._service.save_chunks.call_args
        chunks_with_embeddings = call_args[0][1]
        assert len(chunks_with_embeddings) == 1
        page_num, chunk_text, embedding = chunks_with_embeddings[0]
        assert isinstance(chunk_text, str)
        assert chunk_text == "12345"

    @pytest.mark.asyncio
    async def test_empty_list_chunk_text(self, mock_service):
        """Test that empty list chunk_text is handled gracefully."""
        book = {
            "pdf-url": "test-url-4",
            "titel": "Test Book 4",
            "forfatter": "Test Author",
            "sider": 1,
            "chunks": [(1, [])],  # Edge case - empty list
            "embeddings": [[0.1] * 768]
        }
        
        await _save_book_with_repository(book, mock_service, "chunks_nomic")
        
        # Verify the service was called
        mock_service._service.save_chunks.assert_called_once()
        
        # Check that empty list becomes empty string
        call_args = mock_service._service.save_chunks.call_args
        chunks_with_embeddings = call_args[0][1]
        assert len(chunks_with_embeddings) == 1
        page_num, chunk_text, embedding = chunks_with_embeddings[0]
        assert isinstance(chunk_text, str)
        assert chunk_text == ""  # Empty list joins to empty string

    @pytest.mark.asyncio
    async def test_multiple_chunks_mixed_types(self, mock_service):
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
        
        await _save_book_with_repository(book, mock_service, "chunks_nomic")
        
        # Verify the service was called
        mock_service._service.save_chunks.assert_called_once()
        
        # Check all chunks are properly converted
        call_args = mock_service._service.save_chunks.call_args
        chunks_with_embeddings = call_args[0][1]
        assert len(chunks_with_embeddings) == 3
        
        # Check first chunk (normal string)
        page_num, chunk_text, embedding = chunks_with_embeddings[0]
        assert isinstance(chunk_text, str)
        assert chunk_text == "Normal string"
        
        # Check second chunk (was list, should be converted)
        page_num, chunk_text, embedding = chunks_with_embeddings[1]
        assert isinstance(chunk_text, str)
        assert chunk_text == "List of words"
        
        # Check third chunk (normal string)
        page_num, chunk_text, embedding = chunks_with_embeddings[2]
        assert isinstance(chunk_text, str)
        assert chunk_text == "Another normal string"


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
