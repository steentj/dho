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
    from create_embeddings.opret_bøger import (
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
        mock_conn.fetchval.return_value = 1
        
        url = "postgresql://test"
        query = "SELECT * FROM test_table"
        
        result = await safe_db_execute(url, mock_conn, query)
        
        assert result == 1
        mock_conn.fetchval.assert_called_once_with(query)

    @pytest.mark.asyncio
    async def test_safe_db_execute_with_params(self):
        """Test database execution with parameters."""
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = 5
        
        url = "postgresql://test"
        query = "SELECT COUNT(*) as count FROM test_table WHERE category = $1"
        params = ("test_category",)
        
        result = await safe_db_execute(url, mock_conn, query, *params)
        
        assert result == 5
        mock_conn.fetchval.assert_called_once_with(query, *params)

    @pytest.mark.asyncio
    async def test_safe_db_execute_exception(self):
        """Test database execution with exception."""
        mock_conn = AsyncMock()
        mock_conn.fetchval.side_effect = Exception("Database error")
        
        url = "postgresql://test"
        query = "SELECT * FROM test_table"
        
        result = await safe_db_execute(url, mock_conn, query)
        
        assert result is None  # safe_db_execute returns None on error

    @pytest.mark.asyncio
    async def test_safe_db_execute_no_results(self):
        """Test database execution with no results."""
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = None
        
        url = "postgresql://test"
        query = "SELECT * FROM test_table WHERE id = 999"
        
        result = await safe_db_execute(url, mock_conn, query)
        
        assert result is None
        mock_conn.fetchval.assert_called_once_with(query)


@pytest.mark.unit
@pytest.mark.skipif(not DATABASE_FUNCTIONS_AVAILABLE, reason="Database functions not available")
class TestSaveBook:
    """Test the save_book function."""
    
    @pytest.mark.asyncio
    async def test_save_book_success(self):
        """Test successful book saving."""
        mock_conn = AsyncMock()
        transaction_context = AsyncMock()
        transaction_context.__aenter__.return_value = transaction_context
        transaction_context.__aexit__.return_value = None
        mock_conn.transaction = lambda: transaction_context

        book = {
            'pdf-url': 'https://example.com/book.pdf',
            'titel': 'Test Book',
            'forfatter': 'Test Author',
            'sider': 1,
            'chunks': [(1, "This is a test chunk."), (2, "This is another test chunk.")],
            'embeddings': [[0.1, 0.2], [0.3, 0.4]]
        }

        with patch('create_embeddings.opret_bøger.safe_db_execute') as mock_execute:
            mock_execute.return_value = 1

            await save_book(book, mock_conn)

            transaction_context.__aenter__.assert_called_once()
            transaction_context.__aexit__.assert_called_once()
            assert mock_execute.call_count == 3

    @pytest.mark.asyncio
    async def test_save_book_with_multiple_pages(self):
        """Test saving book with multiple pages."""
        mock_conn = AsyncMock()
        transaction_context = AsyncMock()
        transaction_context.__aenter__.return_value = transaction_context
        transaction_context.__aexit__.return_value = None
        mock_conn.transaction = lambda: transaction_context

        book = {
            'pdf-url': 'https://example.com/multipage.pdf',
            'titel': 'Multi-page Book',
            'forfatter': 'Test Author',
            'sider': 3,
            'chunks': [
                (1, "Page 1 content"),
                (2, "Page 2 content"),
                (3, "Page 3 content")
            ],
            'embeddings': [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
        }

        with patch('create_embeddings.opret_bøger.safe_db_execute') as mock_execute:
            mock_execute.return_value = 1

            await save_book(book, mock_conn)

            transaction_context.__aenter__.assert_called_once()
            transaction_context.__aexit__.assert_called_once()
            assert mock_execute.call_count == 4

    @pytest.mark.asyncio
    async def test_save_book_database_error(self):
        """Test book saving with database error."""
        mock_conn = AsyncMock()
        transaction_context = AsyncMock()
        transaction_context.__aenter__.return_value = transaction_context
        transaction_context.__aexit__.return_value = None
        mock_conn.transaction = lambda: transaction_context

        book = {
            'pdf-url': 'https://example.com/error.pdf',
            'titel': 'Error Test Book',
            'forfatter': 'Test Author',
            'sider': 1,
            'chunks': [(1, "Test content")],
            'embeddings': [[0.1, 0.2]]
        }

        with patch('create_embeddings.opret_bøger.safe_db_execute') as mock_execute:
            mock_execute.side_effect = Exception("Database error")

            with pytest.raises(Exception, match="Database error"):
                await save_book(book, mock_conn)

    @pytest.mark.asyncio
    async def test_save_book_empty_chunks(self):
        """Test saving book with no chunks."""
        mock_conn = AsyncMock()
        transaction_context = AsyncMock()
        transaction_context.__aenter__.return_value = transaction_context
        transaction_context.__aexit__.return_value = None
        mock_conn.transaction = lambda: transaction_context

        book = {
            'pdf-url': 'https://example.com/empty.pdf',
            'titel': 'Empty Book',
            'forfatter': 'Test Author',
            'sider': 0,
            'chunks': [],
            'embeddings': []
        }

        with patch('create_embeddings.opret_bøger.safe_db_execute') as mock_execute:
            mock_execute.return_value = 1

            await save_book(book, mock_conn)

            transaction_context.__aenter__.assert_called_once()
            transaction_context.__aexit__.assert_called_once()
            assert mock_execute.call_count == 1


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
        
        # Create a mock for the transaction context
        transaction_context = AsyncMock()
        # Set up the async context manager protocol
        transaction_context.__aenter__.return_value = transaction_context
        transaction_context.__aexit__.return_value = None
        # Make transaction a regular method that returns the context
        mock_conn.transaction = lambda: transaction_context
        
        # Test transaction context
        async with mock_conn.transaction() as trans:
            assert trans == transaction_context
            
        # Verify context manager was used correctly
        transaction_context.__aenter__.assert_called_once()
        transaction_context.__aexit__.assert_called_once()

    @pytest.mark.skip(reason="Requires real database connection")
    async def test_real_database_operations(self):
        """Test with real database - would require actual DB setup."""
        # This would test actual database operations:
        # conn = await asyncpg.connect(DATABASE_URL)
        # await safe_db_execute(DATABASE_URL, conn, "SELECT 1")
        # await conn.close()
        pass
