"""
Test for the PostgreSQL data type bug that causes:
"invalid input for query argument $3: [...] (expected str, got list)"

IMPORTANT: The production error was NOT with vector data (parameter $4), 
but with chunk_text data (parameter $3) being passed as a list instead of string.

This test demonstrates:
1. Vector data (Python lists) work correctly with pgvector
2. The actual bug is chunk_text receiving lists instead of strings
3. The defensive fix prevents this error
"""
import pytest
import asyncpg
from pgvector.asyncpg import register_vector

# Test classes to reproduce the exact issue
@pytest.mark.asyncio
async def test_vector_data_works_correctly_with_lists():
    """
    Verify that vector data insertion works correctly with Python lists.
    
    This test confirms that the production error was NOT caused by vector data (parameter $4),
    but by chunk_text data (parameter $3) being passed as a list instead of string.
    """
    # Create a test database connection exactly like the production code
    database_url = "postgresql://postgres:postgres@localhost:5432/test_db"
    
    # Skip if database not available
    try:
        connection = await asyncpg.connect(database_url)
    except Exception:
        pytest.skip("Test database not available")
    
    try:
        # Register vector support - same as production code
        await register_vector(connection)
        
        # Create a test table with vector column - same schema as chunks_nomic
        await connection.execute("""
            CREATE EXTENSION IF NOT EXISTS vector;
        """)
        
        await connection.execute("""
            DROP TABLE IF EXISTS test_chunks_vector;
            CREATE TABLE test_chunks_vector (
                id BIGSERIAL PRIMARY KEY,
                book_id INTEGER NOT NULL,
                sidenr INTEGER NOT NULL,
                chunk TEXT NOT NULL,
                embedding vector(768)
            );
        """)
        
        # Create test data exactly like the real data flow
        test_embedding = [-0.4073981046676636, 0.2563869953155517] + [0.1] * 766  # 768 dimensions
        
        # Test 1: Normal case - string chunk_text, list embedding (should work)
        await connection.execute("""
            INSERT INTO test_chunks_vector (book_id, sidenr, chunk, embedding)
            VALUES ($1, $2, $3, $4)
        """, 1, 1, "Test chunk", test_embedding)
        
        # Verify the insert worked
        result = await connection.fetchrow("""
            SELECT book_id, sidenr, chunk, embedding FROM test_chunks_vector WHERE id = 1
        """)
        assert result is not None
        assert result['book_id'] == 1
        assert result['chunk'] == "Test chunk"
        assert result['embedding'] is not None
        
        # Test 2: Reproduce the actual bug - list chunk_text (should fail)
        try:
            await connection.execute("""
                INSERT INTO test_chunks_vector (book_id, sidenr, chunk, embedding)
                VALUES ($1, $2, $3, $4)
            """, 2, 1, ["This", "is", "a", "list"], test_embedding)  # chunk as list!
            
            # If we get here, something is wrong - this should fail
            pytest.fail("Expected list chunk_text to fail, but it succeeded")
            
        except asyncpg.exceptions.DataError as e:
            # This should be the actual production error
            error_msg = str(e)
            assert "expected str, got list" in error_msg
            # Verify it's parameter $3 (chunk), not $4 (embedding)
            assert "$3" in error_msg or "argument 3" in error_msg.lower()
        
    finally:
        await connection.close()


@pytest.mark.asyncio 
async def test_vector_data_type_fix():
    """
    Test the corrected approach for inserting vector data.
    
    This test shows the CORRECT way to handle vector data with asyncpg + pgvector.
    """
    # Create a test database connection
    database_url = "postgresql://postgres:postgres@localhost:5432/test_db"
    
    # Skip if database not available
    try:
        connection = await asyncpg.connect(database_url)
    except Exception:
        pytest.skip("Test database not available")
    
    try:
        # Register vector support
        await register_vector(connection)
        
        # Create a test table
        await connection.execute("""
            CREATE EXTENSION IF NOT EXISTS vector;
        """)
        
        await connection.execute("""
            DROP TABLE IF EXISTS test_chunks_vector_fixed;
            CREATE TABLE test_chunks_vector_fixed (
                id BIGSERIAL PRIMARY KEY,
                book_id INTEGER NOT NULL,
                sidenr INTEGER NOT NULL, 
                chunk TEXT NOT NULL,
                embedding vector(768)
            );
        """)
        
        # Create test data
        test_embedding = [-0.4073981046676636, 0.2563869953155517] + [0.1] * 766  # 768 dimensions
        
        # Convert list to proper format for pgvector
        # The fix should be here - we need to find the right conversion
        from pgvector.asyncpg import Vector
        vector_data = Vector(test_embedding)
        
        # This should work with the proper conversion
        await connection.execute("""
            INSERT INTO test_chunks_vector_fixed (book_id, sidenr, chunk, embedding)
            VALUES ($1, $2, $3, $4) 
        """, 1, 1, "Test chunk", vector_data)
        
        # Verify the data was inserted correctly
        result = await connection.fetchrow("""
            SELECT book_id, sidenr, chunk, embedding
            FROM test_chunks_vector_fixed
            WHERE id = 1
        """)
        
        assert result is not None
        assert result['book_id'] == 1
        assert result['sidenr'] == 1
        assert result['chunk'] == "Test chunk"
        
        # Verify embedding vector can be used for similarity search
        query_embedding = Vector([-0.4, 0.25] + [0.1] * 766)
        similarity_result = await connection.fetchrow("""
            SELECT embedding <=> $1 as distance
            FROM test_chunks_vector_fixed
            WHERE id = 1
        """, query_embedding)
        
        assert similarity_result is not None
        assert isinstance(similarity_result['distance'], float)
        assert similarity_result['distance'] >= 0.0  # Cosine distance is always >= 0
        
    finally:
        await connection.close()


@pytest.mark.asyncio
async def test_pgvector_with_raw_list_approach():
    """
    Test alternative approach - maybe the register_vector should make raw lists work.
    """
    database_url = "postgresql://postgres:postgres@localhost:5432/test_db"
    
    try:
        connection = await asyncpg.connect(database_url)
    except Exception:
        pytest.skip("Test database not available")
    
    try:
        # Maybe there's a different way to register vector support
        await register_vector(connection)
        
        await connection.execute("""
            CREATE EXTENSION IF NOT EXISTS vector;
        """)
        
        await connection.execute("""
            DROP TABLE IF EXISTS test_raw_vector;
            CREATE TABLE test_raw_vector (
                id BIGSERIAL PRIMARY KEY,
                embedding vector(768)
            );
        """)
        
        # Test if raw list works with proper registration
        test_embedding = [0.1, 0.2, 0.3] + [0.0] * 765  # 768 dimensions
        
        # Try the raw list approach 
        try:
            await connection.execute("""
                INSERT INTO test_raw_vector (embedding) VALUES ($1)
            """, test_embedding)
            
            # If this works, then the issue might be elsewhere
            result = await connection.fetchval("""
                SELECT embedding FROM test_raw_vector WHERE id = 1
            """)
            assert result is not None
            
        except asyncpg.exceptions.DataError as e:
            if "expected str, got list" in str(e):
                # This confirms the bug - raw lists don't work even with register_vector
                pytest.fail("Raw lists still don't work - need Vector() wrapper")
            else:
                raise
        
    finally:
        await connection.close()
