"""
Test utilities for create_embeddings package tests.

This module provides shared test utilities for transitioning from the
standalone functions to the modern architecture using pipeline, orchestrator,
and factory patterns.

Creation date/time: 22. juli 2025, 10:30
Last Modified date/time: 22. juli 2025, 16:45
"""

from typing import Dict, Any, List, Iterable
from unittest.mock import MagicMock

from create_embeddings.book_processing_pipeline import BookProcessingPipeline
from create_embeddings.providers.factory import EmbeddingProviderFactory
from create_embeddings.providers.embedding_providers import OpenAIEmbeddingProvider, DummyEmbeddingProvider
from create_embeddings.chunking import SentenceSplitterChunkingStrategy


def indlæs_urls_adapter(file_path: str) -> List[str]:
    """
    Adapter function that provides the same interface as the old indlæs_urls
    but delegates to BookProcessingPipeline.load_urls_from_file.
    
    Args:
        file_path: Path to the file containing URLs
        
    Returns:
        List of URLs to process
    """
    # Create a minimal pipeline instance just for URL loading
    pipeline = BookProcessingPipeline(
        book_service=MagicMock(),
        embedding_provider=MagicMock(),
        chunking_strategy=MagicMock()
    )
    
    # Call the pipeline's method
    return pipeline.load_urls_from_file(file_path)


def extract_text_by_page_adapter(pdf) -> Dict[int, str]:
    """
    Adapter function that provides the same interface as the old extract_text_by_page
    but delegates to BookProcessingPipeline.extract_text_by_page.
    
    This helps tests transition from using the old standalone function to the 
    new class method without breaking existing test code.
    
    Args:
        pdf: PDF document to extract text from
        
    Returns:
        Dict mapping page numbers to their text content
    """
    # Create a minimal pipeline instance just for text extraction
    pipeline = BookProcessingPipeline(
        book_service=MagicMock(),
        embedding_provider=MagicMock(),
        chunking_strategy=MagicMock()
    )
    
    # Call the pipeline's method
    return pipeline.extract_text_by_page(pdf)


async def parse_book_adapter(pdf, book_url, chunk_size, embedding_provider, chunking_strategy) -> Dict[str, Any]:
    """
    Adapter function that provides the same interface as the old parse_book function
    but delegates to BookProcessingPipeline.parse_pdf_to_book_data.
    
    Args:
        pdf: PDF document to parse
        book_url: URL of the PDF
        chunk_size: Maximum size for text chunks
        embedding_provider: Provider for generating embeddings
        chunking_strategy: Strategy for text chunking
        
    Returns:
        Dict containing book metadata, chunks, and embeddings
    """
    # Create a minimal pipeline instance
    pipeline = BookProcessingPipeline(
        book_service=MagicMock(),
        embedding_provider=embedding_provider,
        chunking_strategy=chunking_strategy
    )
    
    # Call the pipeline's method
    return await pipeline.parse_pdf_to_book_data(pdf, book_url, chunk_size)


async def process_book_adapter(book_url, chunk_size, book_service, session, embedding_provider, chunking_strategy):
    """
    Adapter for the old process_book function.
    Delegates to BookProcessingPipeline.process_book_from_url.
    
    Args:
        book_url: URL of the PDF to process
        chunk_size: Maximum size for text chunks
        book_service: Service for database operations
        session: HTTP session for fetching PDFs
        embedding_provider: Provider for generating embeddings
        chunking_strategy: Strategy for text chunking
    """
    # Create pipeline with injected dependencies
    pipeline = BookProcessingPipeline(
        book_service=book_service,
        embedding_provider=embedding_provider,
        chunking_strategy=chunking_strategy
    )
    
    # Delegate to pipeline
    await pipeline.process_book_from_url(book_url, chunk_size, session)


def chunk_text_adapter(text, max_tokens, title=None):
    """
    Adapter for the old chunk_text function.
    Delegates to ChunkingStrategy.chunk_text.
    
    Args:
        text: Text to chunk
        max_tokens: Maximum tokens per chunk
        title: Optional title to prepend to chunks
        
    Returns:
        Iterable of text chunks
    """
    # Use the default sentence splitter strategy
    strategy = SentenceSplitterChunkingStrategy()
    return strategy.chunk_text(text, max_tokens, title)


def create_provider_adapter(provider_name, api_key):
    """
    Adapter for the old EmbeddingProviderFactory.create_provider.
    Delegates to the new factory implementation.
    
    Args:
        provider_name: Name of the provider to create
        api_key: API key for the provider
        
    Returns:
        EmbeddingProvider instance
    """
    return EmbeddingProviderFactory.create_provider(provider_name, api_key)


async def safe_db_execute_adapter(url, connection, query, *params):
    """
    Adapter for the old safe_db_execute function.
    Provides safe execution of database queries with error handling.
    
    Args:
        url: URL for context in error messages
        connection: Database connection
        query: SQL query to execute
        params: Query parameters
        
    Returns:
        Query result or None on error
    """
    try:
        return await connection.fetchval(query, *params)
    except Exception as e:
        import logging
        logging.exception(f"Database error for {url}: {type(e).__name__}: {str(e)}")
        return None


# Create adapters for main function to maintain backward compatibility with test_refactoring_4.py
async def main_adapter():
    """
    Adapter for the old main function.
    This is a placeholder to satisfy imports in test_refactoring_4.py.
    The actual implementation delegates to BookProcessingApplication.run_book_processing.
    """
    from create_embeddings.book_processing_orchestrator import BookProcessingApplication
    # This function is only used for import testing in test_refactoring_4.py
    # and will not be called directly
    pass
