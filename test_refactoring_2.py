#!/usr/bin/env python3
"""
Test file to validate Refactoring 2: Strategy Pattern for Text Processing
"""
import asyncio
from unittest.mock import MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'create_embeddings'))

from create_embeddings.chunking import SentenceSplitterChunkingStrategy, WordOverlapChunkingStrategy
from create_embeddings.tests.test_utils import parse_book_adapter as parse_book


class MockEmbeddingProvider:
    def __init__(self):
        self.provider_name = "test_provider"
        self.call_count = 0
        
    async def get_embedding(self, text):
        self.call_count += 1
        # Return a simple embedding (just the length as a float in a list)
        return [float(len(text))]
        
    def get_provider_name(self):
        return self.provider_name


def create_mock_pdf(pages_content):
    """Create a mock PDF object with the given page content"""
    mock_pdf = MagicMock()
    mock_pdf.metadata = {"title": "Test Book", "author": "Test Author"}
    mock_pdf.__len__ = MagicMock(return_value=len(pages_content))
    mock_pdf.close = MagicMock()
    
    # Mock the extract_text_by_page function
    def extract_text_by_page(pdf):
        return {i+1: content for i, content in enumerate(pages_content)}
    
    # Patch the extract_text_by_page function in BookProcessingPipeline
    import create_embeddings.book_processing_pipeline
    create_embeddings.book_processing_pipeline.BookProcessingPipeline._extract_text_by_page = lambda self, pdf: extract_text_by_page(pdf)
    
    return mock_pdf


async def test_sentence_splitter_processing():
    """Test that SentenceSplitterChunkingStrategy uses page-by-page processing"""
    print("Testing SentenceSplitterChunkingStrategy...")
    
    pages_content = [
        "First page with multiple sentences. This is sentence two. And sentence three.",
        "Second page starts here. More content follows. Final sentence on page two.",
        "Third page begins. Content continues. End of page three."
    ]
    
    mock_pdf = create_mock_pdf(pages_content)
    mock_embedding_provider = MockEmbeddingProvider()
    chunking_strategy = SentenceSplitterChunkingStrategy()
    
    result = await parse_book(
        pdf=mock_pdf,
        book_url="test://sentence-test.pdf",
        chunk_size=50,
        embedding_provider=mock_embedding_provider,
        chunking_strategy=chunking_strategy
    )
    
    print(f"✓ SentenceSplitter processed {len(result['chunks'])} chunks")
    print(f"✓ Generated {len(result['embeddings'])} embeddings")
    assert len(result['chunks']) == len(result['embeddings'])
    
    # Check that chunks have page numbers from all pages
    page_numbers = {page_num for page_num, _ in result['chunks']}
    print(f"✓ Chunks span pages: {sorted(page_numbers)}")
    assert len(page_numbers) == 3  # Should have chunks from all 3 pages
    
    # Verify title prefixes (SentenceSplitterChunkingStrategy behavior)
    for page_num, chunk_text in result['chunks']:
        assert chunk_text.startswith("##Test Book##"), f"Missing title prefix in chunk: {chunk_text[:50]}"
    
    print("✓ SentenceSplitterChunkingStrategy test passed!\n")
    return True


async def test_word_overlap_processing():
    """Test that WordOverlapChunkingStrategy uses cross-page processing"""
    print("Testing WordOverlapChunkingStrategy...")
    
    pages_content = [
        "First page with substantial content that should span across multiple chunks when processed. " * 10,
        "Second page continues the narrative with even more content to ensure cross-page processing. " * 10,
        "Third page completes our test document with final substantial content for verification. " * 10
    ]
    
    mock_pdf = create_mock_pdf(pages_content)
    mock_embedding_provider = MockEmbeddingProvider()
    chunking_strategy = WordOverlapChunkingStrategy()
    
    result = await parse_book(
        pdf=mock_pdf,
        book_url="test://word-overlap-test.pdf", 
        chunk_size=400,
        embedding_provider=mock_embedding_provider,
        chunking_strategy=chunking_strategy
    )
    
    print(f"✓ WordOverlap processed {len(result['chunks'])} chunks")
    print(f"✓ Generated {len(result['embeddings'])} embeddings")
    assert len(result['chunks']) == len(result['embeddings'])
    
    # Check that chunks have reasonable page numbers  
    page_numbers = [page_num for page_num, _ in result['chunks']]
    print(f"✓ Chunks start on pages: {page_numbers}")
    assert all(1 <= p <= 3 for p in page_numbers), "Invalid page numbers"
    
    # WordOverlapChunkingStrategy doesn't add title prefixes
    for page_num, chunk_text in result['chunks']:
        assert not chunk_text.startswith("##"), f"Unexpected title prefix in chunk: {chunk_text[:50]}"
    
    print("✓ WordOverlapChunkingStrategy test passed!\n")
    return True


async def test_strategy_polymorphism():
    """Test that both strategies work polymorphically through the same interface"""
    print("Testing strategy polymorphism...")
    
    pages_content = ["Test content for polymorphism verification."]
    
    strategies = [
        ("SentenceSplitter", SentenceSplitterChunkingStrategy()),
        ("WordOverlap", WordOverlapChunkingStrategy())
    ]
    
    for name, strategy in strategies:
        mock_embedding_provider = MockEmbeddingProvider()
        
        result = await parse_book(
            pdf=create_mock_pdf(pages_content),  # Create fresh mock each time
            book_url=f"test://{name.lower()}-polymorphism.pdf",
            chunk_size=50,
            embedding_provider=mock_embedding_provider,
            chunking_strategy=strategy
        )
        
        print(f"✓ {name} strategy produced {len(result['chunks'])} chunks")
        assert len(result['chunks']) > 0
        assert len(result['chunks']) == len(result['embeddings'])
    
    print("✓ Polymorphism test passed!\n")
    return True


async def main():
    """Run all refactoring validation tests"""
    print("=" * 60)
    print("REFACTORING 2 VALIDATION: Strategy Pattern for Text Processing")
    print("=" * 60)
    print()
    
    try:
        success = True
        success &= await test_sentence_splitter_processing()
        success &= await test_word_overlap_processing() 
        success &= await test_strategy_polymorphism()
        
        if success:
            print("🎉 ALL REFACTORING 2 TESTS PASSED!")
            print("\nRefactoring Summary:")
            print("✓ Removed _process_cross_page_chunking() helper function")
            print("✓ Removed _find_starting_page() helper function")  
            print("✓ Added process_document() method to ChunkingStrategy interface")
            print("✓ Implemented process_document() in both strategy classes")
            print("✓ Updated parse_book() to use new strategy interface")
            print("✓ Eliminated chunking strategy dispatch logic from parse_book()")
            print("✓ Moved page processing responsibility to strategies")
        else:
            print("❌ SOME TESTS FAILED!")
            return False
            
    except Exception as e:
        print(f"❌ TEST FAILED WITH ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    return True


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)
