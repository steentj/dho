#!/usr/bin/env python3
"""
Test PostgreSQLService directly with vector data types - reproducing the exact production issue.
This simulates the case where book_service is PostgreSQLService (not BookService).
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


async def test_postgresql_service_vector_insertion():
    """Test direct PostgreSQLService usage with vector data."""
    print("🧪 Testing PostgreSQLService vector insertion (exact production scenario)")
    
    try:
        # Initialize the PostgreSQL service directly (like production might)
        print("1️⃣ Creating PostgreSQLService directly...")
        database_url = "postgresql://steen:pgDHOai@postgres:5432/WW2"
        service = PostgreSQLService(database_url=database_url)
        
        # Check if this service has save_chunks method
        print(f"✓ service has save_chunks: {hasattr(service, 'save_chunks')}")
        print(f"✓ service has _service: {hasattr(service, '_service')}")
        
        # Connect to database
        print("2️⃣ Connecting to database...")
        await service.connect()
        
        # Create test chunks with embeddings (simulate Ollama output)
        print("3️⃣ Creating test vector data...")
        
        # Simulate what Ollama returns - Python list of floats
        test_embedding = [0.1] * 768  # 768-dimensional vector as Python list
        
        chunks_with_embeddings = [
            (1, "Test chunk one", test_embedding),
            (2, "Test chunk two", test_embedding),
            (3, "Test chunk three", test_embedding)
        ]
        
        print(f"   Embedding type: {type(test_embedding)}")
        print(f"   Embedding length: {len(test_embedding)}")
        print(f"   First element type: {type(test_embedding[0])}")
        
        # Test save_chunks directly (this is what line 127 in opret_bøger.py does)
        print("4️⃣ Testing save_chunks directly on PostgreSQLService...")
        print("   This should reproduce the production error!")
        
        book_id = 818  # Test book ID (created above)
        await service.save_chunks(book_id, chunks_with_embeddings, "chunks_nomic")
        
        print("✅ SUCCESS: Vector insertion completed without errors!")
        
    except Exception as e:
        print(f"❌ PRODUCTION ERROR REPRODUCED: {type(e).__name__}: {e}")
        import traceback
        print("Full traceback:")
        traceback.print_exc()
        return False
    
    finally:
        try:
            await service.disconnect()
        except Exception:
            pass
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_postgresql_service_vector_insertion())
    if success:
        print("\n🎉 Test completed successfully!")
    else:
        print("\n💥 Test reproduced the production error!")
