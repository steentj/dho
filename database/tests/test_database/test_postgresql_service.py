"""
Unit tests for PostgreSQL service layer.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from database.postgresql_service import PostgreSQLService, BookService, create_postgresql_service, create_book_service


@pytest.mark.unit
class TestPostgreSQLService:
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'})
    async def test_find_book_by_url_exception_propagation(self):
        """Test that exceptions in find_book_by_url are propagated."""
        service = PostgreSQLService()
        mock_book_repo = AsyncMock()
        service._connection = Mock()  # Just to pass _ensure_connected
        service._book_repository = mock_book_repo
        service._search_repository = Mock()

        mock_book_repo.find_book_by_url.side_effect = Exception("DB error")

        with pytest.raises(Exception, match="DB error"):
            await service.find_book_by_url("test.pdf")
    """Test PostgreSQL service implementation."""
    
    @patch.dict('os.environ', {'TESTING': 'true'})
    def test_service_initialization(self):
        """Test service can be instantiated."""
        service = PostgreSQLService()
        assert service._connection is None
        assert service._book_repository is None
        assert service._search_repository is None
    
    def test_service_initialization_with_url(self):
        """Test service initialization with custom database URL."""
        service = PostgreSQLService("postgresql://test:test@localhost/test")
        assert service._connection is None  # Not connected yet
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'})
    @patch('database.postgresql_service.create_database_factory')
    async def test_connect_success(self, mock_create_factory):
        """Test successful service connection."""
        # Setup mocks
        mock_factory = Mock()
        mock_connection = AsyncMock()
        mock_book_repo = Mock()
        mock_search_repo = Mock()
        
        mock_create_factory.return_value = mock_factory
        # create_connection should be async
        mock_factory.create_connection = AsyncMock(return_value=mock_connection)
        mock_factory.create_book_repository.return_value = mock_book_repo
        mock_factory.create_search_repository.return_value = mock_search_repo
        
        # Test connection
        service = PostgreSQLService()
        await service.connect()
        
        # Verify
        assert service._connection == mock_connection
        assert service._book_repository == mock_book_repo
        assert service._search_repository == mock_search_repo
        mock_create_factory.assert_called_once_with("postgresql", database_url=None)
        mock_factory.create_connection.assert_called_once()
        mock_factory.create_book_repository.assert_called_once_with(mock_connection)
        mock_factory.create_search_repository.assert_called_once_with(mock_connection)
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'})
    @patch.dict('os.environ', {'TESTING': 'true'})
    async def test_disconnect_success(self):
        """Test successful service disconnection."""
        service = PostgreSQLService()
        mock_connection = AsyncMock()
        service._connection = mock_connection
        service._book_repository = Mock()
        service._search_repository = Mock()
        
        await service.disconnect()
        
        mock_connection.close.assert_called_once()
        assert service._connection is None
        assert service._book_repository is None
        assert service._search_repository is None
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'})
    @patch.dict('os.environ', {'TESTING': 'true'})
    async def test_disconnect_when_not_connected(self):
        """Test disconnection when not connected."""
        service = PostgreSQLService()
        # Should not raise exception
        await service.disconnect()
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'})
    @patch('database.postgresql_service.create_database_factory')
    async def test_lifespan_context(self, mock_create_factory):
        """Test lifespan context manager."""
        # Setup mocks
        mock_factory = Mock()  # Use regular Mock for factory
        mock_connection = AsyncMock()
        mock_book_repo = Mock()  # Use regular Mock for repositories
        mock_search_repo = Mock()
        
        mock_create_factory.return_value = mock_factory
        mock_factory.create_connection = AsyncMock(return_value=mock_connection)
        mock_factory.create_book_repository.return_value = mock_book_repo
        mock_factory.create_search_repository.return_value = mock_search_repo
        
        service = PostgreSQLService()
        
        async with service.lifespan_context() as ctx_service:
            assert ctx_service is service
            assert service._connection == mock_connection
        
        # Should be disconnected after context
        mock_connection.close.assert_called_once()
        assert service._connection is None
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'})
    async def test_connection_interface_methods(self):
        """Test connection interface methods."""
        service = PostgreSQLService()
        mock_connection = AsyncMock()
        service._connection = mock_connection
        
        # Test execute
        mock_connection.execute.return_value = "EXECUTED"
        result = await service.execute("SELECT 1", "param")
        assert result == "EXECUTED"
        mock_connection.execute.assert_called_once_with("SELECT 1", "param")
        
        # Test fetchone
        mock_connection.fetchone.return_value = {"id": 1}
        result = await service.fetchone("SELECT * FROM test", 1)
        assert result == {"id": 1}
        mock_connection.fetchone.assert_called_once_with("SELECT * FROM test", 1)
        
        # Test fetchall
        mock_connection.fetchall.return_value = [{"id": 1}, {"id": 2}]
        result = await service.fetchall("SELECT * FROM test")
        assert result == [{"id": 1}, {"id": 2}]
        mock_connection.fetchall.assert_called_once_with("SELECT * FROM test")
        
        # Test fetchval
        mock_connection.fetchval.return_value = 42
        result = await service.fetchval("SELECT COUNT(*)")
        assert result == 42
        mock_connection.fetchval.assert_called_once_with("SELECT COUNT(*)")
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'})
    async def test_transaction_context(self):
        """Test transaction context manager."""
        from contextlib import asynccontextmanager
        
        service = PostgreSQLService()
        mock_connection = Mock()
        service._connection = mock_connection
        
        # Create a proper async context manager
        @asynccontextmanager
        async def mock_transaction():
            yield
        
        mock_connection.transaction = mock_transaction
        
        async with service.transaction():
            pass
        
        # Transaction was successfully used (no assertion needed since it's a function)
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'})
    async def test_repository_operations(self):
        """Test high-level repository operations."""
        service = PostgreSQLService()
        mock_book_repo = AsyncMock()
        mock_search_repo = AsyncMock()
        service._connection = Mock()  # Just to pass _ensure_connected
        service._book_repository = mock_book_repo
        service._search_repository = mock_search_repo
        
        # Test find_book_by_url
        mock_book_repo.find_book_by_url.return_value = 123
        result = await service.find_book_by_url("test.pdf")
        assert result == 123
        mock_book_repo.find_book_by_url.assert_called_once_with("test.pdf")
        
        # Test create_book
        mock_book_repo.create_book.return_value = 456
        result = await service.create_book("test.pdf", "Title", "Author", 100)
        assert result == 456
        mock_book_repo.create_book.assert_called_once_with("test.pdf", "Title", "Author", 100)
        
        # Test save_chunks
        chunks = [(1, "chunk1", [0.1, 0.2]), (2, "chunk2", [0.3, 0.4])]
        await service.save_chunks(123, chunks)
        mock_book_repo.save_chunks.assert_called_once_with(123, chunks, "chunks")
        
        # Test vector_search
        embedding = [0.1, 0.2, 0.3]
        mock_search_repo.vector_search.return_value = [("result1",), ("result2",)]
        result = await service.vector_search(embedding, limit=5)
        assert result == [("result1",), ("result2",)]
        mock_search_repo.vector_search.assert_called_once_with(embedding, 5, "cosine", "normal", None)
    
    @patch.dict('os.environ', {'TESTING': 'true'})
    def test_ensure_connected_when_not_connected(self):
        """Test _ensure_connected raises error when not connected."""
        service = PostgreSQLService()
        
        with pytest.raises(RuntimeError, match="PostgreSQL service is not connected"):
            service._ensure_connected()
    
    @patch.dict('os.environ', {'TESTING': 'true'})
    def test_ensure_connected_when_connected(self):
        """Test _ensure_connected passes when connected."""
        service = PostgreSQLService()
        service._connection = Mock()
        
        # Should not raise
        service._ensure_connected()
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'})
    async def test_cursor_compatibility(self):
        """Test cursor method for compatibility."""
        service = PostgreSQLService()
        service._connection = Mock()  # Just to pass _ensure_connected
        
        cursor = await service.cursor()
        assert cursor._service is service


@pytest.mark.unit
class TestPostgreSQLCursor:
    """Test PostgreSQL cursor compatibility layer."""
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'})
    async def test_execute_with_params(self):
        """Test cursor execute with parameters."""
        mock_service = AsyncMock()
        from database.postgresql_service import PostgreSQLCursor
        cursor = PostgreSQLCursor(mock_service)
        
        await cursor.execute("SELECT * FROM test WHERE id = %s", (1,))
        mock_service.execute.assert_called_once_with("SELECT * FROM test WHERE id = %s", 1)
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'})
    async def test_execute_without_params(self):
        """Test cursor execute without parameters."""
        mock_service = AsyncMock()
        from database.postgresql_service import PostgreSQLCursor
        cursor = PostgreSQLCursor(mock_service)
        
        await cursor.execute("SELECT 1")
        mock_service.execute.assert_called_once_with("SELECT 1")
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'})
    async def test_fetchall_not_implemented(self):
        """Test that fetchall raises NotImplementedError."""
        mock_service = AsyncMock()
        from database.postgresql_service import PostgreSQLCursor
        cursor = PostgreSQLCursor(mock_service)
        
        with pytest.raises(NotImplementedError):
            await cursor.fetchall()


@pytest.mark.unit
class TestBookService:
    """Test book service convenience wrapper."""
    
    def test_book_service_initialization(self):
        """Test book service can be instantiated."""
        mock_service = Mock()
        book_service = BookService(mock_service)
        assert book_service._service is mock_service
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'})
    async def test_save_book(self):
        """Test complete book saving workflow."""
        from unittest.mock import AsyncMock
        from contextlib import asynccontextmanager
        
        mock_service = AsyncMock()
        book_service = BookService(mock_service)
        
        # Setup book data
        book_data = {
            "pdf-url": "http://example.com/test.pdf",
            "titel": "Test Book",
            "forfatter": "Test Author", 
            "sider": 100,
            "chunks": [(1, "chunk1"), (2, "chunk2")],
            "embeddings": [[0.1, 0.2], [0.3, 0.4]]
        }
        
        # Mock service responses for enhanced workflow
        mock_service.find_book_by_url.return_value = None  # Book doesn't exist
        mock_service.create_book.return_value = 123
        
        # Mock transaction as an async context manager
        @asynccontextmanager
        async def mock_transaction():
            yield
        
        mock_service.transaction = mock_transaction
        
        # Call save_book
        result = await book_service.save_book(book_data)
        
        # Verify enhanced workflow is used
        assert result == 123
        mock_service.find_book_by_url.assert_called_once()  # Now calls find first
        mock_service.create_book.assert_called_once_with(
            "http://example.com/test.pdf",
            "Test Book", 
            "Test Author",
            100
        )
        
        expected_chunks = [(1, "chunk1", [0.1, 0.2]), (2, "chunk2", [0.3, 0.4])]
        mock_service.save_chunks.assert_called_once_with(123, expected_chunks, 'chunks')
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'})
    async def test_safe_db_execute_success(self):
        """Test safe_db_execute with successful query."""
        mock_service = AsyncMock()
        book_service = BookService(mock_service)
        
        mock_service.fetchval.return_value = 42
        
        result = await book_service.safe_db_execute("test.pdf", "SELECT COUNT(*)")
        
        assert result == 42
        mock_service.fetchval.assert_called_once_with("SELECT COUNT(*)")
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'})
    async def test_safe_db_execute_exception(self):
        """Test safe_db_execute with exception."""
        mock_service = AsyncMock()
        book_service = BookService(mock_service)
        
        mock_service.fetchval.side_effect = Exception("Database error")
        
        result = await book_service.safe_db_execute("test.pdf", "SELECT COUNT(*)")
        
        assert result is None


@pytest.mark.unit
class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'})
    @patch('database.postgresql_service.PostgreSQLService')
    async def test_create_postgresql_service(self, mock_service_class):
        """Test create_postgresql_service convenience function."""
        mock_service = AsyncMock()
        mock_service_class.return_value = mock_service
        
        result = await create_postgresql_service("postgresql://test")
        
        assert result is mock_service
        mock_service_class.assert_called_once_with("postgresql://test")
        mock_service.connect.assert_called_once()
    
    def test_create_book_service(self):
        """Test create_book_service convenience function."""
        mock_service = Mock()
        
        result = create_book_service(mock_service)
        
        assert isinstance(result, BookService)
        assert result._service is mock_service


@pytest.mark.integration
class TestPostgreSQLServiceIntegration:
    """Integration tests for PostgreSQL service."""
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'})
    @patch('database.postgresql_service.create_database_factory')
    async def test_full_service_workflow(self, mock_create_factory):
        """Test complete service workflow with mocked dependencies."""
        # Setup mocks
        mock_factory = Mock()
        mock_connection = AsyncMock()
        mock_book_repo = AsyncMock()
        mock_search_repo = AsyncMock()
        
        mock_create_factory.return_value = mock_factory
        mock_factory.create_connection = AsyncMock(return_value=mock_connection)
        mock_factory.create_book_repository.return_value = mock_book_repo
        mock_factory.create_search_repository.return_value = mock_search_repo
        
        # Mock repository responses
        mock_book_repo.find_book_by_url.return_value = None  # Book doesn't exist
        mock_book_repo.create_book.return_value = 123
        mock_search_repo.vector_search.return_value = [
            ("test.pdf", "Test Book", "Test Author", 1, "chunk text", 0.1)
        ]
        
        # Test workflow
        async with PostgreSQLService().lifespan_context() as service:
            # Check if book exists
            book_id = await service.find_book_by_url("test.pdf")
            assert book_id is None
            
            # Create book
            book_id = await service.create_book("test.pdf", "Test Book", "Test Author", 100)
            assert book_id == 123
            
            # Save chunks
            chunks = [(1, "chunk text", [0.1, 0.2, 0.3])]
            await service.save_chunks(book_id, chunks)
            
            # Search
            results = await service.vector_search([0.1, 0.2, 0.3])
            assert len(results) == 1
            assert results[0][0] == "test.pdf"
        
        # Verify all operations were called
        mock_book_repo.find_book_by_url.assert_called_once_with("test.pdf")
        mock_book_repo.create_book.assert_called_once_with("test.pdf", "Test Book", "Test Author", 100)
        mock_book_repo.save_chunks.assert_called_once_with(123, chunks, "chunks")
        mock_search_repo.vector_search.assert_called_once()
