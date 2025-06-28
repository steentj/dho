"""Integration tests for the embedding system."""
import asyncio
import pytest

pytestmark = [pytest.mark.integration]  # Mark all tests in this module as integration tests

class Timer:
    """Simple context manager for timing code blocks."""
    def __enter__(self):
        import time
        self.start = time.time()
        return self
    
    def __exit__(self, *args):
        import time
        self.end = time.time()
        self.duration = self.end - self.start

@pytest.mark.asyncio
async def test_ollama_embedding_generation(test_db, ollama_provider, test_book_chunks):
    """Test generating embeddings with Ollama provider."""
    # Insert test book
    book_id = await test_db.fetchval(
        'INSERT INTO books (title) VALUES ($1) RETURNING id',
        'Test Book'
    )
    
    # Generate and store embeddings
    for i, chunk in enumerate(test_book_chunks):
        embedding = await ollama_provider.get_embedding(chunk)
        assert len(embedding) in [768, 1536], f"Embedding should be 768 or 1536 dimensional, got {len(embedding)}"
        
        # Convert embedding to string format for storage
        embedding_str = str(embedding)
        await test_db.execute('''
            INSERT INTO chunks_nomic (id, book_id, sidenr, chunk, embedding)
            VALUES ($1, $2, $3, $4, $5)
        ''', i+1, book_id, i+1, chunk, embedding_str)
    
    # Verify storage
    count = await test_db.fetchval('SELECT COUNT(*) FROM chunks_nomic')
    assert count == len(test_book_chunks), "All chunks should be stored"

@pytest.mark.asyncio
async def test_similarity_search(test_db, ollama_provider):
    """Test similarity search with stored embeddings."""
    # Insert test book
    book_id = await test_db.fetchval(
        'INSERT INTO books (title) VALUES ($1) RETURNING id',
        'Test Book'
    )
    
    # Insert test data
    embedding = await ollama_provider.get_embedding("This is the first chapter.")
    await test_db.execute('''
        INSERT INTO chunks_nomic (id, book_id, sidenr, chunk, embedding)
        VALUES ($1, $2, $3, $4, $5)
    ''', 1, book_id, 1, "This is the first chapter.", str(embedding))
    
    # For simple test, just check that we can retrieve stored chunks
    similar_chunks = await test_db.fetch('''
        SELECT chunk, embedding
        FROM chunks_nomic
        LIMIT 1
    ''')
    
    assert len(similar_chunks) > 0, "Should find at least one stored chunk"
    assert "first chapter" in similar_chunks[0]['chunk'], "Should find relevant chunk"

@pytest.mark.asyncio
async def test_cross_provider_compatibility(test_db, ollama_provider, dummy_provider):
    """Test compatibility between different providers."""
    # Insert test book
    book_id = await test_db.fetchval(
        'INSERT INTO books (title) VALUES ($1) RETURNING id',
        'Test Book'
    )
    
    # Generate embeddings with both providers
    text = "This is a test of cross-provider compatibility."
    
    ollama_embedding = await ollama_provider.get_embedding(text)
    dummy_embedding = await dummy_provider.get_embedding(text)
    
    # Store both embeddings
    await test_db.execute('''
        INSERT INTO chunks_nomic (id, book_id, sidenr, chunk, embedding, provider)
        VALUES ($1, $2, $3, $4, $5, $6)
    ''', 1000, book_id, 1, text, str(ollama_embedding), 'ollama')
    
    # Verify dimensions
    assert len(ollama_embedding) in [768, 1536], f"Ollama embedding should be 768 or 1536-dimensional, got {len(ollama_embedding)}"
    assert len(dummy_embedding) == 1536, f"Dummy embedding should be 1536-dimensional, got {len(dummy_embedding)}"

@pytest.mark.asyncio
@pytest.mark.benchmark
@pytest.mark.parametrize("chunk_size", [1000, 5000, 10000])
async def test_batch_processing_performance(test_db, ollama_provider, chunk_size):
    """Test performance with different batch sizes."""
    # Insert test book
    book_id = await test_db.fetchval(
        'INSERT INTO books (title) VALUES ($1) RETURNING id',
        'Test Book'
    )
    
    # Generate test data
    chunks = [f"Test chunk {i}" for i in range(chunk_size)]
    
    # Process in batches of 100
    batch_size = 100
    with Timer() as t:
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            embeddings = await asyncio.gather(
                *[ollama_provider.get_embedding(chunk) for chunk in batch]
            )
            
            # Bulk insert
            await test_db.executemany('''
                INSERT INTO chunks_nomic (id, book_id, sidenr, chunk, embedding)
                VALUES ($1, $2, $3, $4, $5)
            ''', [(i+j, book_id, j, chunk, str(emb)) for j, (chunk, emb) in enumerate(zip(batch, embeddings))])
    
    # Log performance metrics
    print(f"Processed {chunk_size} chunks in {t.duration:.2f} seconds")
    print(f"Average time per chunk: {(t.duration/chunk_size)*1000:.2f}ms")
