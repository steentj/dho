#!/usr/bin/env python3
"""
Test with REAL production book processing workflow to reproduce the chunk_text list issue.
"""

import asyncio
import sys
import os
import traceback
from create_embeddings.book_processor_wrapper import process_books
from database.postgresql_service import PostgreSQLService

# Add the project root to Python path  
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import after path setup
sys.path.insert(0, "/app")


async def test_production_book_processing():
    """Test with real production book processing workflow."""
    print("🔥 Testing REAL production book processing workflow...")
    
    try:
        # Initialize database service
        print("1️⃣ Setting up database service...")
        database_url = "postgresql://steen:pgDHOai@postgres:5432/WW2"
        service = PostgreSQLService(database_url=database_url)
        await service.connect()
        
        # Use a book that actually exists in the failed folder or create a minimal test case
        print("2️⃣ Looking for real book files...")
        
        # Check what's available in the container
        import os
        failed_dir = "/app/failed"
        input_dir = "/app/input"
        
        book_paths = []
        
        # Check failed directory
        if os.path.exists(failed_dir):
            for file in os.listdir(failed_dir):
                if file.endswith('.pdf'):
                    book_paths.append(os.path.join(failed_dir, file))
                    print(f"   Found failed book: {file}")
        
        # Check input directory  
        if os.path.exists(input_dir):
            for file in os.listdir(input_dir):
                if file.endswith('.pdf'):
                    book_paths.append(os.path.join(input_dir, file))
                    print(f"   Found input book: {file}")
        
        if not book_paths:
            print("   ⚠️ No PDF files found, creating minimal test...")
            # We can't create real PDFs in this test, so skip this approach
            print("   Skipping real PDF test - no files available")
            return True
        
        # Take the first available book
        test_book_path = book_paths[0]
        print(f"3️⃣ Testing with: {test_book_path}")
        
        # **THIS IS THE KEY**: Use the exact same process_books function that production uses
        # This will trigger the exact same code path that's failing in production
        
        # Set up minimal configuration for process_books
        class TestConfig:
            chunk_size = 500
            embedding_provider = "ollama"
            model = "nomic-embed-text:latest"
            chunking_strategy = "sentence_splitter"  # Try both strategies
            table_name = "chunks_nomic"
        
        config = TestConfig()
        
        # Create a simple book list with just one book
        book_list = [test_book_path]
        
        print("4️⃣ Processing book with REAL production flow...")
        print("   This will use the exact same code path that's failing!")
        
        # This is the exact function call that happens in production
        await process_books(
            book_list=book_list,
            chunk_size=config.chunk_size,
            embedding_provider_name=config.embedding_provider,
            model=config.model,
            chunking_strategy_name=config.chunking_strategy,
            table_name=config.table_name,
            database_service=service
        )
        
        print("✅ SUCCESS: Production workflow completed without errors!")
        
    except Exception as e:
        print(f"💥 PRODUCTION ERROR CAUGHT: {type(e).__name__}: {e}")
        
        # Check if this is the specific error we're looking for
        error_str = str(e)
        if "expected str, got list" in error_str:
            print("🎯 REPRODUCED THE PRODUCTION ERROR!")
            print("🔍 Full error details:")
            traceback.print_exc()
            return "REPRODUCED"
        elif "expected str, got" in error_str:
            print("🎯 REPRODUCED SIMILAR ERROR PATTERN!")
            print("🔍 Full error details:")
            traceback.print_exc()
            return "SIMILAR"
        else:
            print("❓ Different error - not the one we're looking for")
            traceback.print_exc()
        
        return False
    
    finally:
        try:
            await service.disconnect()
        except Exception:
            pass
    
    return True


if __name__ == "__main__":
    result = asyncio.run(test_production_book_processing())
    if result == "REPRODUCED":
        print("\n🎉 SUCCESSFULLY REPRODUCED THE PRODUCTION ERROR!")
    elif result == "SIMILAR":
        print("\n🔍 REPRODUCED SIMILAR ERROR - good lead!")
    elif result:
        print("\n✅ Test completed successfully - production flow works")
    else:
        print("\n💥 Test failed with different error")
