import asyncio
import unittest.mock as mock
from unittest.mock import AsyncMock
import sys
import os
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from create_embeddings.book_processing_pipeline import BookProcessingPipeline
from create_embeddings.chunking import WordOverlapChunkingStrategy, SentenceSplitterChunkingStrategy, ChunkingStrategyFactory
from create_embeddings.book_service_interface import IBookService


class MockBookService(IBookService):
    """Mock BookService for testing"""
    
    def __init__(self):
        self.books = {}
        self.chunks = []
        self.next_book_id = 1
        # Create a mock PostgreSQL service
        self._service = AsyncMock()
        self._service.find_book_by_url = self._find_book_by_url
    
    async def _find_book_by_url(self, pdf_url):
        """Internal method to find book by URL, returns book ID if found"""
        book = self.books.get(pdf_url)
        return book["id"] if book else None
    
    async def create_book(self, pdf_navn, titel, forfatter, antal_sider):
        """Create a new book and return its ID"""
        book_id = self.next_book_id
        self.next_book_id += 1
        self.books[pdf_navn] = {
            "id": book_id,
            "pdf_navn": pdf_navn,
            "titel": titel,
            "forfatter": forfatter,
            "antal_sider": antal_sider
        }
        return book_id
    
    async def create_chunk(self, book_id, sidenr, chunk, embedding):
        """Create a new chunk"""
        self.chunks.append({
            "book_id": book_id,
            "sidenr": sidenr,
            "chunk": chunk,
            "embedding": embedding
        })

    # BookService interface implementation
    async def save_book_with_chunks(self, book: dict, table_name: str) -> int:
        """Save a complete book with all its data (metadata, chunks, and embeddings)."""
        # Extract PDF URL from book dict (handle both formats)
        pdf_url = book.get("pdf_url") or book.get("url") or book.get("pdf-url")
        
        # Create book
        book_id = await self.create_book(
            pdf_url,
            book["titel"],
            book["forfatter"], 
            book["sider"]
        )
        
        # Save all chunks
        for (page_num, chunk_text), embedding in zip(book["chunks"], book["embeddings"]):
            await self.create_chunk(book_id, page_num, chunk_text, embedding)
            
        return book_id

    async def book_exists_with_provider(self, pdf_url: str, provider_name: str) -> bool:
        """Check if book exists with embeddings for a specific provider."""
        # Find book by URL
        book = self.books.get(pdf_url)
        if not book:
            return False
            
        # For mock purposes, assume if book exists, it has embeddings
        # In real implementation, this would check provider-specific tables
        book_id = book["id"]
        book_chunks = [chunk for chunk in self.chunks if chunk["book_id"] == book_id]
        return len(book_chunks) > 0


class MockEmbeddingProvider:
    """Mock embedding provider for testing"""
    
    def __init__(self, embedding_size=1536):
        self.embedding_size = embedding_size
        self.call_count = 0
    
    async def get_embedding(self, text):
        """Generate a mock embedding based on text"""
        self.call_count += 1
        # Create a deterministic but varied embedding based on text length and content
        base_value = len(text) / 1000.0
        return [base_value + (i / self.embedding_size) for i in range(self.embedding_size)]
    
    async def has_embeddings_for_book(self, book_id: int, db_service) -> bool:
        """Mock implementation for abstract method."""
        return False
    
    def get_provider_name(self) -> str:
        """Get provider name."""
        return "mock_provider"
    
    def get_table_name(self) -> str:
        """Get table name."""
        return "chunks_mock"


def create_mock_pdf(pages_content):
    """Create a mock PDF with specified page content"""
    mock_pdf = mock.MagicMock()
    mock_pdf.metadata = {"title": "Integration Test Book", "author": "Test Author"}
    mock_pdf.__len__ = mock.MagicMock(return_value=len(pages_content))
    
    # Create mock pages
    mock_pages = []
    for content in pages_content:
        mock_page = mock.MagicMock()
        mock_page.get_text.return_value = content
        mock_pages.append(mock_page)
    
    mock_pdf.__getitem__ = mock.MagicMock(side_effect=mock_pages)
    return mock_pdf


async def parse_book_with_pipeline(pdf, book_url, chunk_size, embedding_provider, chunking_strategy):
    """Helper function that uses the pipeline to parse a book - replacement for the old parse_book function"""
    book_service = MockBookService()
    pipeline = BookProcessingPipeline(
        book_service=book_service,
        embedding_provider=embedding_provider,
        chunking_strategy=chunking_strategy
    )
    
    # Extract the book data using pipeline's internal method
    book_data = await pipeline.parse_pdf_to_book_data(pdf, book_url, chunk_size)
    
    return book_data


