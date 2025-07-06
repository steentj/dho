"""
Test the vector data type issue inside the actual Docker environment.
This script will be run inside the book-processor container to test the exact same environment.
"""
import asyncio
import os
import asyncpg
from pgvector.asyncpg import register_vector

async def test_vector_in_docker():
    """Test vector data types in the actual Docker environment"""
    
    # Use the same connection parameters as the actual application
    database_url = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@postgres:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB')}"
    
    print(f"Connecting to: {database_url}")
    
    try:
        connection = await asyncpg.connect(database_url)
        print("✓ Connected to database")
        
        # Register vector support - same as production code
        await register_vector(connection)
        print("✓ Registered vector support")
        
        # Test if the chunks_nomic table exists
        table_exists = await connection.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'chunks_nomic'
            );
        """)
        print(f"✓ chunks_nomic table exists: {table_exists}")
        
        if not table_exists:
            print("Creating chunks_nomic table...")
            await connection.execute("""
                CREATE TABLE chunks_nomic (
                    id BIGSERIAL PRIMARY KEY,
                    book_id INTEGER NOT NULL,
                    sidenr INTEGER NOT NULL,
                    chunk TEXT NOT NULL,
                    embedding vector(768)
                );
            """)
            print("✓ Created chunks_nomic table")
        
        # Test embedding data exactly like production
        test_embedding = [-0.4073981046676636, 0.2563869953155517] + [0.1] * 766  # 768 dimensions
        print(f"✓ Test embedding length: {len(test_embedding)}")
        print(f"✓ Test embedding type: {type(test_embedding)}")
        print(f"✓ First few values: {test_embedding[:5]}")
        
        # Create a test book first (required for foreign key)
        book_id = await connection.fetchval("""
            INSERT INTO books (pdf_navn, titel, forfatter, antal_sider)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        """, "test_book_vector.pdf", "Test Book", "Test Author", 1)
        print(f"✓ Created test book with ID: {book_id}")
        
        # Try the exact same INSERT that fails in production
        try:
            print("Attempting INSERT with raw Python list...")
            await connection.execute("""
                INSERT INTO chunks_nomic (book_id, sidenr, chunk, embedding)
                VALUES ($1, $2, $3, $4)
            """, book_id, 1, "Test chunk from Docker", test_embedding)
            
            print("✅ INSERT with raw list SUCCEEDED!")
            
            # Check what was inserted
            result = await connection.fetchrow("""
                SELECT embedding FROM chunks_nomic WHERE book_id = $1
            """, book_id)
            print(f"✓ Retrieved embedding type: {type(result['embedding'])}")
            print(f"✓ Retrieved embedding length: {len(result['embedding'])}")
            
        except Exception as e:
            print(f"❌ INSERT with raw list FAILED: {type(e).__name__}: {e}")
            
            if "expected str, got list" in str(e):
                print("🎯 Reproduced the exact production error!")
                
                # Try the fix with Vector wrapper
                try:
                    from pgvector.asyncpg import Vector
                    vector_data = Vector(test_embedding)
                    print(f"✓ Created Vector wrapper: {type(vector_data)}")
                    
                    await connection.execute("""
                        INSERT INTO chunks_nomic (book_id, sidenr, chunk, embedding)
                        VALUES ($1, $2, $3, $4)
                    """, book_id, 2, "Test chunk with Vector wrapper", vector_data)
                    
                    print("✅ INSERT with Vector wrapper SUCCEEDED!")
                    
                except Exception as fix_error:
                    print(f"❌ Vector wrapper also failed: {type(fix_error).__name__}: {fix_error}")
            else:
                print(f"Different error than expected: {e}")
        
        # Clean up test data
        if 'book_id' in locals():
            await connection.execute("DELETE FROM chunks_nomic WHERE book_id = $1", book_id)
            await connection.execute("DELETE FROM books WHERE id = $1", book_id)
            print("✓ Cleaned up test data")
        
    except Exception as e:
        print(f"❌ Connection or setup failed: {type(e).__name__}: {e}")
        
    finally:
        if 'connection' in locals():
            await connection.close()
            print("✓ Connection closed")

if __name__ == "__main__":
    asyncio.run(test_vector_in_docker())
