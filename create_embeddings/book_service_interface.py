"""
Book service interface for dependency injection.

This module defines the contract for book processing operations,
eliminating magic string detection and hasattr() checks.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class IBookService(ABC):
    """Abstract interface for book processing operations."""
    
    @abstractmethod
    async def save_book_with_chunks(self, book: Dict[str, Any], table_name: str) -> int:
        """
        Save a complete book with all its data (metadata, chunks, and embeddings).
        
        Args:
            book: Dictionary with book data in the format used by opret_bøger.py
                  {
                      "pdf-url" or "pdf_url": str,  # Accept both formats
                      "titel": str, 
                      "forfatter": str,
                      "sider": int,
                      "chunks": List[Tuple[int, str]],  # (page_num, chunk_text)
                      "embeddings": List[List[float]]
                  }
            table_name: Name of the table to save chunks to (provider-specific)
                  
        Returns:
            int: The book ID
        """
        pass
    
    @abstractmethod 
    async def book_exists_with_provider(self, pdf_url: str, provider_name: str) -> bool:
        """
        Check if book exists with embeddings for a specific provider.
        
        Args:
            pdf_url: The PDF URL to check
            provider_name: Name of the embedding provider (e.g., "openai", "ollama")
            
        Returns:
            bool: True if book exists with embeddings for this provider
        """
        pass