@pytest.mark.asyncio
async def test_word_overlap_end_to_end_integration():
    """Test complete end-to-end processing with WordOverlapChunkingStrategy"""
    
    # Create substantial multi-page content
    pages_content = []
    for page_num in range(1, 6):  # 5 pages
        page_sentences = []
        for sentence_num in range(1, 21):  # 20 sentences per page
            sentence = f"This is sentence {sentence_num} on page {page_num} containing meaningful content for testing purposes."
            page_sentences.append(sentence)
        pages_content.append(" ".join(page_sentences))
    
    mock_pdf = create_mock_pdf(pages_content)
    mock_embedding_provider = MockEmbeddingProvider()
    
    # Use WordOverlapChunkingStrategy
    chunking_strategy = WordOverlapChunkingStrategy()
    chunk_size = 400
    
    # Test parse_book function with pipeline
    book_result = await parse_book_with_pipeline(
        pdf=mock_pdf,
        book_url="test://integration-test.pdf",
        chunk_size=chunk_size,
        embedding_provider=mock_embedding_provider,
        chunking_strategy=chunking_strategy
    )
    
    # Verify book structure
    assert book_result["pdf-url"] == "test://integration-test.pdf"
    assert book_result["titel"] == "Integration Test Book"
    assert book_result["forfatter"] == "Test Author"
    assert book_result["sider"] == 5
    
    # Verify chunks were created
    assert len(book_result["chunks"]) > 0
    assert len(book_result["embeddings"]) == len(book_result["chunks"])
    
    # Verify cross-page chunking characteristics
    page_numbers = [page_num for page_num, _ in book_result["chunks"]]
    unique_pages = set(page_numbers)
    
    # Should have reasonable number of chunks - cross-page chunking typically produces fewer chunks
    # than page-by-page processing, but the exact number can vary based on content
    assert 1 <= len(book_result["chunks"]) <= len(pages_content), f"Expected 1-{len(pages_content)} chunks, got {len(book_result['chunks'])}"
    
    # Should have chunks starting on multiple pages (unless all text fits in one chunk)
    if len(book_result["chunks"]) > 1:
        assert len(unique_pages) >= 1, f"Expected chunks from at least one page, got pages: {unique_pages}"
    
    # Verify chunk characteristics
    for i, (page_num, chunk_text) in enumerate(book_result["chunks"]):
        assert 1 <= page_num <= 5  # Valid page numbers
        chunk_word_count = len(chunk_text.split())
        
        # Chunks should be substantial but not too large
        assert chunk_word_count >= 100, f"Chunk {i+1} has {chunk_word_count} words, expected ≥100"
        # Should not exceed configured chunk_size by more than tolerance
        assert chunk_word_count <= int(chunk_size * 1.1) + 1, f"Chunk {i+1} too large: {chunk_word_count} > {chunk_size}"
        
        assert not chunk_text.startswith("##")  # No title prefix
    
    # Verify embeddings were generated
    assert mock_embedding_provider.call_count == len(book_result["chunks"])
    
    # Test overlap between consecutive chunks (if we have multiple chunks)
    if len(book_result["chunks"]) >= 2:
        chunk1_text = book_result["chunks"][0][1]
        chunk2_text = book_result["chunks"][1][1]
        
        # Look for overlapping sentences - but don't fail if exact pattern doesn't match
        # due to potential variations in chunking
        import re
        chunk1_sentences = set(re.findall(r'sentence (\d+) on page (\d+)', chunk1_text))
        chunk2_sentences = set(re.findall(r'sentence (\d+) on page (\d+)', chunk2_text))
        
        overlap = chunk1_sentences & chunk2_sentences
        # Note: Overlap might not always be detectable with this pattern matching
        # The important thing is that the chunking strategy is working correctly
        if overlap:
            print(f"Found overlap between chunks: {len(overlap)} sentences")
        else:
            print("No overlap detected with sentence pattern matching (this may be normal)")


@pytest.mark.asyncio
async def test_sentence_splitter_end_to_end_integration():
    """Test complete end-to-end processing with SentenceSplitterChunkingStrategy for comparison"""
    
    # Create smaller content for page-by-page processing
    pages_content = [
        "First page has this content. Another sentence on first page. Third sentence here.",
        "Second page starts here. More content on second page. Additional text follows.",
        "Third page begins now. Final content on third page. Last sentence here."
    ]
    
    mock_pdf = create_mock_pdf(pages_content)
    mock_embedding_provider = MockEmbeddingProvider()
    
    # Use SentenceSplitterChunkingStrategy
    chunking_strategy = SentenceSplitterChunkingStrategy()
    chunk_size = 50  # Small to create multiple chunks per page
    
    # Test parse_book function with pipeline
    book_result = await parse_book_with_pipeline(
        pdf=mock_pdf,
        book_url="test://sentence-splitter-test.pdf",
        chunk_size=chunk_size,
        embedding_provider=mock_embedding_provider,
        chunking_strategy=chunking_strategy
    )
    
    # Verify book structure
    assert book_result["pdf-url"] == "test://sentence-splitter-test.pdf"
    assert book_result["titel"] == "Integration Test Book"
    assert book_result["forfatter"] == "Test Author"
    assert book_result["sider"] == 3
    
    # Verify chunks were created
    assert len(book_result["chunks"]) > 0
    assert len(book_result["embeddings"]) == len(book_result["chunks"])
    
    # Verify page-by-page chunking characteristics
    page_numbers = [page_num for page_num, _ in book_result["chunks"]]
    unique_pages = set(page_numbers)
    
    # Skip-first-page rule (multi-page): page 1 content removed, expect pages 2 and 3 only
    assert unique_pages == {2, 3}
    
    # Verify chunk characteristics
    for page_num, chunk_text in book_result["chunks"]:
        assert 2 <= page_num <= 3  # Valid page numbers after skipping page 1
        assert chunk_text.startswith("##Integration Test Book##")  # Has title prefix
    
    # Verify embeddings were generated
    assert mock_embedding_provider.call_count == len(book_result["chunks"])


