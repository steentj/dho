"""
Unit tests for PostgreSQL database implementation.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from database.postgresql import PostgreSQLConnection, PostgreSQLBookRepository, PostgreSQLSearchRepository, PostgreSQLDatabaseFactory


class AsyncContextManagerMock:
    """A mock async context manager."""
    def __init__(self):
        self.enter_called = False
        self.exit_called = False
    
    async def __aenter__(self):
        self.enter_called = True
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.exit_called = True
        return None


class TestPostgreSQLConnection:
    """Test PostgreSQL database connection implementation."""
    
    def test_postgresql_connection_instantiation(self):
        """Test PostgreSQL connection can be instantiated."""
        mock_asyncpg_conn = Mock()
        conn = PostgreSQLConnection(mock_asyncpg_conn)
        assert conn._connection == mock_asyncpg_conn
    
    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful query execution."""
        mock_asyncpg_conn = AsyncMock()
        mock_asyncpg_conn.execute.return_value = "INSERT 0 1"
        
        conn = PostgreSQLConnection(mock_asyncpg_conn)
        result = await conn.execute("INSERT INTO test VALUES ($1)", "value")
        
        assert result == "INSERT 0 1"
        mock_asyncpg_conn.execute.assert_called_once_with("INSERT INTO test VALUES ($1)", "value")
    
    @pytest.mark.asyncio
    async def test_fetchone_success(self):
        """Test successful fetchone operation."""
        mock_asyncpg_conn = AsyncMock()
        mock_record = {"id": 1, "name": "test"}
        mock_asyncpg_conn.fetchrow.return_value = mock_record
        
        conn = PostgreSQLConnection(mock_asyncpg_conn)
        result = await conn.fetchone("SELECT * FROM test WHERE id = $1", 1)
        
        assert result == mock_record
        mock_asyncpg_conn.fetchrow.assert_called_once_with("SELECT * FROM test WHERE id = $1", 1)
    
    @pytest.mark.asyncio
    async def test_fetchall_success(self):
        """Test successful fetchall operation."""
        mock_asyncpg_conn = AsyncMock()
        mock_records = [{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}]
        mock_asyncpg_conn.fetch.return_value = mock_records
        
        conn = PostgreSQLConnection(mock_asyncpg_conn)
        result = await conn.fetchall("SELECT * FROM test")
        
        assert result == mock_records
        mock_asyncpg_conn.fetch.assert_called_once_with("SELECT * FROM test")
    
    @pytest.mark.asyncio
    async def test_fetchval_success(self):
        """Test successful fetchval operation."""
        mock_asyncpg_conn = AsyncMock()
        mock_asyncpg_conn.fetchval.return_value = 42
        
        conn = PostgreSQLConnection(mock_asyncpg_conn)
        result = await conn.fetchval("SELECT COUNT(*) FROM test")
        
        assert result == 42
        mock_asyncpg_conn.fetchval.assert_called_once_with("SELECT COUNT(*) FROM test")
    
    @pytest.mark.asyncio
    async def test_close_success(self):
        """Test successful connection close."""
        mock_asyncpg_conn = AsyncMock()
        
        conn = PostgreSQLConnection(mock_asyncpg_conn)
        await conn.close()
        
        mock_asyncpg_conn.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_transaction_context_manager(self):
        """Test transaction context manager."""
        mock_asyncpg_conn = Mock()
        mock_transaction = AsyncContextManagerMock()
        mock_asyncpg_conn.transaction.return_value = mock_transaction
        
        conn = PostgreSQLConnection(mock_asyncpg_conn)
        
        async with conn.transaction():
            pass
        
        mock_asyncpg_conn.transaction.assert_called_once()
        assert mock_transaction.enter_called
        assert mock_transaction.exit_called


class TestPostgreSQLBookRepository:
    """Test PostgreSQL book repository implementation."""
    
    def test_postgresql_book_repository_instantiation(self):
        """Test PostgreSQL book repository can be instantiated."""
        mock_conn = Mock()
        repo = PostgreSQLBookRepository(mock_conn)
        assert repo._connection == mock_conn
    
    @pytest.mark.asyncio
    async def test_find_book_by_url_found(self):
        """Test finding existing book by URL."""
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = 123
        
        repo = PostgreSQLBookRepository(mock_conn)
        result = await repo.find_book_by_url("http://example.com/book.pdf")
        
        assert result == 123
        mock_conn.fetchval.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_find_book_by_url_not_found(self):
        """Test finding non-existing book by URL."""
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = None
        
        repo = PostgreSQLBookRepository(mock_conn)
        result = await repo.find_book_by_url("http://example.com/nonexistent.pdf")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_create_book_success(self):
        """Test successful book creation."""
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = 456
        
        repo = PostgreSQLBookRepository(mock_conn)
        result = await repo.create_book(
            "http://example.com/book.pdf",
            "Test Book",
            "Test Author",
            100
        )
        
        assert result == 456
        mock_conn.fetchval.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_save_chunks_success(self):
        """Test successful chunks saving."""
        mock_conn = AsyncMock()
        mock_transaction = AsyncContextManagerMock()
        # Need to use a regular mock for transaction to avoid the coroutine issue
        mock_conn.transaction = Mock(return_value=mock_transaction)
        
        repo = PostgreSQLBookRepository(mock_conn)
        chunks_data = [
            (1, "First chunk text", [0.1, 0.2, 0.3]),
            (2, "Second chunk text", [0.4, 0.5, 0.6])
        ]
        
        await repo.save_chunks(1, chunks_data)
        
        mock_conn.transaction.assert_called_once()
        assert mock_transaction.enter_called
        assert mock_transaction.exit_called
        # Check that execute was called for each chunk
        assert mock_conn.execute.call_count == 2


