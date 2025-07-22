"""
Unit tests for IBookService interface compliance.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from database.postgresql_service import (
    PostgreSQLService, 
    BookService, 
    PostgreSQLPoolService
)
from create_embeddings.book_service_interface import IBookService


@pytest.mark.unit
class TestIBookServiceCompliance:
    """Test that all implementations correctly implement the IBookService interface."""
    
    def test_postgresql_service_implements_interface(self):
        """Test PostgreSQLService implements IBookService."""
        # Verify class inheritance
        assert issubclass(PostgreSQLService, IBookService)
        
        # Verify required methods are implemented
        service = PostgreSQLService()
        assert hasattr(service, "save_book_with_chunks")
        assert hasattr(service, "book_exists_with_provider")
        
        # Verify method signatures match interface
        assert callable(service.save_book_with_chunks)
        assert callable(service.book_exists_with_provider)
    
    def test_book_service_implements_interface(self):
        """Test BookService implements IBookService."""
        # Verify class inheritance
        assert issubclass(BookService, IBookService)
        
        # Create instance with mock dependency
        mock_pg_service = AsyncMock(spec=PostgreSQLService)
        service = BookService(mock_pg_service)
        
        # Verify required methods are implemented
        assert hasattr(service, "save_book_with_chunks")
        assert hasattr(service, "book_exists_with_provider")
        
        # Verify method signatures match interface
        assert callable(service.save_book_with_chunks)
        assert callable(service.book_exists_with_provider)
    
    def test_postgresql_pool_service_implements_interface(self):
        """Test PostgreSQLPoolService implements IBookService."""
        # Verify class inheritance
        assert issubclass(PostgreSQLPoolService, IBookService)
        
        # Verify required methods are implemented
        service = PostgreSQLPoolService()
        assert hasattr(service, "save_book_with_chunks")
        assert hasattr(service, "book_exists_with_provider")
        
        # Verify method signatures match interface
        assert callable(service.save_book_with_chunks)
        assert callable(service.book_exists_with_provider)
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_book_service_interface_delegation(self):
        """Test BookService correctly delegates to PostgreSQLService."""
        # Create mock service
        mock_pg_service = AsyncMock(spec=PostgreSQLService)
        service = BookService(mock_pg_service)
        
        # Setup mocks
        mock_pg_service.save_book_with_chunks = AsyncMock(return_value=123)
        mock_pg_service.book_exists_with_provider = AsyncMock(return_value=True)
        
        # Test save_book_with_chunks
        book_data = {
            "pdf_url": "test.pdf",
            "title": "Test Book",
            "author": "Test Author",
            "pages": 10
        }
        result = await service.save_book_with_chunks(book_data, "chunks_test")
        assert result == 123
        mock_pg_service.save_book_with_chunks.assert_called_once_with(book_data, "chunks_test")
        
        # Test book_exists_with_provider
        result = await service.book_exists_with_provider("test.pdf", "openai")
        assert result is True
        mock_pg_service.book_exists_with_provider.assert_called_once_with("test.pdf", "openai")
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_pool_service_interface_implementation(self):
        """Test PostgreSQLPoolService's implementation of IBookService."""
        # Create service
        service = PostgreSQLPoolService()
        
        # Create mock for book repository and factory
        mock_book_repo = AsyncMock()
        mock_book_repo.find_book_by_url = AsyncMock(return_value=123)
        mock_connection = AsyncMock()
        mock_connection.fetchval = AsyncMock(return_value=5)
        
        # Setup get_book_repository to return mock repo
        service.get_book_repository = MagicMock()
        
        # Create async context manager for get_book_repository
        class AsyncContextManagerMock:
            async def __aenter__(self):
                return mock_book_repo
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        
        service.get_book_repository.return_value = AsyncContextManagerMock()
        
        # Setup get_connection to return mock connection
        service.get_connection = MagicMock()
        
        # Create async context manager for get_connection
        class ConnectionContextManagerMock:
            async def __aenter__(self):
                return mock_connection
                
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        
        service.get_connection.return_value = ConnectionContextManagerMock()
        
        # Test book_exists_with_provider
        result = await service.book_exists_with_provider("test.pdf", "openai")
        
        # Verify
        assert result is True
        mock_book_repo.find_book_by_url.assert_called_once_with("test.pdf")
        mock_connection.fetchval.assert_called_once()