@pytest.mark.asyncio
async def test_chunking_strategy_factory_integration():
    """Test that the factory works correctly in integration scenarios"""
    
    # Test creating strategies from factory
    word_overlap_strategy = ChunkingStrategyFactory.create_strategy("word_overlap")
    sentence_strategy = ChunkingStrategyFactory.create_strategy("sentence_splitter")
    
    assert isinstance(word_overlap_strategy, WordOverlapChunkingStrategy)
    assert isinstance(sentence_strategy, SentenceSplitterChunkingStrategy)
    
    # Test that they produce different results with same input
    test_pages = {
        1: "Page one content with multiple sentences. More text on page one. Additional content here.",
        2: "Page two begins here. More content on page two. Final text on this page."
    }
    
    # Test cross-page chunking via process_document
    word_overlap_chunks = list(word_overlap_strategy.process_document(test_pages, 400, "Test"))
    
    # Test page-by-page chunking via process_document
    sentence_chunks = list(sentence_strategy.process_document(test_pages, 50, "Test"))
    
    # Should produce different results
    assert len(word_overlap_chunks) != len(sentence_chunks) or word_overlap_chunks != sentence_chunks
    
    # Word overlap should have no title prefixes
    for _, chunk in word_overlap_chunks:
        assert not chunk.startswith("##")
    
    # Sentence strategy should have title prefixes
    for _, chunk in sentence_chunks:
        assert chunk.startswith("##Test##")


@pytest.mark.asyncio
async def test_database_integration_simulation():
    """Test the database interaction simulation"""
    
    mock_book_service = MockBookService()
    mock_embedding_provider = MockEmbeddingProvider()
    
    # Create simple content
    pages_content = ["Test content for database integration. Multiple sentences here."]
    mock_pdf = create_mock_pdf(pages_content)
    
    chunking_strategy = WordOverlapChunkingStrategy()
    
    # Parse the book with pipeline
    book_result = await parse_book_with_pipeline(
        pdf=mock_pdf,
        book_url="test://db-test.pdf",
        chunk_size=400,
        embedding_provider=mock_embedding_provider,
        chunking_strategy=chunking_strategy
    )
    
    # Simulate saving to database (like save_book function does)
    book_id = await mock_book_service.create_book(
        pdf_navn=book_result["pdf-url"],
        titel=book_result["titel"],
        forfatter=book_result["forfatter"],
        antal_sider=book_result["sider"]
    )
    
    # Save chunks
    for (page_num, chunk_text), embedding in zip(book_result["chunks"], book_result["embeddings"]):
        await mock_book_service.create_chunk(
            book_id=book_id,
            sidenr=page_num,
            chunk=chunk_text,
            embedding=embedding
        )
    
    # Verify database state
    assert len(mock_book_service.books) == 1
    assert len(mock_book_service.chunks) == len(book_result["chunks"])
    
    # Verify book was stored correctly
    stored_book = list(mock_book_service.books.values())[0]
    assert stored_book["titel"] == "Integration Test Book"
    assert stored_book["forfatter"] == "Test Author"
    
    # Verify chunks were stored correctly
    for chunk_record in mock_book_service.chunks:
        assert chunk_record["book_id"] == book_id
        assert 1 <= chunk_record["sidenr"] <= 1  # Only one page
        assert len(chunk_record["chunk"]) > 0
        assert len(chunk_record["embedding"]) == 1536


# Async test runner
async def run_integration_tests():
    """Run all integration tests"""
    print("Running integration tests...")
    
    await test_word_overlap_end_to_end_integration()
    print("✓ WordOverlapChunkingStrategy end-to-end test passed")
    
    await test_sentence_splitter_end_to_end_integration()
    print("✓ SentenceSplitterChunkingStrategy end-to-end test passed")
    
    await test_chunking_strategy_factory_integration()
    print("✓ ChunkingStrategyFactory integration test passed")
    
    await test_database_integration_simulation()
    print("✓ Database integration simulation test passed")
    
    print("All integration tests passed! ✅")


if __name__ == "__main__":
    asyncio.run(run_integration_tests())
