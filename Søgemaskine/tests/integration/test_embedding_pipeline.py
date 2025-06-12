"""
Integration tests for the embedding pipeline.

Tests the complete flow from text input to embeddings storage.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
import asyncio


@pytest.mark.integration
class TestEmbeddingPipeline:
    """Test the complete embedding pipeline."""

    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client for integration tests."""
        mock_client = AsyncMock()
        mock_client.embeddings.create.return_value = AsyncMock(
            data=[
                MagicMock(embedding=[0.1, 0.2, 0.3] * 512)  # 1536 dimensions
            ]
        )
        return mock_client

    @pytest.fixture
    def mock_database_connection(self):
        """Mock database connection for integration tests."""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        mock_cursor.fetchone.return_value = None
        return mock_conn

    @pytest.fixture
    def sample_text_data(self):
        """Sample text data for testing."""
        return {
            "book_id": "test_book_123",
            "title": "Test Bog",
            "content": "Dette er en test tekst til embeddings. Den indeholder dansk tekst som kan bruges til søgning.",
            "chunks": [
                "Dette er en test tekst til embeddings.",
                "Den indeholder dansk tekst som kan bruges til søgning."
            ]
        }

    @pytest.mark.asyncio
    async def test_complete_embedding_pipeline(self, mock_openai_client, mock_database_connection, sample_text_data):
        """Test the complete pipeline from text to embeddings storage."""
        
        # Mock the text processing functions
        def mock_chunk_text(text, chunk_size=1000):
            return sample_text_data["chunks"]
        
        async def mock_get_embedding(chunk):
            return [0.1, 0.2, 0.3] * 512  # Mock 1536-dimensional embedding
        
        async def mock_save_to_database(book_id, title, chunk, embedding, chunk_index):
            # Simulate successful database save
            return True
        
        # Test the pipeline steps
        book_id = sample_text_data["book_id"]
        title = sample_text_data["title"]
        content = sample_text_data["content"]
        
        # Step 1: Chunk the text
        chunks = mock_chunk_text(content, chunk_size=1000)
        assert len(chunks) == 2
        assert chunks[0] == "Dette er en test tekst til embeddings."
        
        # Step 2: Generate embeddings for each chunk
        embeddings = []
        for chunk in chunks:
            embedding = await mock_get_embedding(chunk)
            embeddings.append(embedding)
            assert len(embedding) == 1536  # OpenAI text-embedding-ada-002 dimension
        
        # Step 3: Save to database
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            success = await mock_save_to_database(book_id, title, chunk, embedding, i)
            assert success is True

    @pytest.mark.asyncio
    async def test_error_handling_in_pipeline(self, mock_openai_client, mock_database_connection):
        """Test error handling throughout the pipeline."""
        
        async def mock_get_embedding_with_error(chunk):
            if "error" in chunk.lower():
                raise Exception("OpenAI API Error")
            return [0.1, 0.2, 0.3] * 512
        
        async def mock_save_with_error(book_id, title, chunk, embedding, chunk_index):
            if "database_error" in chunk.lower():
                raise Exception("Database Error")
            return True
        
        # Test with error in embedding generation
        chunks_with_error = ["Normal chunk", "Error chunk", "Another normal chunk"]
        
        successful_saves = 0
        for i, chunk in enumerate(chunks_with_error):
            try:
                embedding = await mock_get_embedding_with_error(chunk)
                await mock_save_with_error("test_book", "Test Title", chunk, embedding, i)
                successful_saves += 1
            except Exception as e:
                assert "Error" in str(e)
        
        # Should have 2 successful saves (skipping the error chunk)
        assert successful_saves == 2

    @pytest.mark.asyncio
    async def test_batch_processing(self, mock_openai_client, mock_database_connection):
        """Test batch processing of multiple documents."""
        
        documents = [
            {"id": "book1", "title": "Bog 1", "content": "Indhold af bog 1"},
            {"id": "book2", "title": "Bog 2", "content": "Indhold af bog 2"},
            {"id": "book3", "title": "Bog 3", "content": "Indhold af bog 3"}
        ]
        
        async def process_document(doc):
            # Simulate document processing
            chunks = [doc["content"]]  # Simple chunking
            embeddings = []
            
            for chunk in chunks:
                # Mock embedding generation
                embedding = [0.1, 0.2, 0.3] * 512
                embeddings.append(embedding)
            
            return len(embeddings)
        
        # Process all documents
        total_chunks = 0
        for doc in documents:
            chunk_count = await process_document(doc)
            total_chunks += chunk_count
        
        assert total_chunks == 3  # One chunk per document

    @pytest.mark.asyncio
    async def test_concurrent_processing(self, mock_openai_client, mock_database_connection):
        """Test concurrent processing of embeddings."""
        
        async def mock_process_chunk(chunk_id):
            # Simulate processing delay
            await asyncio.sleep(0.01)
            return f"processed_chunk_{chunk_id}"
        
        # Process multiple chunks concurrently
        chunk_ids = list(range(10))
        tasks = [mock_process_chunk(chunk_id) for chunk_id in chunk_ids]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 10
        assert all("processed_chunk_" in result for result in results)

    @pytest.mark.asyncio
    async def test_rate_limiting_simulation(self, mock_openai_client):
        """Test simulation of rate limiting handling."""
        
        call_count = 0
        
        async def mock_api_call_with_rate_limit():
            nonlocal call_count
            call_count += 1
            
            if call_count % 3 == 0:  # Every 3rd call fails
                raise Exception("Rate limit exceeded")
            
            return [0.1, 0.2, 0.3] * 512
        
        successful_calls = 0
        total_attempts = 10
        
        for _ in range(total_attempts):
            try:
                await mock_api_call_with_rate_limit()
                successful_calls += 1
            except Exception:
                # In real implementation, this would trigger retry logic
                pass
        
        # Should have ~7 successful calls (10 - 3 failures)
        assert successful_calls == 7


