"""
Unit tests for database interfaces and PostgreSQL implementations.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncpg

from database.interfaces import DatabaseConnection, DatabaseFactory
from database.postgresql import (
    PostgreSQLConnection, 
    PostgreSQLBookRepository, 
    PostgreSQLSearchRepository,
    PostgreSQLDatabaseFactory
)
from database.factory import DatabaseFactoryRegistry, create_database_factory


@pytest.mark.unit
class TestPostgreSQLConnection:
    """Test PostgreSQL connection implementation."""
    
    @pytest.fixture
    def mock_asyncpg_connection(self):
        """Create a mock asyncpg connection."""
        return AsyncMock(spec=asyncpg.Connection)
    
    @pytest.fixture
    def postgres_connection(self, mock_asyncpg_connection):
        """Create a PostgreSQL connection with mocked asyncpg connection."""
        return PostgreSQLConnection(mock_asyncpg_connection)
    
    @pytest.mark.asyncio
    async def test_execute(self, postgres_connection, mock_asyncpg_connection):
        """Test execute method."""
        mock_asyncpg_connection.execute.return_value = "SUCCESS"
        
        result = await postgres_connection.execute("INSERT INTO test VALUES ($1)", "value")
        
        assert result == "SUCCESS"
        mock_asyncpg_connection.execute.assert_called_once_with("INSERT INTO test VALUES ($1)", "value")
    
    @pytest.mark.asyncio
    async def test_fetchone(self, postgres_connection, mock_asyncpg_connection):
        """Test fetchone method."""
        mock_row = {"id": 1, "name": "test"}
        mock_asyncpg_connection.fetchrow.return_value = mock_row
        
        result = await postgres_connection.fetchone("SELECT * FROM test WHERE id = $1", 1)
        
        assert result == mock_row
        mock_asyncpg_connection.fetchrow.assert_called_once_with("SELECT * FROM test WHERE id = $1", 1)
    
    @pytest.mark.asyncio
    async def test_fetchall(self, postgres_connection, mock_asyncpg_connection):
        """Test fetchall method."""
        mock_rows = [{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}]
        mock_asyncpg_connection.fetch.return_value = mock_rows
        
        result = await postgres_connection.fetchall("SELECT * FROM test")
        
        assert result == mock_rows
        mock_asyncpg_connection.fetch.assert_called_once_with("SELECT * FROM test")
    
    @pytest.mark.asyncio
    async def test_fetchval(self, postgres_connection, mock_asyncpg_connection):
        """Test fetchval method."""
        mock_asyncpg_connection.fetchval.return_value = 42
        
        result = await postgres_connection.fetchval("SELECT COUNT(*) FROM test")
        
        assert result == 42
        mock_asyncpg_connection.fetchval.assert_called_once_with("SELECT COUNT(*) FROM test")
    
    @pytest.mark.asyncio
    async def test_close(self, postgres_connection, mock_asyncpg_connection):
        """Test close method."""
        await postgres_connection.close()
        
        mock_asyncpg_connection.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_transaction(self, postgres_connection, mock_asyncpg_connection):
        """Test transaction context manager."""
        # Create a proper async context manager for transaction
        mock_transaction_cm = AsyncMock()
        mock_transaction = AsyncMock()
        mock_transaction_cm.__aenter__.return_value = mock_transaction
        mock_transaction_cm.__aexit__.return_value = None
        
        # Override the transaction method with a regular method (not a coroutine)
        from unittest.mock import MagicMock
        mock_asyncpg_connection.transaction = MagicMock(return_value=mock_transaction_cm)
        
        async with postgres_connection.transaction() as trans:
            assert trans is not None
        
        mock_asyncpg_connection.transaction.assert_called_once()


@pytest.mark.unit
class TestPostgreSQLBookRepository:
    """Test PostgreSQL book repository implementation."""
    
    @pytest.fixture
    def mock_connection(self):
        """Create a mock database connection."""
        return AsyncMock(spec=DatabaseConnection)
    
    @pytest.fixture
    def book_repository(self, mock_connection):
        """Create a book repository with mocked connection."""
        return PostgreSQLBookRepository(mock_connection)
    
    @pytest.mark.asyncio
    async def test_find_book_by_url_found(self, book_repository, mock_connection):
        """Test finding a book by URL when it exists."""
        mock_connection.fetchval.return_value = 123
        
        result = await book_repository.find_book_by_url("test.pdf")
        
        assert result == 123
        mock_connection.fetchval.assert_called_once_with(
            "SELECT id FROM books WHERE pdf_navn LIKE $1", "%test.pdf"
        )
    
    @pytest.mark.asyncio
    async def test_find_book_by_url_not_found(self, book_repository, mock_connection):
        """Test finding a book by URL when it doesn't exist."""
        mock_connection.fetchval.return_value = None
        
        result = await book_repository.find_book_by_url("nonexistent.pdf")
        
        assert result is None
        mock_connection.fetchval.assert_called_once_with(
            "SELECT id FROM books WHERE pdf_navn LIKE $1", "%nonexistent.pdf"
        )
    
    @pytest.mark.asyncio
    async def test_create_book(self, book_repository, mock_connection):
        """Test creating a new book."""
        mock_connection.fetchval.return_value = 456
        
        result = await book_repository.create_book("new.pdf", "New Book", "Author", 100)
        
        assert result == 456
        expected_query = """
            INSERT INTO books(pdf_navn, titel, forfatter, antal_sider) 
            VALUES ($1, $2, $3, $4) RETURNING id
        """
        mock_connection.fetchval.assert_called_once_with(
            expected_query, "new.pdf", "New Book", "Author", 100
        )
    
    @pytest.mark.asyncio
    async def test_create_book_failure(self, book_repository, mock_connection):
        """Test creating a book when database returns no ID."""
        mock_connection.fetchval.return_value = None
        
        with pytest.raises(RuntimeError, match="Failed to create book - no ID returned"):
            await book_repository.create_book("new.pdf", "New Book", "Author", 100)
    
    @pytest.mark.asyncio
    async def test_save_chunks(self, book_repository, mock_connection):
        """Test saving chunks with embeddings."""
        chunks_data = [
            (1, "First chunk", [0.1, 0.2, 0.3]),
            (2, "Second chunk", [0.4, 0.5, 0.6])
        ]
        
        # Create a proper async context manager for transaction
        mock_transaction_cm = AsyncMock()
        mock_transaction = AsyncMock()
        mock_transaction_cm.__aenter__.return_value = mock_transaction
        mock_transaction_cm.__aexit__.return_value = None
        
        # Override the transaction method with a regular method (not a coroutine)
        # that returns our mock context manager
        from unittest.mock import MagicMock
        mock_connection.transaction = MagicMock(return_value=mock_transaction_cm)
        
        await book_repository.save_chunks(123, chunks_data)
        
        # Verify transaction was used
        mock_connection.transaction.assert_called_once()
        
        # Verify chunks were inserted
        expected_query = """
            INSERT INTO chunks (book_id, sidenr, chunk, embedding) 
            VALUES ($1, $2, $3, $4)
        """
        expected_calls = [
            (expected_query, 123, 1, "First chunk", [0.1, 0.2, 0.3]),
            (expected_query, 123, 2, "Second chunk", [0.4, 0.5, 0.6])
        ]
        
        assert mock_connection.execute.call_count == 2
        for i, (expected_query, *expected_args) in enumerate(expected_calls):
            actual_call = mock_connection.execute.call_args_list[i]
            assert actual_call[0] == (expected_query, *expected_args)


