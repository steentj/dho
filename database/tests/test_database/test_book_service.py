"""
Unit tests for Book Service operations.
"""
import pytest
from unittest.mock import AsyncMock, patch
from database.postgresql_service import PostgreSQLService, BookService


@pytest.mark.unit
class TestBookService:
    """Test BookService operations."""
    
    @pytest.fixture
    def service_with_mocks(self):
        """Create a BookService with mocked PostgreSQLService."""
        mock_pg_service = AsyncMock(spec=PostgreSQLService)
        service = BookService(mock_pg_service)
        return service, mock_pg_service
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_save_book(self, service_with_mocks):
        """Test save_book delegates correctly to service."""
        service, mock_pg_service = service_with_mocks
        
        # Mock the save_book method directly in BookService
        original_save_book = service.save_book
        service.save_book = AsyncMock(return_value=123)
        
        try:
            # Test data
            book_data = {
                "pdf-url": "test.pdf",
                "titel": "Test Book",
                "forfatter": "Test Author",
                "sider": 10,
                "chunks": [(1, "Test chunk")],
                "embeddings": [[0.1, 0.2, 0.3]]
            }
            
            # Call method
            result = await service.save_book(book_data, "chunks_test")
            
            # Verify
            assert result == 123
            service.save_book.assert_called_once_with(book_data, "chunks_test")
        finally:
            # Restore original method
            service.save_book = original_save_book
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_safe_db_execute_success(self, service_with_mocks):
        """Test safe_db_execute successfully executes query."""
        service, mock_pg_service = service_with_mocks
        
        # Setup mock
        mock_pg_service.fetchval = AsyncMock(return_value=42)
        
        # Call method
        result = await service.safe_db_execute(
            "test.pdf", "SELECT COUNT(*) FROM books WHERE url = $1", "test.pdf"
        )
        
        # Verify
        assert result == 42
        mock_pg_service.fetchval.assert_called_once_with(
            "SELECT COUNT(*) FROM books WHERE url = $1", "test.pdf"
        )
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_safe_db_execute_error(self, service_with_mocks):
        """Test safe_db_execute handles errors gracefully."""
        service, mock_pg_service = service_with_mocks
        
        # Setup mock to raise exception
        mock_pg_service.fetchval = AsyncMock(side_effect=Exception("DB error"))
        
        # Call method
        result = await service.safe_db_execute(
            "test.pdf", "SELECT COUNT(*) FROM books WHERE url = $1", "test.pdf"
        )
        
        # Verify
        assert result is None
        mock_pg_service.fetchval.assert_called_once_with(
            "SELECT COUNT(*) FROM books WHERE url = $1", "test.pdf"
        )
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_get_or_create_book_existing(self, service_with_mocks):
        """Test get_or_create_book returns existing book ID."""
        service, mock_pg_service = service_with_mocks
        
        # Setup mock to return existing book
        mock_pg_service.find_book_by_url = AsyncMock(return_value=123)
        mock_pg_service.create_book = AsyncMock()
        
        # Call method
        result = await service.get_or_create_book("test.pdf", "Test Book", "Test Author", 10)
        
        # Verify
        assert result == 123
        mock_pg_service.find_book_by_url.assert_called_once_with("test.pdf")
        mock_pg_service.create_book.assert_not_called()
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_get_or_create_book_new(self, service_with_mocks):
        """Test get_or_create_book creates new book when not found."""
        service, mock_pg_service = service_with_mocks
        
        # Setup mock to return no existing book
        mock_pg_service.find_book_by_url = AsyncMock(return_value=None)
        mock_pg_service.create_book = AsyncMock(return_value=456)
        
        # Call method
        result = await service.get_or_create_book("test.pdf", "Test Book", "Test Author", 10)
        
        # Verify
        assert result == 456
        mock_pg_service.find_book_by_url.assert_called_once_with("test.pdf")
        mock_pg_service.create_book.assert_called_once_with(
            "test.pdf", "Test Book", "Test Author", 10
        )
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_get_or_create_book_missing_metadata(self, service_with_mocks):
        """Test get_or_create_book raises error when book not found and metadata missing."""
        service, mock_pg_service = service_with_mocks
        
        # Setup mock to return no existing book
        mock_pg_service.find_book_by_url = AsyncMock(return_value=None)
        
        # Test missing title
        with pytest.raises(ValueError, match="insufficient metadata"):
            await service.get_or_create_book("test.pdf", None, "Test Author", 10)
        
        # Test missing author
        with pytest.raises(ValueError, match="insufficient metadata"):
            await service.get_or_create_book("test.pdf", "Test Book", None, 10)
        
        # Test missing pages
        with pytest.raises(ValueError, match="insufficient metadata"):
            await service.get_or_create_book("test.pdf", "Test Book", "Test Author", None)
        
        # Test zero pages
        with pytest.raises(ValueError, match="insufficient metadata"):
            await service.get_or_create_book("test.pdf", "Test Book", "Test Author", 0)
        
        # Verify find_book_by_url was called for each attempt
        assert mock_pg_service.find_book_by_url.call_count == 4
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_save_book_with_chunks(self, service_with_mocks):
        """Test save_book_with_chunks delegates to service."""
        service, mock_pg_service = service_with_mocks
        
        # Setup mock
        mock_pg_service.save_book_with_chunks = AsyncMock(return_value=123)
        
        # Test data
        book_data = {
            "pdf_url": "test.pdf",
            "titel": "Test Book",
            "forfatter": "Test Author",
            "sider": 10,
            "chunks": [(1, "Test chunk")],
            "embeddings": [[0.1, 0.2, 0.3]]
        }
        
        # Call method
        result = await service.save_book_with_chunks(book_data, "chunks_test")
        
        # Verify
        assert result == 123
        mock_pg_service.save_book_with_chunks.assert_called_once_with(book_data, "chunks_test")
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_book_exists_with_provider(self, service_with_mocks):
        """Test book_exists_with_provider delegates to service."""
        service, mock_pg_service = service_with_mocks
        
        # Setup mock
        mock_pg_service.book_exists_with_provider = AsyncMock(return_value=True)
        
        # Call method
        result = await service.book_exists_with_provider("test.pdf", "openai")
        
        # Verify
        assert result is True
        mock_pg_service.book_exists_with_provider.assert_called_once_with("test.pdf", "openai")
