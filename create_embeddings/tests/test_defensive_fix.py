#!/usr/bin/env python3
"""
Test to verify proper type validation in chunking strategies.
This test ensures that chunking strategies always return proper string types.
"""

import pytest
from create_embeddings.chunking import SentenceSplitterChunkingStrategy, WordOverlapChunkingStrategy
from create_embeddings.book_processing_pipeline import BookProcessingPipeline
from create_embeddings.book_service_interface import IBookService


class MockBookService(IBookService):
    """Mock BookService for testing type validation"""
    
    def __init__(self):
        self.saved_books = []
        self.saved_chunks = []
    
    async def save_book_with_chunks(self, book, table_name: str) -> int:
        """Mock save_book_with_chunks that captures the data for inspection"""
        self.saved_books.append(book)
        
        # Extract chunks to verify data types
        for (page_num, chunk_text), embedding in zip(book["chunks"], book["embeddings"]):
            self.saved_chunks.append({
                "page_num": page_num,
                "chunk_text": chunk_text,
                "chunk_text_type": type(chunk_text),
                "embedding": embedding
            })
        
        return 123  # Mock book ID
    
    async def book_exists_with_provider(self, pdf_url: str, provider_name: str) -> bool:
        return False  # For test purposes, assume book doesn't exist


class MockEmbeddingProvider:
    """Mock embedding provider for testing"""
    
    async def get_embedding(self, text: str):
        """Mock get_embedding method"""
        return [0.1] * 768
    
    async def has_embeddings_for_book(self, book_id: int, db_service) -> bool:
        """Mock implementation for abstract method."""
        return False
    
    def get_table_name(self):
        return "chunks_test"
    
    def get_provider_name(self):
        return "test_provider"


async def save_book_with_pipeline(book, book_service, embedding_provider):
    """Helper function that uses the pipeline to save a book"""
    pipeline = BookProcessingPipeline(
        book_service=book_service,
        embedding_provider=embedding_provider,
        chunking_strategy=None  # Not needed for direct save test
    )
    
    # Use the pipeline's internal save method
    await pipeline.save_book_data(book)


class TestChunkingTypeValidation:
    """Test proper type validation in chunking strategies and book processing."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock book service for testing."""
        return MockBookService()

    @pytest.fixture
    def mock_embedding_provider(self):
        """Create a mock embedding provider for testing."""
        return MockEmbeddingProvider()

    @pytest.mark.asyncio
    async def test_normal_string_chunk_text(self, mock_service, mock_embedding_provider):
        """Test that normal string chunk_text works as expected."""
        book = {
            "pdf-url": "test-url",
            "titel": "Test Book",
            "forfatter": "Test Author",
            "sider": 1,
            "chunks": [(1, "Normal string chunk")],  # ✅ Normal case
            "embeddings": [[0.1] * 768]
        }
        
        await save_book_with_pipeline(book, mock_service, mock_embedding_provider)
        
        # Verify the chunk text is passed as string
        assert len(mock_service.saved_chunks) == 1
        chunk = mock_service.saved_chunks[0]
        assert isinstance(chunk["chunk_text"], str)
        assert chunk["chunk_text"] == "Normal string chunk"

    def test_sentence_splitter_type_validation(self):
        """Test that SentenceSplitterChunkingStrategy validates return types."""
        strategy = SentenceSplitterChunkingStrategy()
        pages_text = {1: "This is a test sentence. This is another sentence."}
        
        # This should work fine and return proper strings
        chunks = list(strategy.process_document(pages_text, 1000, "Test Title"))
        
        # Verify all chunks are strings
        for page_num, chunk_text in chunks:
            assert isinstance(chunk_text, str), f"Expected str, got {type(chunk_text)}"
            assert isinstance(page_num, int), f"Expected int page number, got {type(page_num)}"

    def test_word_overlap_type_validation(self):
        """Test that WordOverlapChunkingStrategy validates return types."""
        strategy = WordOverlapChunkingStrategy()
        pages_text = {
            1: "This is the first page with some content that should be chunked properly. " * 50,
            2: "This is the second page with more content for testing. " * 50
        }
        
        # This should work fine and return proper strings
        chunks = list(strategy.process_document(pages_text, 1000, "Test Title"))
        
        # Verify all chunks are strings  
        for page_num, chunk_text in chunks:
            assert isinstance(chunk_text, str), f"Expected str, got {type(chunk_text)}"
            assert isinstance(page_num, int), f"Expected int page number, got {type(page_num)}"

    @pytest.mark.asyncio
    async def test_multiple_normal_chunks(self, mock_service, mock_embedding_provider):
        """Test multiple chunks with proper string types."""
        book = {
            "pdf-url": "test-url-5",
            "titel": "Test Book 5",
            "forfatter": "Test Author",
            "sider": 3,
            "chunks": [
                (1, "First normal string"),  # Normal
                (2, "Second normal string"),  # Normal 
                (3, "Third normal string")  # Normal
            ],
            "embeddings": [[0.1] * 768, [0.2] * 768, [0.3] * 768]
        }
        
        await save_book_with_pipeline(book, mock_service, mock_embedding_provider)
        
        # Check all chunks are properly handled
        assert len(mock_service.saved_chunks) == 3
        
        for i, chunk in enumerate(mock_service.saved_chunks):
            assert isinstance(chunk["chunk_text"], str)
            assert "normal string" in chunk["chunk_text"]

    def test_chunking_strategies_always_return_strings(self):
        """Test that all chunking strategies consistently return strings."""
        test_text = "This is a test document. It has multiple sentences. Each should be handled properly."
        pages_text = {1: test_text}
        
        # Test SentenceSplitterChunkingStrategy
        sentence_strategy = SentenceSplitterChunkingStrategy()
        sentence_chunks = list(sentence_strategy.process_document(pages_text, 50, "Test"))
        
        for page_num, chunk_text in sentence_chunks:
            assert isinstance(chunk_text, str), "SentenceSplitter must return strings"
        
        # Test WordOverlapChunkingStrategy
        word_strategy = WordOverlapChunkingStrategy()  
        word_chunks = list(word_strategy.process_document(pages_text, 50, "Test"))
        
        for page_num, chunk_text in word_chunks:
            assert isinstance(chunk_text, str), "WordOverlap must return strings"


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
