"""
Tests for Phase 4: BookService Enhancement with get_or_create_book method.
"""

import pytest
from unittest.mock import AsyncMock
from database.postgresql_service import BookService


@pytest.mark.unit
class TestBookServiceGetOrCreateBook:
    """Test the get_or_create_book method enhancement."""

    @pytest.fixture
    def mock_postgresql_service(self):
        """Create a mock PostgreSQL service."""
        return AsyncMock()

    @pytest.fixture
    def book_service(self, mock_postgresql_service):
        """Create a BookService with mocked PostgreSQL service."""
        return BookService(mock_postgresql_service)

    @pytest.mark.asyncio
    async def test_get_or_create_book_existing_book(self, book_service, mock_postgresql_service):
        """Test get_or_create_book when book already exists - should return existing ID."""
        # Setup - book exists with ID 123
        mock_postgresql_service.find_book_by_url.return_value = 123
        
        # Call method
        result = await book_service.get_or_create_book(
            pdf_url="https://example.com/existing.pdf",
            title="New Title",  # Should be ignored since book exists
            author="New Author",  # Should be ignored since book exists
            pages=100  # Should be ignored since book exists
        )
        
        # Verify
        assert result == 123
        mock_postgresql_service.find_book_by_url.assert_called_once_with("https://example.com/existing.pdf")
        mock_postgresql_service.create_book.assert_not_called()  # Should not try to create

    @pytest.mark.asyncio
    async def test_get_or_create_book_new_book_with_full_metadata(self, book_service, mock_postgresql_service):
        """Test get_or_create_book when book doesn't exist and full metadata provided."""
        # Setup - book doesn't exist, create_book returns new ID
        mock_postgresql_service.find_book_by_url.return_value = None
        mock_postgresql_service.create_book.return_value = 456
        
        # Call method
        result = await book_service.get_or_create_book(
            pdf_url="https://example.com/new.pdf",
            title="New Book Title",
            author="New Author",
            pages=150
        )
        
        # Verify
        assert result == 456
        mock_postgresql_service.find_book_by_url.assert_called_once_with("https://example.com/new.pdf")
        mock_postgresql_service.create_book.assert_called_once_with(
            "https://example.com/new.pdf",
            "New Book Title",
            "New Author",
            150
        )

    @pytest.mark.asyncio
    async def test_get_or_create_book_new_book_missing_title(self, book_service, mock_postgresql_service):
        """Test get_or_create_book when book doesn't exist and title is missing."""
        # Setup - book doesn't exist
        mock_postgresql_service.find_book_by_url.return_value = None
        
        # Call method and expect ValueError
        with pytest.raises(ValueError) as exc_info:
            await book_service.get_or_create_book(
                pdf_url="https://example.com/new.pdf",
                title=None,  # Missing title
                author="Author",
                pages=100
            )
        
        # Verify error message
        assert "insufficient metadata provided" in str(exc_info.value)
        assert "title=None" in str(exc_info.value)
        mock_postgresql_service.create_book.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_book_new_book_missing_author(self, book_service, mock_postgresql_service):
        """Test get_or_create_book when book doesn't exist and author is missing."""
        # Setup - book doesn't exist
        mock_postgresql_service.find_book_by_url.return_value = None
        
        # Call method and expect ValueError
        with pytest.raises(ValueError) as exc_info:
            await book_service.get_or_create_book(
                pdf_url="https://example.com/new.pdf",
                title="Title",
                author=None,  # Missing author
                pages=100
            )
        
        # Verify error message
        assert "insufficient metadata provided" in str(exc_info.value)
        assert "author=None" in str(exc_info.value)
        mock_postgresql_service.create_book.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_book_new_book_missing_pages(self, book_service, mock_postgresql_service):
        """Test get_or_create_book when book doesn't exist and pages is missing."""
        # Setup - book doesn't exist
        mock_postgresql_service.find_book_by_url.return_value = None
        
        # Call method and expect ValueError
        with pytest.raises(ValueError) as exc_info:
            await book_service.get_or_create_book(
                pdf_url="https://example.com/new.pdf",
                title="Title",
                author="Author",
                pages=None  # Missing pages
            )
        
        # Verify error message
        assert "insufficient metadata provided" in str(exc_info.value)
        assert "pages=None" in str(exc_info.value)
        mock_postgresql_service.create_book.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_book_new_book_empty_string_title(self, book_service, mock_postgresql_service):
        """Test get_or_create_book when book doesn't exist and title is empty string."""
        # Setup - book doesn't exist
        mock_postgresql_service.find_book_by_url.return_value = None
        
        # Call method and expect ValueError
        with pytest.raises(ValueError) as exc_info:
            await book_service.get_or_create_book(
                pdf_url="https://example.com/new.pdf",
                title="",  # Empty string (falsy)
                author="Author",
                pages=100
            )
        
        # Verify error message
        assert "insufficient metadata provided" in str(exc_info.value)
        mock_postgresql_service.create_book.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_book_new_book_zero_pages(self, book_service, mock_postgresql_service):
        """Test get_or_create_book when book doesn't exist and pages is 0."""
        # Setup - book doesn't exist
        mock_postgresql_service.find_book_by_url.return_value = None
        
        # Call method and expect ValueError (pages=0 is falsy)
        with pytest.raises(ValueError) as exc_info:
            await book_service.get_or_create_book(
                pdf_url="https://example.com/new.pdf",
                title="Title",
                author="Author",
                pages=0  # Zero pages (falsy)
            )
        
        # Verify error message
        assert "insufficient metadata provided" in str(exc_info.value)
        mock_postgresql_service.create_book.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_book_existing_book_with_no_metadata(self, book_service, mock_postgresql_service):
        """Test get_or_create_book when book exists and no metadata provided - should work."""
        # Setup - book exists with ID 789
        mock_postgresql_service.find_book_by_url.return_value = 789
        
        # Call method with no metadata (should work since book exists)
        result = await book_service.get_or_create_book(
            pdf_url="https://example.com/existing.pdf"
            # No title, author, or pages provided
        )
        
        # Verify
        assert result == 789
        mock_postgresql_service.find_book_by_url.assert_called_once_with("https://example.com/existing.pdf")
        mock_postgresql_service.create_book.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_book_database_error_during_find(self, book_service, mock_postgresql_service):
        """Test get_or_create_book when database error occurs during find."""
        # Setup - find_book_by_url raises exception
        mock_postgresql_service.find_book_by_url.side_effect = Exception("Database connection failed")
        
        # Call method and expect exception to propagate
        with pytest.raises(Exception, match="Database connection failed"):
            await book_service.get_or_create_book(
                pdf_url="https://example.com/new.pdf",
                title="Title",
                author="Author",
                pages=100
            )
        
        # Verify create_book was not called
        mock_postgresql_service.create_book.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_book_database_error_during_create(self, book_service, mock_postgresql_service):
        """Test get_or_create_book when database error occurs during create."""
        # Setup - book doesn't exist, but create_book fails
        mock_postgresql_service.find_book_by_url.return_value = None
        mock_postgresql_service.create_book.side_effect = Exception("Failed to create book")
        
        # Call method and expect exception to propagate
        with pytest.raises(Exception, match="Failed to create book"):
            await book_service.get_or_create_book(
                pdf_url="https://example.com/new.pdf",
                title="Title",
                author="Author",
                pages=100
            )
        
        # Verify create_book was called
        mock_postgresql_service.create_book.assert_called_once()


