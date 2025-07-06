#!/usr/bin/env python3
"""
Test chunk_text data types - reproducing the "expected str, got list" error.
This investigates if chunk_text is incorrectly passed as a list instead of string.
"""

import asyncio
import sys
import os
from database.postgresql_service import PostgreSQLService

# Add the project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import after path setup
sys.path.insert(0, "/app")


async def test_chunk_text_data_types():
    """Test different chunk_text data types to reproduce the error."""
    print("🧪 Testing chunk_text data types (finding the 'expected str, got list' error)")
    
    try:
        # Initialize service 
        print("1️⃣ Creating PostgreSQLService...")
        database_url = "postgresql://steen:pgDHOai@postgres:5432/WW2"
        service = PostgreSQLService(database_url=database_url)
        
        await service.connect()
        print("✅ Connected to database")
        
        # Test embedding (this we know works)
        test_embedding = [0.1] * 768
        
        # Test different chunk_text types that might cause the issue
        test_cases = [
            ("Valid string", "This is a normal string chunk"),
            ("List instead of string", ["This", "is", "a", "list"]),  # This should cause error!
            ("Tuple instead of string", ("This", "is", "a", "tuple")),  # This might cause error!
            ("Number instead of string", 12345),  # This might cause error!
            ("None instead of string", None),  # This might cause error!
            ("Empty string", ""),
            ("Unicode string", "Special chars: æøå, émañá, 中文"),
        ]
        
        print("2️⃣ Testing different chunk_text data types...")
        
        for case_name, chunk_text in test_cases:
            print(f"\n--- Testing: {case_name} ---")
            print(f"   chunk_text type: {type(chunk_text)}")
            print(f"   chunk_text value: {repr(chunk_text)}")
            
            try:
                # Create chunks_with_embeddings with potentially problematic data
                chunks_with_embeddings = [(1, chunk_text, test_embedding)]
                
                print("   🔥 Testing vector insertion...")
                await service.save_chunks(818, chunks_with_embeddings, "chunks_nomic")
                print("   ✅ SUCCESS: Insertion worked!")
                
            except Exception as e:
                print(f"   💥 ERROR REPRODUCED: {type(e).__name__}: {e}")
                if "expected str, got list" in str(e):
                    print("   🎯 FOUND THE PRODUCTION ERROR!")
                elif "expected str, got" in str(e):
                    print("   🎯 FOUND SIMILAR ERROR PATTERN!")
                # Continue with next test case
        
        print("\n🎉 All tests completed!")
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        try:
            await service.disconnect()
        except Exception:
            pass
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_chunk_text_data_types())
    if success:
        print("\n✅ Testing completed - check results above!")
    else:
        print("\n💥 Critical error occurred!")
