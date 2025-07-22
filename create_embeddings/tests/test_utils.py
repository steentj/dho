"""
Test utilities for create_embeddings package tests.

This module provides shared test utilities for transitioning from the
standalone extract_text_by_page function to the BookProcessingPipeline._extract_text_by_page method.

Creation date/time: 22. juli 2025, 10:30
Last Modified date/time: 22. juli 2025, 10:30
"""

from typing import Dict, Any
from unittest.mock import MagicMock

from create_embeddings.book_processing_pipeline import BookProcessingPipeline


def extract_text_by_page_adapter(pdf) -> Dict[int, str]:
    """
    Adapter function that provides the same interface as the old extract_text_by_page
    but delegates to BookProcessingPipeline._extract_text_by_page.
    
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
    return pipeline._extract_text_by_page(pdf)


async def parse_book_adapter(pdf, book_url, chunk_size, embedding_provider, chunking_strategy) -> Dict[str, Any]:
    """
    Adapter function that provides the same interface as the old parse_book function
    but delegates to BookProcessingPipeline._parse_pdf_to_book_data.
    
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
    return await pipeline._parse_pdf_to_book_data(pdf, book_url, chunk_size)
