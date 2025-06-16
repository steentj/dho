"""
PostgreSQL implementation of database interfaces.

This module provides concrete implementations of the database interfaces
for PostgreSQL with pgvector support.
"""
import os
import logging
from typing import List, Tuple, Optional, Any
from contextlib import asynccontextmanager

import asyncpg
from pgvector.asyncpg import register_vector

from .interfaces import DatabaseConnection, BookRepository, SearchRepository, DatabaseFactory


logger = logging.getLogger(__name__)


class PostgreSQLConnection(DatabaseConnection):
    """PostgreSQL implementation of DatabaseConnection."""
    
    def __init__(self, connection: asyncpg.Connection):
        self._connection = connection
    
    async def execute(self, query: str, *params) -> Optional[Any]:
        """Execute a query and return the result."""
        try:
            return await self._connection.execute(query, *params)
        except Exception as e:
            logger.error(f"Error executing query '{query}': {e}")
            raise
    
    async def fetchone(self, query: str, *params) -> Optional[Tuple]:
        """Execute a query and return one row."""
        try:
            return await self._connection.fetchrow(query, *params)
        except Exception as e:
            logger.error(f"Error fetching one row for query '{query}': {e}")
            raise
    
    async def fetchall(self, query: str, *params) -> List[Tuple]:
        """Execute a query and return all rows."""
        try:
            return await self._connection.fetch(query, *params)
        except Exception as e:
            logger.error(f"Error fetching all rows for query '{query}': {e}")
            raise
    
    async def fetchval(self, query: str, *params) -> Optional[Any]:
        """Execute a query and return a single value."""
        try:
            return await self._connection.fetchval(query, *params)
        except Exception as e:
            logger.error(f"Error fetching value for query '{query}': {e}")
            raise
    
    async def close(self) -> None:
        """Close the database connection."""
        try:
            await self._connection.close()
        except Exception as e:
            logger.error(f"Error closing connection: {e}")
            raise
    
    @asynccontextmanager
    async def transaction(self):
        """Context manager for database transactions."""
        async with self._connection.transaction() as transaction:
            yield transaction


class PostgreSQLBookRepository(BookRepository):
    """PostgreSQL implementation of BookRepository."""
    
    def __init__(self, connection: DatabaseConnection):
        self._connection = connection
    
    async def find_book_by_url(self, pdf_url: str) -> Optional[int]:
        """Find a book by its PDF URL and return the book ID if found."""
        like_pattern = f"%{pdf_url}"
        query = "SELECT id FROM books WHERE pdf_navn LIKE $1"
        return await self._connection.fetchval(query, like_pattern)
    
    async def create_book(self, pdf_url: str, title: str, author: str, pages: int) -> int:
        """Create a new book and return its ID."""
        query = """
            INSERT INTO books(pdf_navn, titel, forfatter, antal_sider) 
            VALUES ($1, $2, $3, $4) RETURNING id
        """
        book_id = await self._connection.fetchval(query, pdf_url, title, author, pages)
        if book_id is None:
            raise RuntimeError("Failed to create book - no ID returned")
        return book_id
    
    async def save_chunks(self, book_id: int, chunks_with_embeddings: List[Tuple[int, str, List[float]]]) -> None:
        """Save chunks and their embeddings for a book."""
        query = """
            INSERT INTO chunks (book_id, sidenr, chunk, embedding) 
            VALUES ($1, $2, $3, $4)
        """
        
        async with self._connection.transaction():
            for page_nr, chunk_text, embedding in chunks_with_embeddings:
                await self._connection.execute(query, book_id, page_nr, chunk_text, embedding)


class PostgreSQLSearchRepository(SearchRepository):
    """PostgreSQL implementation of SearchRepository."""
    
    def __init__(self, connection: DatabaseConnection):
        self._connection = connection
    
    async def vector_search(
        self, 
        embedding: List[float], 
        limit: int = 10, 
        distance_function: str = "cosine",
        chunk_size: str = "normal"
    ) -> List[Tuple]:
        """Perform vector similarity search."""
        # Map chunk size to table name
        table_map = {
            "normal": "chunks",
            "large": "chunks_large", 
            "small": "chunks_small",
            "tiny": "chunks_tiny"
        }
        table = table_map.get(chunk_size, "chunks")
        
        # Map distance function to operator
        operator_map = {
            "cosine": "<=>",
            "l2": "<->", 
            "inner_product": "<#>",
            "l1": "<+>"
        }
        distance_operator = operator_map.get(distance_function, "<=>")
        
        query = f"""
            SELECT b.pdf_navn, b.titel, b.forfatter, c.sidenr, c.chunk, 
                   c.embedding {distance_operator} $1 AS distance
            FROM {table} c 
            JOIN books b ON c.book_id = b.id 
            ORDER BY c.embedding {distance_operator} $1 
            LIMIT $2
        """
        
        return await self._connection.fetchall(query, embedding, limit)


class PostgreSQLDatabaseFactory(DatabaseFactory):
    """PostgreSQL implementation of DatabaseFactory."""
    
    def __init__(self, database_url: str = None, **kwargs):
        """Initialize PostgreSQL factory.
        
        Args:
            database_url: Database connection URL
            **kwargs: Additional keyword arguments (ignored for compatibility)
        """
        self._database_url = database_url or self._build_database_url()
    
    def _build_database_url(self) -> str:
        """Build database URL from environment variables."""
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        database = os.getenv("POSTGRES_DB")
        user = os.getenv("POSTGRES_USER")
        password = os.getenv("POSTGRES_PASSWORD")
        
        if not all([database, user, password]):
            # For testing, provide a default URL if environment variables are missing
            if os.getenv("TESTING", "false").lower() == "true":
                return "postgresql://test_user:test_password@localhost:5432/test_db"
            raise ValueError("Missing required database environment variables")
        
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    async def create_connection(self) -> DatabaseConnection:
        """Create a database connection."""
        try:
            connection = await asyncpg.connect(self._database_url)
            await register_vector(connection)
            return PostgreSQLConnection(connection)
        except Exception as e:
            logger.error(f"Failed to create database connection: {e}")
            raise
    
    def create_book_repository(self, connection: DatabaseConnection) -> BookRepository:
        """Create a book repository with the given connection."""
        return PostgreSQLBookRepository(connection)
    
    def create_search_repository(self, connection: DatabaseConnection) -> SearchRepository:
        """Create a search repository with the given connection."""
        return PostgreSQLSearchRepository(connection)
