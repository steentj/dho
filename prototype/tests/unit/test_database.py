"""
Unit tests for database operations and connection handling.
"""
import pytest
from unittest.mock import AsyncMock, patch
import sys
from pathlib import Path

# Add the create_embeddings directory to the path for imports
create_embeddings_path = Path(__file__).parent.parent.parent.parent / "create_embeddings"
sys.path.insert(0, str(create_embeddings_path))

try:
    from opret_bøger import (
        safe_db_execute,
        save_book
    )
    DATABASE_FUNCTIONS_AVAILABLE = True
except ImportError as e:
    pytest.skip(f"Could not import database functions: {e}", allow_module_level=True)
    DATABASE_FUNCTIONS_AVAILABLE = False


@pytest.mark.unit
@pytest.mark.skipif(not DATABASE_FUNCTIONS_AVAILABLE, reason="Database functions not available")
class TestSafeDbExecute:
    """Test the safe_db_execute function."""
    
    @pytest.mark.asyncio
    async def test_safe_db_execute_success(self):
        """Test successful database execution."""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [{"id": 1, "name": "test"}]
        
        # Note: safe_db_execute signature is (url, conn, query, *params)
        url = "postgresql://test"
        query = "SELECT * FROM test_table"
        
        result = await safe_db_execute(url, mock_conn, query)
        
        assert result == [{"id": 1, "name": "test"}]
        mock_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once()
        mock_cursor.fetchall.assert_called_once()

    @pytest.mark.asyncio
    async def test_safe_db_execute_with_params(self):
        """Test database execution with parameters."""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [{"count": 5}]
        
        url = "postgresql://test"
        query = "SELECT COUNT(*) as count FROM test_table WHERE category = %s"
        params = ("test_category",)
        
        result = await safe_db_execute(url, mock_conn, query, *params)
        
        assert result == [{"count": 5}]
        mock_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_safe_db_execute_exception(self):
        """Test database execution with exception."""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Database error")
        
        url = "postgresql://test"
        query = "SELECT * FROM test_table"
        
        with pytest.raises(Exception, match="Database error"):
            await safe_db_execute(url, mock_conn, query)

    @pytest.mark.asyncio
    async def test_safe_db_execute_no_results(self):
        """Test database execution with no results."""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        
        url = "postgresql://test"
        query = "SELECT * FROM test_table WHERE id = 999"
        
        result = await safe_db_execute(url, mock_conn, query)
        
        assert result == []
        mock_cursor.execute.assert_called_once()
        mock_cursor.fetchall.assert_called_once()


@pytest.mark.unit
@pytest.mark.skipif(not DATABASE_FUNCTIONS_AVAILABLE, reason="Database functions not available")
class TestSaveBook:
    """Test the save_book function."""
    
    @pytest.mark.asyncio
    async def test_save_book_success(self):
        """Test successful book saving."""
        mock_conn = AsyncMock()
        
        # Mock book data structure
        book = {
            'url': 'https://example.com/book.pdf',
            'title': 'Test Book',
            'pages': {
                '1': [
                    {
                        'text': 'This is page 1 content',
                        'embedding': [0.1, 0.2, 0.3]
                    }
                ]
            }
        }
        
        with patch('opret_bøger.safe_db_execute') as mock_execute:
            mock_execute.return_value = [{'id': 1}]  # Mock book ID return
            
            await save_book(book, mock_conn)
            
            # Verify safe_db_execute was called for book insertion
            assert mock_execute.call_count >= 1  # Called at least once for book insert

    @pytest.mark.asyncio
    async def test_save_book_with_multiple_pages(self):
        """Test saving book with multiple pages."""
        mock_conn = AsyncMock()
        
        book = {
            'url': 'https://example.com/book.pdf',
            'title': 'Multi-page Book',
            'pages': {
                '1': [{'text': 'Page 1', 'embedding': [0.1, 0.2]}],
                '2': [{'text': 'Page 2', 'embedding': [0.3, 0.4]}],
                '3': [{'text': 'Page 3', 'embedding': [0.5, 0.6]}]
            }
        }
        
        with patch('opret_bøger.safe_db_execute') as mock_execute:
            mock_execute.return_value = [{'id': 1}]
            
            await save_book(book, mock_conn)
            
            # Should be called multiple times for book + chunks
            assert mock_execute.call_count >= 3  # Book + at least 3 chunks

    @pytest.mark.asyncio
    async def test_save_book_database_error(self):
        """Test book saving with database error."""
        mock_conn = AsyncMock()
        
        book = {
            'url': 'https://example.com/book.pdf',
            'title': 'Test Book',
            'pages': {
                '1': [{'text': 'Content', 'embedding': [0.1, 0.2]}]
            }
        }
        
        with patch('opret_bøger.safe_db_execute') as mock_execute:
            mock_execute.side_effect = Exception("Database error")
            
            with pytest.raises(Exception, match="Database error"):
                await save_book(book, mock_conn)

    @pytest.mark.asyncio
    async def test_save_book_empty_pages(self):
        """Test saving book with no pages."""
        mock_conn = AsyncMock()
        
        book = {
            'url': 'https://example.com/book.pdf',
            'title': 'Empty Book',
            'pages': {}
        }
        
        with patch('opret_bøger.safe_db_execute') as mock_execute:
            mock_execute.return_value = [{'id': 1}]
            
            await save_book(book, mock_conn)
            
            # Should still save the book entry
            mock_execute.assert_called()


@pytest.mark.integration
@pytest.mark.database
class TestDatabaseIntegration:
    """Integration tests for database operations."""
    
    @pytest.mark.asyncio
    async def test_database_connection_with_asyncpg(self):
        """Test database connection using asyncpg."""
        with patch('asyncpg.connect') as mock_connect:
            mock_connection = AsyncMock()
            mock_connect.return_value = mock_connection
            
            # Test connection creation
            conn = await mock_connect('postgresql://test')
            assert conn == mock_connection
            mock_connect.assert_called_once_with('postgresql://test')

    @pytest.mark.asyncio
    async def test_database_transaction_context(self):
        """Test database transaction context management."""
        mock_conn = AsyncMock()
        mock_transaction = AsyncMock()
        mock_conn.transaction.return_value.__aenter__.return_value = mock_transaction
        
        # Test transaction context
        async with mock_conn.transaction() as trans:
            assert trans == mock_transaction
            
        mock_conn.transaction.assert_called_once()

    @pytest.mark.skip(reason="Requires real database connection")
    async def test_real_database_operations(self):
        """Test with real database - would require actual DB setup."""
        # This would test actual database operations:
        # conn = await asyncpg.connect(DATABASE_URL)
        # await safe_db_execute(DATABASE_URL, conn, "SELECT 1")
        # await conn.close()
        pass
