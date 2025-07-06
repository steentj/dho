#!/usr/bin/env python3
"""
Test with REAL Ollama embeddings to reproduce the vector data type issue.
This tests the actual Ollama integration that might be causing the production error.
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


async def test_real_ollama_embeddings():
    """Test with real Ollama embeddings to find the production issue."""
    print("🧪 Testing REAL Ollama embeddings (reproducing production issue)")
    
    try:
        # Initialize service 
        print("1️⃣ Creating PostgreSQLService...")
        database_url = "postgresql://steen:pgDHOai@postgres:5432/WW2"
        service = PostgreSQLService(database_url=database_url)
        
        await service.connect()
        print("✅ Connected to database")
        
        # Test different text inputs that might cause issues
        test_texts = [
            "Simple test text",
            "Text with special characters: æøå, émañá, 中文",
            "Very long text that might cause issues: " + "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 10,
            "Text with numbers: 123, 456.789, -99.5",
            "Text with punctuation!!! ???... ((()))",
            "",  # Empty string
            "Single word",
            "Multiple\nlines\nof\ntext\nwith\nbreaks",
        ]
        
        print("2️⃣ Testing various text inputs with real Ollama...")
        
        for i, text in enumerate(test_texts, 1):
            print(f"\n--- Test {i}: {repr(text[:50])}{'...' if len(text) > 50 else ''} ---")
            
            try:
                # Get real embedding from Ollama
                print("   Calling Ollama for embedding...")
                
                # Use the same method as the production code
                import aiohttp
                
                async with aiohttp.ClientSession() as session:
                    payload = {
                        "model": "nomic-embed-text:latest",
                        "prompt": text
                    }
                    
                    async with session.post(
                        "http://dho-ollama:11434/api/embeddings",
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            embedding = result.get("embedding", [])
                        else:
                            print(f"   ❌ Ollama error: {response.status}")
                            continue
                
                print(f"   Embedding type: {type(embedding)}")
                print(f"   Embedding length: {len(embedding) if embedding else 'None'}")
                
                if embedding:
                    print(f"   First element type: {type(embedding[0])}")
                    print(f"   First few values: {embedding[:3]}")
                    
                    # Test the problematic line - vector insertion
                    chunks_with_embeddings = [(i, text, embedding)]
                    
                    print("   🔥 Testing vector insertion...")
                    await service.save_chunks(818, chunks_with_embeddings, "chunks_nomic")
                    print("   ✅ Vector insertion successful!")
                    
                else:
                    print("   ⚠️  Empty embedding returned")
                    
            except Exception as e:
                print(f"   💥 ERROR with this text: {type(e).__name__}: {e}")
                # Don't stop - continue with other texts
                import traceback
                print("   Full traceback:")
                traceback.print_exc()
                print()
        
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
    success = asyncio.run(test_real_ollama_embeddings())
    if success:
        print("\n✅ Testing completed - check results above!")
    else:
        print("\n💥 Critical error occurred!")