@pytest.mark.unit
class TestPostgreSQLSearchRepository:
    """Test PostgreSQL search repository implementation."""
    
    @pytest.fixture
    def mock_connection(self):
        """Create a mock database connection."""
        return AsyncMock(spec=DatabaseConnection)
    
    @pytest.fixture
    def search_repository(self, mock_connection):
        """Create a search repository with mocked connection."""
        return PostgreSQLSearchRepository(mock_connection)
    
    @pytest.mark.asyncio
    async def test_vector_search_default_params(self, search_repository, mock_connection):
        """Test vector search with default parameters."""
        embedding = [0.1, 0.2, 0.3]
        mock_results = [
            ("book.pdf", "Book Title", "Author", 1, "chunk text", 0.85)
        ]
        mock_connection.fetchall.return_value = mock_results
        
        result = await search_repository.vector_search(embedding)
        
        assert result == mock_results
        expected_query = """
            SELECT b.pdf_navn, b.titel, b.forfatter, c.sidenr, c.chunk, 
                   c.embedding <=> $1 AS distance
            FROM chunks c 
            JOIN books b ON c.book_id = b.id 
            ORDER BY c.embedding <=> $1 
            LIMIT $2
        """
        mock_connection.fetchall.assert_called_once_with(expected_query, embedding, 10)
    
    @pytest.mark.asyncio
    async def test_vector_search_custom_params(self, search_repository, mock_connection):
        """Test vector search with custom parameters."""
        embedding = [0.1, 0.2, 0.3]
        mock_results = []
        mock_connection.fetchall.return_value = mock_results
        
        result = await search_repository.vector_search(
            embedding, limit=5, distance_function="l2", chunk_size="large"
        )
        
        assert result == mock_results
        expected_query = """
            SELECT b.pdf_navn, b.titel, b.forfatter, c.sidenr, c.chunk, 
                   c.embedding <-> $1 AS distance
            FROM chunks_large c 
            JOIN books b ON c.book_id = b.id 
            ORDER BY c.embedding <-> $1 
            LIMIT $2
        """
        mock_connection.fetchall.assert_called_once_with(expected_query, embedding, 5)
    
    @pytest.mark.asyncio
    async def test_vector_search_unknown_chunk_size(self, search_repository, mock_connection):
        """Test vector search with unknown chunk size falls back to default."""
        embedding = [0.1, 0.2, 0.3]
        mock_connection.fetchall.return_value = []
        
        await search_repository.vector_search(embedding, chunk_size="unknown")
        
        # Should use default "chunks" table
        expected_query = """
            SELECT b.pdf_navn, b.titel, b.forfatter, c.sidenr, c.chunk, 
                   c.embedding <=> $1 AS distance
            FROM chunks c 
            JOIN books b ON c.book_id = b.id 
            ORDER BY c.embedding <=> $1 
            LIMIT $2
        """
        mock_connection.fetchall.assert_called_once_with(expected_query, embedding, 10)


