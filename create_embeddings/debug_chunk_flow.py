#!/usr/bin/env python3
"""
Debug the exact data flow to find where chunk_text becomes a list instead of string.
"""

import asyncio
import sys
import os
from create_embeddings.opret_bøger import parse_book
from create_embeddings.chunking import ChunkingStrategyFactory

# Add the project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import after path setup
sys.path.insert(0, "/app")


async def debug_chunk_data_types():
    """Debug data types throughout the book processing flow."""
    print("🔍 Debugging chunk data types throughout the flow...")
    
    try:
        # Create a minimal test case
        print("1️⃣ Creating test data...")
        
        # Mock PDF object
        class MockPDF:
            def __init__(self):
                self.metadata = {"title": "Test Book", "author": "Test Author"}
                self._pages = ["Page 1 content. More text here.", "Page 2 content. Additional text."]
            
            def __len__(self):
                return len(self._pages)
            
            def __getitem__(self, page_num):
                class MockPage:
                    def __init__(self, text):
                        self.text = text
                    def get_text(self):
                        return self.text
                return MockPage(self._pages[page_num])
            
            def close(self):
                pass
        
        # Mock embedding provider
        class MockEmbeddingProvider:
            async def get_embedding(self, text):
                print(f"    📊 get_embedding called with: {type(text)} = {repr(text[:50])}{'...' if len(text) > 50 else ''}")
                return [0.1] * 768  # Mock embedding
        
        pdf = MockPDF()
        embedding_provider = MockEmbeddingProvider()
        
        # Test different chunking strategies
        strategies = ["sentence_splitter", "word_overlap"]
        
        for strategy_name in strategies:
            print(f"\n2️⃣ Testing strategy: {strategy_name}")
            
            chunking_strategy = ChunkingStrategyFactory.create_strategy(strategy_name)
            
            # Debug the chunking strategy output first
            print("   📝 Testing chunking strategy directly...")
            test_text = "First sentence here. Second sentence follows."
            chunks = list(chunking_strategy.chunk_text(test_text, 50, "Test Title"))
            for i, chunk in enumerate(chunks):
                print(f"      Chunk {i}: {type(chunk)} = {repr(chunk)}")
            
            # Test the full parse_book flow
            print("   📚 Testing full parse_book flow...")
            book_result = await parse_book(
                pdf=pdf,
                book_url="test-url",
                chunk_size=50,
                embedding_provider=embedding_provider,
                chunking_strategy=chunking_strategy
            )
            
            print(f"   📊 Result chunks type: {type(book_result['chunks'])}")
            print(f"   📊 Number of chunks: {len(book_result['chunks'])}")
            
            for i, chunk_data in enumerate(book_result["chunks"]):
                print(f"      Chunk {i}: {type(chunk_data)} = {chunk_data}")
                if isinstance(chunk_data, (list, tuple)) and len(chunk_data) >= 2:
                    page_num, chunk_text = chunk_data[0], chunk_data[1]
                    print(f"         page_num: {type(page_num)} = {page_num}")
                    print(f"         chunk_text: {type(chunk_text)} = {repr(chunk_text)}")
                    
                    # This is the problematic line - check if chunk_text is a list
                    if isinstance(chunk_text, list):
                        print(f"         🔥 FOUND THE BUG! chunk_text is a list: {chunk_text}")
                        print(f"         🔥 List contents: {[type(x) for x in chunk_text]}")
        
        print("\n🎉 Debugging completed!")
        
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(debug_chunk_data_types())
    if success:
        print("\n✅ Debug completed - check results above!")
    else:
        print("\n💥 Debug failed!")
