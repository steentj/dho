"""
Unit tests for database interfaces.
"""
import pytest
from typing import Optional
from database.interfaces import DatabaseConnection, BookRepository, SearchRepository, DatabaseFactory


class TestDatabaseConnection:
    """Test the DatabaseConnection interface compliance."""
    
    def test_database_connection_is_abstract(self):
        """Test that DatabaseConnection cannot be instantiated directly."""
        with pytest.raises(TypeError):
            DatabaseConnection()
    
    def test_database_connection_methods_exist(self):
        """Test that all required methods exist in the interface."""
        required_methods = [
            'execute', 'fetchone', 'fetchall', 'fetchval', 'close', 'transaction'
        ]
        
        for method in required_methods:
            assert hasattr(DatabaseConnection, method)


class TestBookRepository:
    """Test the BookRepository interface compliance."""
    
    def test_book_repository_is_abstract(self):
        """Test that BookRepository cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BookRepository()
    
    def test_book_repository_methods_exist(self):
        """Test that all required methods exist in the interface."""
        required_methods = [
            'find_book_by_url', 'create_book', 'save_chunks'
        ]
        
        for method in required_methods:
            assert hasattr(BookRepository, method)


class TestSearchRepository:
    """Test the SearchRepository interface compliance."""
    
    def test_search_repository_is_abstract(self):
        """Test that SearchRepository cannot be instantiated directly."""
        with pytest.raises(TypeError):
            SearchRepository()
    
    def test_search_repository_methods_exist(self):
        """Test that all required methods exist in the interface."""
        required_methods = ['vector_search']
        
        for method in required_methods:
            assert hasattr(SearchRepository, method)


class TestDatabaseFactory:
    """Test the DatabaseFactory interface compliance."""
    
    def test_database_factory_is_abstract(self):
        """Test that DatabaseFactory cannot be instantiated directly."""
        with pytest.raises(TypeError):
            DatabaseFactory()
    
    def test_database_factory_methods_exist(self):
        """Test that all required methods exist in the interface."""
        required_methods = [
            'create_connection', 'create_book_repository', 'create_search_repository'
        ]
        
        for method in required_methods:
            assert hasattr(DatabaseFactory, method)


# Mock implementations for testing
class MockDatabaseConnection(DatabaseConnection):
    """Mock implementation for testing."""
    
    async def execute(self, query: str, *params):
        return f"EXECUTED: {query}"
    
    async def fetchone(self, query: str, *params):
        return {"id": 1, "title": "Test"}
    
    async def fetchall(self, query: str, *params):
        return [{"id": 1, "title": "Test"}, {"id": 2, "title": "Test2"}]
    
    async def fetchval(self, query: str, *params):
        return 1
    
    async def close(self):
        pass
    
    async def transaction(self):
        class MockTransaction:
            async def __aenter__(self):
                return self
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        return MockTransaction()


class MockBookRepository(BookRepository):
    """Mock implementation for testing."""
    
    async def find_book_by_url(self, pdf_url: str) -> Optional[int]:
        return 1 if pdf_url == "existing_url" else None
    
    async def create_book(self, pdf_url: str, title: str, author: str, pages: int) -> int:
        return 1
    
    async def save_chunks(self, book_id: int, chunks_with_embeddings):
        pass


class MockSearchRepository(SearchRepository):
    """Mock implementation for testing."""
    
    async def vector_search(self, embedding, limit: int = 10, 
                          distance_function: str = "cosine", chunk_size: str = "normal"):
        return [{"id": 1, "similarity": 0.95, "text": "Similar text"}]


class MockDatabaseFactory(DatabaseFactory):
    """Mock implementation for testing."""
    
    async def create_connection(self):
        return MockDatabaseConnection()
    
    def create_book_repository(self, connection):
        return MockBookRepository()
    
    def create_search_repository(self, connection):
        return MockSearchRepository()


class TestMockImplementations:
    """Test that mock implementations work correctly."""
    
    @pytest.mark.asyncio
    async def test_mock_database_connection(self):
        """Test mock database connection functionality."""
        conn = MockDatabaseConnection()
        
        result = await conn.execute("SELECT 1")
        assert "EXECUTED" in result
        
        row = await conn.fetchone("SELECT * FROM test")
        assert row["id"] == 1
        
        rows = await conn.fetchall("SELECT * FROM test")
        assert len(rows) == 2
        
        val = await conn.fetchval("SELECT COUNT(*) FROM test")
        assert val == 1
        
        await conn.close()
        
        async with await conn.transaction():
            pass  # Test transaction context manager
    
    @pytest.mark.asyncio
    async def test_mock_book_repository(self):
        """Test mock book repository functionality."""
        repo = MockBookRepository()
        
        # Test finding existing book
        book_id = await repo.find_book_by_url("existing_url")
        assert book_id == 1
        
        # Test finding non-existing book
        book_id = await repo.find_book_by_url("new_url")
        assert book_id is None
        
        # Test creating book
        new_id = await repo.create_book("new_url", "Test Title", "Test Author", 100)
        assert new_id == 1
        
        # Test saving chunks
        await repo.save_chunks(1, [])  # Should not raise
    
    @pytest.mark.asyncio
    async def test_mock_search_repository(self):
        """Test mock search repository functionality."""
        repo = MockSearchRepository()
        
        results = await repo.vector_search([0.1, 0.2, 0.3])
        assert len(results) == 1
        assert results[0]["similarity"] == 0.95
    
    @pytest.mark.asyncio
    async def test_mock_database_factory(self):
        """Test mock database factory functionality."""
        factory = MockDatabaseFactory()
        
        conn = await factory.create_connection()
        assert isinstance(conn, MockDatabaseConnection)
        
        book_repo = factory.create_book_repository(conn)
        assert isinstance(book_repo, MockBookRepository)
        
        search_repo = factory.create_search_repository(conn)
        assert isinstance(search_repo, MockSearchRepository)
