"""
Database interfaces for dependency injection.

This module defines the contracts for database operations,
enabling pluggable database implementations.
"""
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Any
from contextlib import asynccontextmanager


class DatabaseConnection(ABC):
    """Abstract interface for database connections."""
    
    @abstractmethod
    async def execute(self, query: str, *params) -> Optional[Any]:
        """Execute a query and return the result."""
        pass
    
    @abstractmethod
    async def fetchone(self, query: str, *params) -> Optional[Tuple]:
        """Execute a query and return one row."""
        pass
    
    @abstractmethod
    async def fetchall(self, query: str, *params) -> List[Tuple]:
        """Execute a query and return all rows."""
        pass
    
    @abstractmethod
    async def fetchval(self, query: str, *params) -> Optional[Any]:
        """Execute a query and return a single value."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the database connection."""
        pass
    
    @abstractmethod
    @asynccontextmanager
    async def transaction(self):
        """Context manager for database transactions."""
        pass


class BookRepository(ABC):
    """Abstract interface for book database operations."""
    
    @abstractmethod
    async def find_book_by_url(self, pdf_url: str) -> Optional[int]:
        """Find a book by its PDF URL and return the book ID if found."""
        pass
    
    @abstractmethod
    async def create_book(self, pdf_url: str, title: str, author: str, pages: int) -> int:
        """Create a new book and return its ID."""
        pass
    
    @abstractmethod
    async def save_chunks(self, book_id: int, chunks_with_embeddings: List[Tuple[int, str, List[float]]], table_name: str = "chunks") -> None:
        """Save chunks and their embeddings for a book.
        
        Args:
            book_id: The database ID of the book
            chunks_with_embeddings: List of tuples containing (page_nr, chunk_text, embedding)
            table_name: Name of the table to store chunks in (default: "chunks")
        """
        pass


class SearchRepository(ABC):
    """Abstract interface for search operations."""
    
    @abstractmethod
    async def vector_search(
        self, 
        embedding: List[float], 
        limit: int = 10, 
        distance_function: str = "cosine",
        chunk_size: str = "normal"
    ) -> List[Tuple]:
        """Perform vector similarity search."""
        pass


class DatabaseFactory(ABC):
    """Abstract factory for creating database components."""
    
    @abstractmethod
    async def create_connection(self) -> DatabaseConnection:
        """Create a database connection."""
        pass
    
    @abstractmethod
    def create_book_repository(self, connection: DatabaseConnection) -> BookRepository:
        """Create a book repository with the given connection."""
        pass
    
    @abstractmethod
    def create_search_repository(self, connection: DatabaseConnection) -> SearchRepository:
        """Create a search repository with the given connection."""
        pass
