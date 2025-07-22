"""
Unit tests for PostgreSQL service error handling.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from database.postgresql_service import PostgreSQLService


@pytest.mark.unit
class TestPostgreSQLServiceErrorHandling:
    """Test PostgreSQL service error handling."""
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_connect_error_handling(self):
        """Test connect method properly handles and propagates errors."""
        # Create service
        service = PostgreSQLService()
        
        # Mock factory to raise exception during connection
        service._factory = MagicMock()
        service._factory.create_connection = AsyncMock(side_effect=Exception("Connection error"))
        
        # Call connect (should raise the exception)
        with pytest.raises(Exception, match="Connection error"):
            await service.connect()
        
        # Verify repository creation was not attempted
        assert service._connection is None
        assert service._book_repository is None
        assert service._search_repository is None
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_disconnect_error_handling(self):
        """Test disconnect method handles errors when closing connection."""
        # Create service with mock connection
        service = PostgreSQLService()
        mock_connection = AsyncMock()
        mock_connection.close = AsyncMock(side_effect=Exception("Close error"))
        service._connection = mock_connection
        
        # Call disconnect (should handle the exception)
        with pytest.raises(Exception, match="Close error"):
            await service.disconnect()
        
        # Verify close was attempted
        mock_connection.close.assert_called_once()
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_lifespan_context_error_during_connect(self):
        """Test lifespan context handles errors during connect."""
        # Create service
        service = PostgreSQLService()
        
        # Mock connect to raise exception
        service.connect = AsyncMock(side_effect=Exception("Connect error"))
        service.disconnect = AsyncMock()
        
        # Use lifespan context (should raise the exception)
        with pytest.raises(Exception, match="Connect error"):
            async with service.lifespan_context():
                pass
        
        # Verify disconnect was not called (connect failed)
        service.connect.assert_called_once()
        service.disconnect.assert_not_called()
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_lifespan_context_error_during_operation(self):
        """Test lifespan context handles errors during operation but still calls disconnect."""
        # Create service
        service = PostgreSQLService()
        
        # Mock connect and disconnect
        service.connect = AsyncMock()
        service.disconnect = AsyncMock()
        
        # Use lifespan context with exception in the body
        with pytest.raises(ValueError, match="Operation error"):
            async with service.lifespan_context():
                raise ValueError("Operation error")
        
        # Verify both connect and disconnect were called
        service.connect.assert_called_once()
        service.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_lifespan_context_error_during_disconnect(self):
        """Test lifespan context handles errors during disconnect."""
        # Create service
        service = PostgreSQLService()
        
        # Mock connect and disconnect
        service.connect = AsyncMock()
        service.disconnect = AsyncMock(side_effect=Exception("Disconnect error"))
        
        # Use lifespan context (disconnect error should propagate)
        with pytest.raises(Exception, match="Disconnect error"):
            async with service.lifespan_context():
                pass  # Normal operation
        
        # Verify both connect and disconnect were called
        service.connect.assert_called_once()
        service.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_execute_not_connected(self):
        """Test execute raises error when not connected."""
        service = PostgreSQLService()
        
        with pytest.raises(RuntimeError, match="PostgreSQL service is not connected"):
            await service.execute("SELECT 1")
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_fetchone_not_connected(self):
        """Test fetchone raises error when not connected."""
        service = PostgreSQLService()
        
        with pytest.raises(RuntimeError, match="PostgreSQL service is not connected"):
            await service.fetchone("SELECT 1")
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_fetchall_not_connected(self):
        """Test fetchall raises error when not connected."""
        service = PostgreSQLService()
        
        with pytest.raises(RuntimeError, match="PostgreSQL service is not connected"):
            await service.fetchall("SELECT 1")
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_fetchval_not_connected(self):
        """Test fetchval raises error when not connected."""
        service = PostgreSQLService()
        
        with pytest.raises(RuntimeError, match="PostgreSQL service is not connected"):
            await service.fetchval("SELECT 1")
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_find_book_by_url_not_connected(self):
        """Test find_book_by_url raises error when not connected."""
        service = PostgreSQLService()
        
        with pytest.raises(RuntimeError, match="PostgreSQL service is not connected"):
            await service.find_book_by_url("test.pdf")
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_create_book_not_connected(self):
        """Test create_book raises error when not connected."""
        service = PostgreSQLService()
        
        with pytest.raises(RuntimeError, match="PostgreSQL service is not connected"):
            await service.create_book("test.pdf", "Test Book", "Test Author", 10)
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_vector_search_not_connected(self):
        """Test vector_search raises error when not connected."""
        service = PostgreSQLService()
        
        with pytest.raises(RuntimeError, match="PostgreSQL service is not connected"):
            await service.vector_search([0.1, 0.2, 0.3])
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_vector_search_database_error(self):
        """Test vector_search handles database errors."""
        # Create service with mocks
        service = PostgreSQLService()
        mock_connection = AsyncMock()
        mock_book_repo = AsyncMock()
        mock_search_repo = AsyncMock()
        
        service._connection = mock_connection
        service._book_repository = mock_book_repo
        service._search_repository = mock_search_repo
        
        # Setup search repo to raise exception
        mock_search_repo.vector_search = AsyncMock(side_effect=Exception("Database error"))
        
        # Call vector_search (should propagate the exception)
        with pytest.raises(Exception, match="Database error"):
            await service.vector_search([0.1, 0.2, 0.3])
        
        # Verify search was attempted
        mock_search_repo.vector_search.assert_called_once()