@pytest.mark.unit
class TestBookServiceBackwardsCompatibility:
    """Test that existing BookService methods still work after enhancement."""

    @pytest.fixture
    def mock_postgresql_service(self):
        """Create a mock PostgreSQL service."""
        return AsyncMock()

    @pytest.fixture
    def book_service(self, mock_postgresql_service):
        """Create a BookService with mocked PostgreSQL service."""
        return BookService(mock_postgresql_service)

    @pytest.mark.asyncio
    async def test_save_book_still_works(self, book_service, mock_postgresql_service):
        """Test that existing save_book method still works after adding get_or_create_book."""
        # Setup
        book_data = {
            "pdf-url": "https://example.com/test.pdf",
            "titel": "Test Book",
            "forfatter": "Test Author",
            "sider": 100,
            "chunks": [(1, "chunk1"), (2, "chunk2")],
            "embeddings": [[0.1, 0.2], [0.3, 0.4]]
        }
        
        mock_postgresql_service.create_book.return_value = 123
        
        # Mock transaction context manager
        from contextlib import asynccontextmanager
        
        @asynccontextmanager
        async def mock_transaction():
            yield
        
        mock_postgresql_service.transaction = mock_transaction
        
        # Call save_book
        result = await book_service.save_book(book_data)
        
        # Verify it still works
        assert result == 123
        mock_postgresql_service.create_book.assert_called_once()
        mock_postgresql_service.save_chunks.assert_called_once()

    def test_book_service_initialization_unchanged(self, mock_postgresql_service):
        """Test that BookService initialization hasn't changed."""
        book_service = BookService(mock_postgresql_service)
        assert book_service._service is mock_postgresql_service
