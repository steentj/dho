#!/usr/bin/env python3
"""
Simple debug test for the integration issue
"""

import asyncio
import sys
import os

# Ensure we can import from the current directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from opret_bøger import parse_book, _process_cross_page_chunking
from chunking import WordOverlapChunkingStrategy
import unittest.mock as mock


class MockEmbeddingProvider:
    def __init__(self, embedding_size=1536):
        self.embedding_size = embedding_size
        self.call_count = 0
    
    async def get_embedding(self, text):
        self.call_count += 1
        base_value = len(text) / 1000.0
        return [base_value + (i / self.embedding_size) for i in range(self.embedding_size)]


def create_mock_pdf(pages_content):
    mock_pdf = mock.MagicMock()
    mock_pdf.metadata = {"title": "Integration Test Book", "author": "Test Author"}
    mock_pdf.__len__ = mock.MagicMock(return_value=len(pages_content))
    
    mock_pages = []
    for content in pages_content:
        mock_page = mock.MagicMock()
        mock_page.get_text.return_value = content
        mock_pages.append(mock_page)
    
    mock_pdf.__getitem__ = mock.MagicMock(side_effect=mock_pages)
    mock_pdf.close = mock.MagicMock()  # Add close method
    return mock_pdf


async def debug_test():
    print("=== DEBUG INTEGRATION TEST ===")
    
    # Create test data
    pages_content = []
    for page_num in range(1, 6):  # 5 pages
        page_sentences = []
        for sentence_num in range(1, 21):  # 20 sentences per page
            sentence = f"This is sentence {sentence_num} on page {page_num} containing meaningful content for testing purposes."
            page_sentences.append(sentence)
        pages_content.append(" ".join(page_sentences))
    
    print(f"Created {len(pages_content)} pages")
    for i, page in enumerate(pages_content):
        print(f"  Page {i+1}: {len(page.split())} words")
    
    # Test direct cross-page chunking
    pdf_pages = {i+1: page for i, page in enumerate(pages_content)}
    strategy = WordOverlapChunkingStrategy()
    
    print("\n=== DIRECT CROSS-PAGE CHUNKING TEST ===")
    cross_page_chunks = _process_cross_page_chunking(pdf_pages, 400, strategy, "Test Book")
    print(f"Direct cross-page chunking produced {len(cross_page_chunks)} chunks:")
    for i, (page_num, chunk) in enumerate(cross_page_chunks):
        print(f"  Chunk {i+1}: Page {page_num}, {len(chunk.split())} words")
    
    # Test full parse_book function
    print("\n=== FULL PARSE_BOOK TEST ===")
    mock_pdf = create_mock_pdf(pages_content)
    mock_embedding_provider = MockEmbeddingProvider()
    
    try:
        book_result = await parse_book(
            pdf=mock_pdf,
            book_url="test://integration-test.pdf",
            chunk_size=400,
            embedding_provider=mock_embedding_provider,
            chunking_strategy=strategy
        )
        
        print(f"parse_book produced {len(book_result['chunks'])} chunks:")
        for i, (page_num, chunk) in enumerate(book_result["chunks"]):
            print(f"  Chunk {i+1}: Page {page_num}, {len(chunk.split())} words")
        
        print(f"Embeddings generated: {len(book_result['embeddings'])}")
        print(f"Embedding provider called {mock_embedding_provider.call_count} times")
        
        return len(book_result['chunks']) == 4  # Expected number of chunks
        
    except Exception as e:
        print(f"ERROR in parse_book: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(debug_test())
    print(f"\nTest result: {'PASS' if result else 'FAIL'}")
    sys.exit(0 if result else 1)