class TestPostgreSQLSearchRepository:
    """Test PostgreSQL search repository implementation."""
    
    def test_postgresql_search_repository_instantiation(self):
        """Test PostgreSQL search repository can be instantiated."""
        mock_conn = Mock()
        repo = PostgreSQLSearchRepository(mock_conn)
        assert repo._connection == mock_conn
    
    @pytest.mark.asyncio
    async def test_vector_search_success(self):
        """Test successful vector search."""
        mock_conn = AsyncMock()
        mock_results = [
            {"id": 1, "similarity": 0.95, "text": "Similar text 1"},
            {"id": 2, "similarity": 0.87, "text": "Similar text 2"}
        ]
        mock_conn.fetchall.return_value = mock_results
        
        repo = PostgreSQLSearchRepository(mock_conn)
        results = await repo.vector_search([0.1, 0.2, 0.3], limit=5)
        
        assert len(results) == 2
        assert results == mock_results
        mock_conn.fetchall.assert_called_once()
        assert results[0]["similarity"] == 0.95
        mock_conn.fetchall.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_vector_search_with_parameters(self):
        """Test vector search with different parameters."""
        mock_conn = AsyncMock()
        mock_conn.fetchall.return_value = []
        
        repo = PostgreSQLSearchRepository(mock_conn)
        await repo.vector_search(
            [0.1, 0.2, 0.3],
            limit=10,
            distance_function="euclidean",
            chunk_size="large"
        )
        
        mock_conn.fetchall.assert_called_once()


class TestPostgreSQLDatabaseFactory:
    """Test PostgreSQL database factory implementation."""
    
    @patch.dict('os.environ', {'TESTING': 'true'})
    def test_postgresql_database_factory_instantiation(self):
        """Test PostgreSQL database factory can be instantiated."""
        factory = PostgreSQLDatabaseFactory()
        assert factory is not None
    
    @pytest.mark.asyncio
    @patch('asyncpg.connect')
    @patch.dict('os.environ', {'TESTING': 'true'})
    async def test_create_connection_success(self, mock_connect):
        """Test successful connection creation."""
        mock_asyncpg_conn = AsyncMock()
        mock_connect.return_value = mock_asyncpg_conn
        
        factory = PostgreSQLDatabaseFactory()
        
        with patch.dict('os.environ', {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'test_db',
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_pass'
        }):
            conn = await factory.create_connection()
        
        assert isinstance(conn, PostgreSQLConnection)
        assert conn._connection == mock_asyncpg_conn
    
    @patch.dict('os.environ', {'TESTING': 'true'})
    def test_create_book_repository(self):
        """Test book repository creation."""
        factory = PostgreSQLDatabaseFactory()
        mock_conn = Mock()
        
        repo = factory.create_book_repository(mock_conn)
        
        assert isinstance(repo, PostgreSQLBookRepository)
        assert repo._connection == mock_conn
    
    @patch.dict('os.environ', {'TESTING': 'true'})
    def test_create_search_repository(self):
        """Test search repository creation."""
        factory = PostgreSQLDatabaseFactory()
        mock_conn = Mock()
        
        repo = factory.create_search_repository(mock_conn)
        
        assert isinstance(repo, PostgreSQLSearchRepository)
        assert repo._connection == mock_conn


class TestPostgreSQLIntegration:
    """Integration tests for PostgreSQL components."""
    
    @pytest.mark.asyncio
    @patch('asyncpg.connect')
    @patch.dict('os.environ', {'TESTING': 'true'})
    async def test_full_workflow(self, mock_connect):
        """Test complete workflow with all components."""
        # Setup mocks
        mock_asyncpg_conn = AsyncMock()
        mock_connect.return_value = mock_asyncpg_conn
        
        # Create factory and connection
        factory = PostgreSQLDatabaseFactory()
        conn = await factory.create_connection()
        
        # Create repositories
        book_repo = factory.create_book_repository(conn)
        search_repo = factory.create_search_repository(conn)
        
        # Verify all components are properly linked
        assert isinstance(conn, PostgreSQLConnection)
        assert isinstance(book_repo, PostgreSQLBookRepository)
        assert isinstance(search_repo, PostgreSQLSearchRepository)
        assert book_repo._connection == conn
        assert search_repo._connection == conn
