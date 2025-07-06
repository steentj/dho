"""
Test using the exact same service setup as production to reproduce the bug.
"""
import asyncio
import sys

# Add parent path for imports
sys.path.append('/app')

async def test_with_exact_service_setup():
    """Test using the exact same service setup as the production main() function"""
    
    # Import exactly what production imports
    from database import BookService, PostgreSQLService
    from create_embeddings.providers import OllamaEmbeddingProvider
    from dotenv import load_dotenv
    import os
    
    # Load environment exactly like production
    load_dotenv(override=True)
    
    # Get database URL exactly like production
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        # Build URL exactly like production would
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        database = os.getenv("POSTGRES_DB")
        user = os.getenv("POSTGRES_USER")
        password = os.getenv("POSTGRES_PASSWORD")
        database_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    print(f"Using database URL: {database_url}")
    
    # Initialize services exactly like production
    db_service = PostgreSQLService(database_url)
    book_service = BookService(db_service)
    embedding_provider = OllamaEmbeddingProvider()
    
    print("✓ Created services exactly like production")
    print(f"  book_service type: {type(book_service)}")
    print(f"  db_service type: {type(db_service)}")
    print(f"  embedding_provider type: {type(embedding_provider)}")
    
    try:
        # Connect exactly like production
        await db_service.connect()
        print("✓ Connected to database")
        
        # Check that we have the exact service structure expected by production
        print(f"✓ book_service._service exists: {hasattr(book_service, '_service')}")
        print(f"✓ book_service has save_chunks: {hasattr(book_service, 'save_chunks')}")
        
        if hasattr(book_service, '_service'):
            print(f"✓ book_service._service type: {type(book_service._service)}")
            print(f"✓ book_service._service has save_chunks: {hasattr(book_service._service, 'save_chunks')}")
        
        # Create test book exactly like production
        book_id = await book_service.get_or_create_book(
            "test_exact_service.pdf",
            "Test Exact Service", 
            "Test Author",
            1
        )
        print(f"✓ Created test book with ID: {book_id}")
        
        # Get embedding exactly like production
        test_chunk = "Test chunk for exact service replication"
        embedding = await embedding_provider.get_embedding(test_chunk)
        
        print("✓ Got embedding from Ollama")
        print(f"  Type: {type(embedding)}")
        print(f"  Length: {len(embedding)}")
        print(f"  Sample values: {embedding[:3]}")
        
        # Call the exact same code path that production uses
        # Based on opret_bøger.py line 127, this should call book_service.save_chunks()
        table_name = embedding_provider.get_table_name()
        chunks_with_embeddings = [(1, test_chunk, embedding)]
        
        print(f"✓ Calling save_chunks with table: {table_name}")
        print(f"  chunks_with_embeddings structure: {[(type(x[0]), type(x[1]), type(x[2])) for x in chunks_with_embeddings]}")
        
        # This is the exact call that fails in production
        await book_service.save_chunks(book_id, chunks_with_embeddings, table_name)
        
        print("✅ SUCCESS: save_chunks completed successfully!")
        
        # Verify the data was saved
        result = await db_service.fetchrow(
            f"SELECT embedding FROM {table_name} WHERE book_id = $1", 
            book_id
        )
        print(f"✓ Verified stored data type: {type(result['embedding'])}")
        
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        
        if "expected str, got list" in str(e):
            print("🎯 REPRODUCED THE PRODUCTION BUG!")
            
            # Let's analyze the exact embedding data
            print("\n🔍 Analyzing embedding data:")
            print(f"  Type: {type(embedding)}")
            print(f"  Repr: {repr(embedding)}")
            print(f"  Is instance of list: {isinstance(embedding, list)}")
            
            if hasattr(embedding, '__class__'):
                print(f"  Class: {embedding.__class__}")
                print(f"  Module: {embedding.__class__.__module__}")
                
            # Check if it's a special list subclass or numpy array
            try:
                import numpy as np
                print(f"  Is numpy array: {isinstance(embedding, np.ndarray)}")
            except ImportError:
                print("  Numpy not available")
            
            # Try to understand why asyncpg sees it as needing str conversion
            print(f"  Dir: {[x for x in dir(embedding) if not x.startswith('_')]}")
            
            import traceback
            traceback.print_exc()
        else:
            print(f"Different error: {e}")
            import traceback
            traceback.print_exc()
        
    finally:
        # Clean up exactly like production
        try:
            if 'book_id' in locals():
                await db_service.execute(f"DELETE FROM {table_name} WHERE book_id = $1", book_id)
                await db_service.execute("DELETE FROM books WHERE id = $1", book_id)
                print("✓ Cleaned up test data")
        except Exception:
            pass
        
        await db_service.disconnect()
        print("✓ Disconnected from database")

if __name__ == "__main__":
    asyncio.run(test_with_exact_service_setup())