@pytest.mark.unit
class TestPostgreSQLDatabaseFactory:
    """Test PostgreSQL database factory implementation."""
    
    def test_init_with_url(self):
        """Test factory initialization with explicit URL."""
        factory = PostgreSQLDatabaseFactory("postgresql://test:test@localhost/test")
        assert factory._database_url == "postgresql://test:test@localhost/test"
    
    @patch.dict("os.environ", {
        "POSTGRES_HOST": "testhost",
        "POSTGRES_PORT": "5433", 
        "POSTGRES_DB": "testdb",
        "POSTGRES_USER": "testuser",
        "POSTGRES_PASSWORD": "testpass"
    })
    def test_init_from_env(self):
        """Test factory initialization from environment variables."""
        factory = PostgreSQLDatabaseFactory()
        expected_url = "postgresql://testuser:testpass@testhost:5433/testdb"
        assert factory._database_url == expected_url
    
    @patch.dict("os.environ", {}, clear=True)
    def test_init_missing_env_vars(self):
        """Test factory initialization with missing environment variables."""
        with pytest.raises(ValueError, match="Missing required database environment variables"):
            PostgreSQLDatabaseFactory()
    
    @pytest.mark.asyncio
    @patch("database.postgresql.asyncpg.connect")
    @patch("database.postgresql.register_vector")
    async def test_create_connection(self, mock_register_vector, mock_connect):
        """Test creating a database connection."""
        mock_connection = AsyncMock()
        mock_connect.return_value = mock_connection
        
        factory = PostgreSQLDatabaseFactory("postgresql://test:test@localhost/test")
        result = await factory.create_connection()
        
        assert isinstance(result, PostgreSQLConnection)
        mock_connect.assert_called_once_with("postgresql://test:test@localhost/test")
        mock_register_vector.assert_called_once_with(mock_connection)
    
    @pytest.mark.asyncio
    @patch("database.postgresql.asyncpg.connect")
    async def test_create_connection_failure(self, mock_connect):
        """Test creating a database connection when asyncpg.connect fails."""
        mock_connect.side_effect = Exception("Connection failed")
        
        factory = PostgreSQLDatabaseFactory("postgresql://test:test@localhost/test")
        
        with pytest.raises(Exception, match="Connection failed"):
            await factory.create_connection()
    
    def test_create_book_repository(self):
        """Test creating a book repository."""
        mock_connection = MagicMock(spec=DatabaseConnection)
        factory = PostgreSQLDatabaseFactory("postgresql://test:test@localhost/test")
        
        result = factory.create_book_repository(mock_connection)
        
        assert isinstance(result, PostgreSQLBookRepository)
        assert result._connection == mock_connection
    
    def test_create_search_repository(self):
        """Test creating a search repository."""
        mock_connection = MagicMock(spec=DatabaseConnection)
        factory = PostgreSQLDatabaseFactory("postgresql://test:test@localhost/test")
        
        result = factory.create_search_repository(mock_connection)
        
        assert isinstance(result, PostgreSQLSearchRepository)
        assert result._connection == mock_connection


