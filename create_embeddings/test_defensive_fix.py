#!/usr/bin/env python3
"""
Test the defensive fix for chunk_text data type issues.
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


async def test_defensive_fix():
    """Test the defensive fix for chunk_text data type issues."""
    print("🛡️ Testing defensive fix for chunk_text data type...")
    
    try:
        # Initialize service 
        print("1️⃣ Creating PostgreSQLService...")
        database_url = "postgresql://steen:pgDHOai@postgres:5432/WW2"
        service = PostgreSQLService(database_url=database_url)
        
        await service.connect()
        print("✅ Connected to database")
        
        # Test embedding
        test_embedding = [0.1] * 768
        
        # Test cases that would trigger the defensive fix
        test_cases = [
            {
                "name": "Normal string chunk_text",
                "book": {
                    "pdf-url": "test-url",
                    "titel": "Test Book",
                    "forfatter": "Test Author", 
                    "sider": 1,
                    "chunks": [(1, "Normal string chunk")],  # ✅ Normal case
                    "embeddings": [test_embedding]
                }
            },
            {
                "name": "List chunk_text (BUG CASE)",
                "book": {
                    "pdf-url": "test-url-2",
                    "titel": "Test Book 2",
                    "forfatter": "Test Author",
                    "sider": 1,
                    "chunks": [(1, ["This", "is", "a", "list"])],  # 🔥 Bug case!
                    "embeddings": [test_embedding]
                }
            },
            {
                "name": "Integer chunk_text (edge case)",
                "book": {
                    "pdf-url": "test-url-3",
                    "titel": "Test Book 3", 
                    "forfatter": "Test Author",
                    "sider": 1,
                    "chunks": [(1, 12345)],  # Edge case
                    "embeddings": [test_embedding]
                }
            }
        ]
        
        print("2️⃣ Testing different chunk_text data types...")
        
        for test_case in test_cases:
            print(f"\n--- Testing: {test_case['name']} ---")
            book = test_case["book"]
            
            try:
                # Import the fixed function
                from create_embeddings.opret_bøger import _save_book_with_repository
                
                # Test the defensive fix
                await _save_book_with_repository(book, service, "chunks_nomic")
                
                print(f"   ✅ SUCCESS: {test_case['name']} handled correctly!")
                
            except Exception as e:
                print(f"   💥 ERROR: {type(e).__name__}: {e}")
                if "expected str, got" in str(e):
                    print("   🔥 DEFENSIVE FIX FAILED - error still occurs!")
                else:
                    print("   ❓ Different error (might be expected)")
        
        print("\n🎉 Defensive fix testing completed!")
        
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
    success = asyncio.run(test_defensive_fix())
    if success:
        print("\n✅ Testing completed - check results above!")
    else:
        print("\n💥 Testing failed!")
