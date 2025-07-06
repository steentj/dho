"""
Test the exact data flow from Ollama provider to database to reproduce the bug.
This replicates the exact path: Ollama -> parse_book -> save_book -> postgresql.py
"""
import asyncio
import sys

# Add parent path for imports
sys.path.append('/app')

async def test_exact_production_flow():
    """Test the exact production data flow that causes the error"""
    
    # Import the actual production classes
    from create_embeddings.providers import OllamaEmbeddingProvider
    from database.postgresql import PostgreSQLDatabaseFactory
    
    # Database connection using the exact same setup as production
    factory = PostgreSQLDatabaseFactory()
    connection = await factory.create_connection()
    book_repository = factory.create_book_repository(connection)
    
    print("✓ Connected using production database factory")
    
    # Create Ollama provider with exact same setup
    ollama_provider = OllamaEmbeddingProvider()
    print(f"✓ Created Ollama provider: {ollama_provider.base_url}, model: {ollama_provider.model}")
    
    try:
        # Create a test book
        book_id = await book_repository.create_book(
            "test_production_flow.pdf", 
            "Test Production Flow", 
            "Test Author", 
            1
        )
        print(f"✓ Created test book with ID: {book_id}")
        
        # Get embedding using actual Ollama provider - this is the exact production path
        test_chunk = "This is a test chunk to reproduce the production bug."
        print(f"Getting embedding for: '{test_chunk}'")
        
        embedding = await ollama_provider.get_embedding(test_chunk)
        print("✓ Got embedding from Ollama")
        print(f"  Type: {type(embedding)}")
        print(f"  Length: {len(embedding) if hasattr(embedding, '__len__') else 'N/A'}")
        print(f"  First 5 values: {embedding[:5] if hasattr(embedding, '__getitem__') else embedding}")
        
        # Check if it's wrapped in any special type
        import json
        print(f"  JSON serializable: {json.dumps(embedding[:3]) if hasattr(embedding, '__getitem__') else 'No'}")
        
        # Now try to save using the exact production code path
        chunks_with_embeddings = [(1, test_chunk, embedding)]
        table_name = ollama_provider.get_table_name()  # Should be "chunks_nomic"
        
        print(f"✓ Using table: {table_name}")
        print(f"✓ Chunks data structure: {type(chunks_with_embeddings)}")
        print(f"✓ Embedding in structure type: {type(chunks_with_embeddings[0][2])}")
        
        # This is the exact line that fails in production
        await book_repository.save_chunks(book_id, chunks_with_embeddings, table_name)
        
        print("✅ SUCCESS: save_chunks completed without error!")
        
        # Verify data was saved correctly
        # Using the raw connection to check what was actually stored
        raw_connection = connection._connection  # Access the underlying asyncpg connection
        result = await raw_connection.fetchrow("""
            SELECT embedding FROM chunks_nomic WHERE book_id = $1
        """, book_id)
        
        print(f"✓ Verified stored embedding type: {type(result['embedding'])}")
        print(f"✓ Verified stored embedding length: {len(result['embedding'])}")
        
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        
        # Check if this is the exact production error
        if "expected str, got list" in str(e):
            print("🎯 REPRODUCED THE PRODUCTION BUG!")
            
            # Let's examine the exact data that caused the problem
            print(f"Problem data type: {type(embedding)}")
            print(f"Problem data repr: {repr(embedding[:10])}")
            
            # Try different fixes
            print("\n🔧 Trying different fixes...")
            
            # Fix 1: Convert to plain Python list
            try:
                if hasattr(embedding, 'tolist'):
                    list_embedding = embedding.tolist()
                else:
                    list_embedding = list(embedding)
                
                print(f"Fix 1 - Plain list conversion: {type(list_embedding)}")
                
                chunks_with_embeddings_fix1 = [(1, test_chunk, list_embedding)]
                await book_repository.save_chunks(book_id, chunks_with_embeddings_fix1, table_name)
                print("✅ Fix 1 WORKED: Plain list conversion")
                
            except Exception as fix1_error:
                print(f"❌ Fix 1 failed: {fix1_error}")
            
            # Fix 2: Use pgvector Vector wrapper
            try:
                from pgvector.asyncpg import Vector
                vector_embedding = Vector(embedding)
                print(f"Fix 2 - Vector wrapper: {type(vector_embedding)}")
                
                chunks_with_embeddings_fix2 = [(2, test_chunk, vector_embedding)]
                await book_repository.save_chunks(book_id, chunks_with_embeddings_fix2, table_name)
                print("✅ Fix 2 WORKED: Vector wrapper")
                
            except Exception as fix2_error:
                print(f"❌ Fix 2 failed: {fix2_error}")
        else:
            print(f"Different error than expected: {e}")
            import traceback
            traceback.print_exc()
        
    finally:
        # Clean up
        try:
            if 'book_id' in locals():
                await connection.execute("DELETE FROM chunks_nomic WHERE book_id = $1", book_id)
                await connection.execute("DELETE FROM books WHERE id = $1", book_id)
                print("✓ Cleaned up test data")
        except Exception:
            pass
        
        await connection.close()
        print("✓ Connection closed")

if __name__ == "__main__":
    asyncio.run(test_exact_production_flow())