@pytest.mark.unit
class TestDatabaseFactoryRegistry:
    """Test database factory registry."""
    
    def test_register_factory(self):
        """Test registering a new factory."""
        class CustomFactory(DatabaseFactory):
            async def create_connection(self):
                pass
            def create_book_repository(self, connection):
                pass
            def create_search_repository(self, connection):
                pass
        
        initial_count = len(DatabaseFactoryRegistry.get_available_types())
        DatabaseFactoryRegistry.register_factory("custom", CustomFactory)
        
        assert len(DatabaseFactoryRegistry.get_available_types()) == initial_count + 1
        assert "custom" in DatabaseFactoryRegistry.get_available_types()
        
        # Clean up
        del DatabaseFactoryRegistry._factories["custom"]
    
    @patch.dict("os.environ", {
        "POSTGRES_DB": "test",
        "POSTGRES_USER": "test", 
        "POSTGRES_PASSWORD": "test"
    })
    def test_create_factory_default(self):
        """Test creating factory with default type."""
        factory = DatabaseFactoryRegistry.create_factory()
        assert isinstance(factory, PostgreSQLDatabaseFactory)
    
    @patch.dict("os.environ", {
        "DATABASE_TYPE": "postgresql",
        "POSTGRES_DB": "test",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test"
    })
    def test_create_factory_from_env(self):
        """Test creating factory from environment variable."""
        factory = DatabaseFactoryRegistry.create_factory()
        assert isinstance(factory, PostgreSQLDatabaseFactory)
    
    def test_create_factory_unknown_type(self):
        """Test creating factory with unknown type."""
        with pytest.raises(ValueError, match="Unknown database type: unknown"):
            DatabaseFactoryRegistry.create_factory("unknown")
    
    def test_get_available_types(self):
        """Test getting available factory types."""
        types = DatabaseFactoryRegistry.get_available_types()
        assert "postgresql" in types
        assert isinstance(types, list)


@pytest.mark.unit
class TestFactoryModule:
    """Test factory module convenience functions."""
    
    @patch.dict("os.environ", {
        "POSTGRES_DB": "test",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test"
    })
    def test_create_database_factory(self):
        """Test convenience function for creating database factory."""
        factory = create_database_factory()
        assert isinstance(factory, PostgreSQLDatabaseFactory)
    
    @patch.dict("os.environ", {
        "POSTGRES_DB": "test",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "test"
    })
    def test_create_database_factory_with_params(self):
        """Test convenience function with explicit parameters."""
        factory = create_database_factory("postgresql")
        assert isinstance(factory, PostgreSQLDatabaseFactory)