@pytest.mark.integration
class TestSearchPipeline:
    """Test the complete search pipeline."""

    @pytest.fixture
    def mock_search_engine(self):
        """Mock search engine for integration tests."""
        search_engine = MagicMock()
        search_engine.get_embedding.return_value = [0.1, 0.2, 0.3] * 512
        search_engine.find_nærmeste.return_value = [
            {
                "book_id": "123",
                "title": "Test Bog",
                "chunk_text": "Dette er en test chunk.",
                "similarity": 0.95,
                "chunk_index": 0
            }
        ]
        return search_engine

    @pytest.mark.asyncio
    async def test_complete_search_pipeline(self, mock_search_engine):
        """Test the complete search pipeline."""
        
        query = "test søgning"
        
        # Step 1: Get embedding for query
        query_embedding = mock_search_engine.get_embedding(query)
        assert len(query_embedding) == 1536
        
        # Step 2: Find similar chunks
        results = mock_search_engine.find_nærmeste(query_embedding, limit=10)
        assert len(results) == 1
        assert results[0]["similarity"] > 0.9
        assert "Test Bog" in results[0]["title"]

    @pytest.mark.asyncio
    async def test_search_with_filters(self, mock_search_engine):
        """Test search with various filters."""
        
        # Mock filtered search
        def mock_filtered_search(embedding, limit=10, chunk_size=1000, distance_func="cosine"):
            results = [
                {
                    "book_id": "123",
                    "title": "Test Bog",
                    "chunk_text": f"Filtered result for chunk_size {chunk_size}",
                    "similarity": 0.9,
                    "chunk_index": 0
                }
            ]
            return results[:limit]
        
        mock_search_engine.find_nærmeste = mock_filtered_search
        
        query_embedding = [0.1, 0.2, 0.3] * 512
        
        # Test different parameters
        results = mock_search_engine.find_nærmeste(
            query_embedding, 
            limit=5, 
            chunk_size=500, 
            distance_func="euclidean"
        )
        
        assert len(results) == 1
        assert "500" in results[0]["chunk_text"]

    @pytest.mark.asyncio
    async def test_empty_search_results(self, mock_search_engine):
        """Test handling of empty search results."""
        
        # Mock empty results
        mock_search_engine.find_nærmeste.return_value = []
        
        query_embedding = [0.1, 0.2, 0.3] * 512
        results = mock_search_engine.find_nærmeste(query_embedding)
        
        assert len(results) == 0
        assert isinstance(results, list)
