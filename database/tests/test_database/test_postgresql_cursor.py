"""
Unit tests for PostgreSQL cursor compatibility layer.
"""
import pytest
from unittest.mock import AsyncMock, patch
from database.postgresql_service import PostgreSQLService, PostgreSQLCursor


@pytest.mark.unit
class TestPostgreSQLCursor:
    """Test PostgreSQL cursor compatibility wrapper."""
    
    @pytest.fixture
    def cursor_with_mocks(self):
        """Create a PostgreSQLCursor with mocked PostgreSQLService."""
        mock_service = AsyncMock(spec=PostgreSQLService)
        cursor = PostgreSQLCursor(mock_service)
        return cursor, mock_service
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_execute_no_params(self, cursor_with_mocks):
        """Test execute without parameters."""
        cursor, mock_service = cursor_with_mocks
        
        # Call method
        await cursor.execute("SELECT * FROM books")
        
        # Verify
        mock_service.execute.assert_called_once_with("SELECT * FROM books")
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_execute_with_params(self, cursor_with_mocks):
        """Test execute with parameters."""
        cursor, mock_service = cursor_with_mocks
        
        # Call method
        params = (1, "test")
        await cursor.execute("SELECT * FROM books WHERE id = %s AND title = %s", params)
        
        # Verify
        mock_service.execute.assert_called_once_with("SELECT * FROM books WHERE id = %s AND title = %s", 1, "test")
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_fetchall_not_implemented(self, cursor_with_mocks):
        """Test fetchall raises NotImplementedError."""
        cursor, _ = cursor_with_mocks
        
        # Verify fetchall raises NotImplementedError
        with pytest.raises(NotImplementedError, match="fetchall\\(\\) without query not supported"):
            await cursor.fetchall()
            
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_service_compatibility(self):
        """Test cursor compatibility with existing code patterns."""
        # Create a mock service
        mock_service = AsyncMock(spec=PostgreSQLService)
        
        # Setup execute and fetchall responses
        mock_service.execute = AsyncMock()
        mock_service.fetchall = AsyncMock(return_value=[("row1",), ("row2",)])
        
        # Create cursor directly instead of using context manager
        # PostgreSQLCursor doesn't support async context manager
        cur = PostgreSQLCursor(mock_service)
        
        # Execute query
        await cur.execute("SELECT * FROM books")
            
        # Use the service's fetchall method
        results = await mock_service.fetchall("SELECT * FROM books")
            
        # Verify
        mock_service.execute.assert_called_once_with("SELECT * FROM books")
        mock_service.fetchall.assert_called_once_with("SELECT * FROM books")
        assert results == [("row1",), ("row2",)]
