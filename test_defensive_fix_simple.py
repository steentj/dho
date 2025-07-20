#!/usr/bin/env python3
"""
Test script to verify the defensive fix for chunk_text data type issues.
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from create_embeddings.opret_bøger import save_book
from create_embeddings.book_service_interface import BookService


class TestBookService(BookService):
    """Test BookService for verifying defensive fix"""
    
    def __init__(self):
        self.captured_chunks = []
    
    async def save_book_with_chunks(self, book, table_name: str) -> int:
        """Capture the chunks for inspection"""
        for (page_num, chunk_text), embedding in zip(book["chunks"], book["embeddings"]):
            self.captured_chunks.append({
                "page_num": page_num,
                "chunk_text": chunk_text,
                "chunk_text_type": type(chunk_text).__name__
            })
        return 123
    
    async def book_exists_with_provider(self, pdf_url: str, provider_name: str) -> bool:
        return False


class TestEmbeddingProvider:
    """Test embedding provider"""
    
    def get_table_name(self):
        return "test_chunks"
    
    def get_provider_name(self):
        return "test"


async def test_defensive_fix():
    """Test that defensive fix converts data types correctly"""
    
    service = TestBookService()
    provider = TestEmbeddingProvider()
    
    # Test book with mixed chunk text types
    test_book = {
        "pdf-url": "test.pdf",
        "titel": "Test Book",
        "forfatter": "Test Author", 
        "sider": 3,
        "chunks": [
            (1, "Normal string"),  # Normal
            (2, ["List", "of", "words"]),  # List (should be converted)
            (3, 12345)  # Integer (should be converted)
        ],
        "embeddings": [[0.1] * 10, [0.2] * 10, [0.3] * 10]
    }
    
    # Run save_book function
    await save_book(test_book, service, provider)
    
    # Check results
    print("Defensive fix test results:")
    for i, chunk in enumerate(service.captured_chunks):
        print(f"Chunk {i+1}: {chunk['chunk_text']} (type: {chunk['chunk_text_type']})")
        
    # Verify all chunk texts are strings
    all_strings = all(chunk['chunk_text_type'] == 'str' for chunk in service.captured_chunks)
    
    if all_strings:
        print("✅ SUCCESS: All chunk texts are strings after defensive fix")
        
        # Verify specific conversions
        chunk2_text = service.captured_chunks[1]['chunk_text']
        chunk3_text = service.captured_chunks[2]['chunk_text']
        
        if chunk2_text == "List of words":
            print("✅ List conversion works correctly")
        else:
            print(f"❌ List conversion failed: got '{chunk2_text}'")
            
        if chunk3_text == "12345":
            print("✅ Integer conversion works correctly")
        else:
            print(f"❌ Integer conversion failed: got '{chunk3_text}'")
            
    else:
        print("❌ FAILURE: Some chunk texts are not strings")
        for chunk in service.captured_chunks:
            if chunk['chunk_text_type'] != 'str':
                print(f"  - Chunk {chunk['page_num']}: {chunk['chunk_text']} is {chunk['chunk_text_type']}")


if __name__ == "__main__":
    asyncio.run(test_defensive_fix())
