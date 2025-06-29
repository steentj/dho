"""
PostgreSQL service layer for DHO Semantic Search System.

This service provides high-level database operations using the dependency injection
infrastructure while maintaining compatibility with existing application code.
"""

import logging
from typing import List, Tuple, Optional, Dict, Any
from contextlib import asynccontextmanager

from .factory import create_database_factory
from .interfaces import DatabaseConnection, BookRepository, SearchRepository, DatabaseFactory


logger = logging.getLogger(__name__)


class PostgreSQLService:
    """
    High-level PostgreSQL service that maintains current application behavior.
    
    This service wraps the dependency injection infrastructure and provides
    a convenient interface for the application layer.
    """
    
    def __init__(self, database_url: str = None):
        """
        Initialize PostgreSQL service.
        
        Args:
            database_url: Optional database URL override
        """
        self._factory: DatabaseFactory = create_database_factory("postgresql", database_url=database_url)
        self._connection: Optional[DatabaseConnection] = None
        self._book_repository: Optional[BookRepository] = None
        self._search_repository: Optional[SearchRepository] = None
    
    async def connect(self) -> None:
        """Establish database connection and initialize repositories."""
        try:
            self._connection = await self._factory.create_connection()
            self._book_repository = self._factory.create_book_repository(self._connection)
            self._search_repository = self._factory.create_search_repository(self._connection)
            logger.info("PostgreSQL service connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect PostgreSQL service: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close database connection."""
        try:
            if self._connection:
                await self._connection.close()
                self._connection = None
                self._book_repository = None
                self._search_repository = None
                logger.info("PostgreSQL service disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting PostgreSQL service: {e}")
            raise
    
    @asynccontextmanager
    async def lifespan_context(self):
        """
        Context manager for service lifecycle management.
        
        Usage:
            async with service.lifespan_context():
                # Service is connected and ready
                results = await service.search(...)
        """
        await self.connect()
        try:
            yield self
        finally:
            await self.disconnect()
    
    # Connection interface for existing code compatibility
    async def execute(self, query: str, *params) -> Optional[Any]:
        """Execute a query and return the result."""
        self._ensure_connected()
        return await self._connection.execute(query, *params)
    
    async def fetchone(self, query: str, *params) -> Optional[Tuple]:
        """Execute a query and return one row."""
        self._ensure_connected()
        return await self._connection.fetchone(query, *params)
    
    async def fetchall(self, query: str, *params) -> List[Tuple]:
        """Execute a query and return all rows."""
        self._ensure_connected()
        return await self._connection.fetchall(query, *params)
    
    async def fetchval(self, query: str, *params) -> Optional[Any]:
        """Execute a query and return a single value."""
        self._ensure_connected()
        return await self._connection.fetchval(query, *params)
    
    @asynccontextmanager
    async def transaction(self):
        """Context manager for database transactions."""
        self._ensure_connected()
        async with self._connection.transaction():
            yield
    
    # High-level repository operations
    async def find_book_by_url(self, pdf_url: str) -> Optional[int]:
        """Find a book by its PDF URL and return the book ID if found."""
        self._ensure_connected()
        return await self._book_repository.find_book_by_url(pdf_url)
    
    async def create_book(self, pdf_url: str, title: str, author: str, pages: int) -> int:
        """Create a new book and return its ID."""
        self._ensure_connected()
        return await self._book_repository.create_book(pdf_url, title, author, pages)
    
    async def save_chunks(self, book_id: int, chunks_with_embeddings: List[Tuple[int, str, List[float]]], table_name: str = "chunks") -> None:
        """Save chunks and their embeddings for a book.
        
        Args:
            book_id: The database ID of the book
            chunks_with_embeddings: List of tuples containing (page_nr, chunk_text, embedding)
            table_name: Name of the table to store chunks in (default: "chunks")
        """
        self._ensure_connected()
        return await self._book_repository.save_chunks(book_id, chunks_with_embeddings, table_name)
    
    async def vector_search(
        self, 
        embedding: List[float], 
        limit: int = 10, 
        distance_function: str = "cosine",
        chunk_size: str = "normal"
    ) -> List[Tuple]:
        """Perform vector similarity search."""
        self._ensure_connected()
        return await self._search_repository.vector_search(
            embedding, limit, distance_function, chunk_size
        )
    
    # Legacy compatibility methods for existing dhosearch.py
    async def cursor(self):
        """
        Compatibility method that returns a cursor-like object.
        
        This maintains compatibility with existing code that uses:
        async with db_conn.cursor() as cur:
            await cur.execute(...)
            results = await cur.fetchall()
        """
        return PostgreSQLCursor(self)
    
    def _ensure_connected(self):
        """Ensure the service is connected to the database."""
        if not self._connection:
            raise RuntimeError("PostgreSQL service is not connected. Call connect() first.")


class PostgreSQLCursor:
    """
    Cursor-like object for compatibility with existing dhosearch.py code.
    
    This allows existing code to work without modification while using
    the new service infrastructure underneath.
    """
    
    def __init__(self, service: PostgreSQLService):
        self._service = service
    
    async def execute(self, query: str, params: Tuple = None) -> None:
        """Execute a query with optional parameters."""
        if params:
            await self._service.execute(query, *params)
        else:
            await self._service.execute(query)
    
    async def fetchall(self) -> List[Tuple]:
        """Fetch all remaining rows from the last query."""
        # Note: In real cursor implementation, this would fetch from the last query
        # For now, this is a simplified implementation for compatibility
        # The actual query execution happens in execute() method above
        # This is a limitation of this compatibility approach
        raise NotImplementedError(
            "fetchall() without query not supported. Use service.fetchall(query, *params) instead."
        )


class BookService:
    """
    Convenience service for book-related operations.
    
    This provides a more focused interface for book operations,
    maintaining compatibility with the existing opret_bøger.py workflow.
    """
    
    def __init__(self, service: PostgreSQLService):
        self._service = service
    
    async def save_book(self, book: Dict[str, Any]) -> int:
        """
        Save a complete book with all its data.
        
        Args:
            book: Dictionary with book data in the format used by opret_bøger.py
                  {
                      "pdf-url": str,
                      "titel": str, 
                      "forfatter": str,
                      "sider": int,
                      "chunks": List[Tuple[int, str]],  # (page_num, chunk_text)
                      "embeddings": List[List[float]]
                  }
                  
        Returns:
            int: The book ID
        """
        async with self._service.transaction():
            # Create the book record
            book_id = await self._service.create_book(
                book["pdf-url"],
                book["titel"], 
                book["forfatter"],
                book["sider"]
            )
            
            # Prepare chunks with embeddings in the format expected by the repository
            chunks_with_embeddings = []
            for (page_num, chunk_text), embedding in zip(book["chunks"], book["embeddings"]):
                chunks_with_embeddings.append((page_num, chunk_text, embedding))
            
            # Save all chunks
            await self._service.save_chunks(book_id, chunks_with_embeddings)
            
            return book_id
    
    async def safe_db_execute(self, url: str, query: str, *params) -> Optional[Any]:
        """
        Compatibility wrapper for the safe_db_execute function in opret_bøger.py.
        
        Args:
            url: PDF URL (for logging purposes)
            query: SQL query
            *params: Query parameters
            
        Returns:
            Query result or None on error
        """
        try:
            return await self._service.fetchval(query, *params)
        except Exception as e:
            logger.exception(f"Databasefejl ved query '{query}' for {url}: {e}")
            return None
    
    async def get_or_create_book(self, pdf_url: str, title: str = None, author: str = None, pages: int = None) -> int:
        """
        Get an existing book by URL or create a new one if it doesn't exist.
        
        This method enables metadata reuse - if a book already exists in the database,
        its existing metadata is preserved. New metadata is only used if the book
        doesn't exist yet.
        
        Args:
            pdf_url: The PDF URL to search for
            title: Title to use if creating a new book (optional if book exists)
            author: Author to use if creating a new book (optional if book exists)  
            pages: Page count to use if creating a new book (optional if book exists)
            
        Returns:
            int: The book ID (either existing or newly created)
            
        Raises:
            ValueError: If book doesn't exist and required metadata is missing
        """
        # First try to find existing book
        existing_book_id = await self._service.find_book_by_url(pdf_url)
        
        if existing_book_id:
            # Book already exists - return its ID
            return existing_book_id
        
        # Book doesn't exist - validate we have metadata to create it
        if not title or not author or not pages or pages <= 0:
            raise ValueError(
                f"Book not found at {pdf_url} and insufficient metadata provided to create it. "
                f"Required: title, author, pages (>0). Provided: title={title}, author={author}, pages={pages}"
            )
        
        # Create new book with provided metadata
        return await self._service.create_book(pdf_url, title, author, pages)


# Convenience functions for easy integration
async def create_postgresql_service(database_url: str = None) -> PostgreSQLService:
    """
    Create and connect a PostgreSQL service.
    
    Args:
        database_url: Optional database URL override
        
    Returns:
        Connected PostgreSQLService instance
    """
    service = PostgreSQLService(database_url)
    await service.connect()
    return service


def create_book_service(service: PostgreSQLService) -> BookService:
    """
    Create a book service from a PostgreSQL service.
    
    Args:
        service: Connected PostgreSQL service
        
    Returns:
        BookService instance
    """
    return BookService(service)
