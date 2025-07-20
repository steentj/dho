"""
Tests for Book Processing Pipeline.

Creation date/time: 20. juli 2025, 14:45
Last Modified date/time: 20. juli 2025, 14:45
"""

import pytest
from unittest.mock import Mock, patch

from create_embeddings.book_processing_pipeline import BookProcessingPipeline
from create_embeddings.book_service_interface import IBookService
from create_embeddings.providers import EmbeddingProvider
from create_embeddings.chunking import ChunkingStrategy


class MockBookService(IBookService):
    """Mock book service for testing."""
    
    def __init__(self):
        self.saved_books = []
        self.existing_books = {}
    
    async def save_book_with_chunks(self, book, table_name: str) -> int:
        self.saved_books.append((book, table_name))
        return 1
    
    async def book_exists_with_provider(self, pdf_url: str, provider_name: str) -> bool:
        return self.existing_books.get((pdf_url, provider_name), False)


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock embedding provider for testing."""
    
    def __init__(self, provider_name="test"):
        self.provider_name = provider_name
        self.call_count = 0
    
    async def get_embedding(self, text: str):
        self.call_count += 1
        return [0.1, 0.2, 0.3]
    
    async def has_embeddings_for_book(self, book_id: int, db_service) -> bool:
        """Mock implementation for abstract method."""
        return False
    
    def get_provider_name(self) -> str:
        return self.provider_name
    
    def get_table_name(self) -> str:
        return f"chunks_{self.provider_name}"


class MockChunkingStrategy(ChunkingStrategy):
    """Mock chunking strategy for testing."""
    
    def chunk_text(self, text: str, max_tokens: int, title: str = None):
        # Simple chunking for tests
        words = text.split()
        for i in range(0, len(words), max_tokens):
            yield " ".join(words[i:i + max_tokens])
    
    def supports_cross_page_chunking(self) -> bool:
        return False
    
    def process_document(self, pages_text, chunk_size: int, title: str):
        # Simple mock implementation
        for page_num, page_text in pages_text.items():
            for chunk in self.chunk_text(page_text, chunk_size, title):
                yield (page_num, chunk)


@pytest.mark.asyncio
async def test_pipeline_initialization():
    """Test pipeline can be initialized with dependencies."""
    book_service = MockBookService()
    embedding_provider = MockEmbeddingProvider()
    chunking_strategy = MockChunkingStrategy()
    
    pipeline = BookProcessingPipeline(
        book_service=book_service,
        embedding_provider=embedding_provider,
        chunking_strategy=chunking_strategy
    )
    
    assert pipeline.book_service is book_service
    assert pipeline.embedding_provider is embedding_provider
    assert pipeline.chunking_strategy is chunking_strategy


@pytest.mark.asyncio
async def test_pipeline_skips_existing_book():
    """Test pipeline skips book that already exists with embeddings."""
    book_service = MockBookService()
    embedding_provider = MockEmbeddingProvider()
    chunking_strategy = MockChunkingStrategy()
    
    # Set up existing book
    book_service.existing_books[("http://example.com/test.pdf", "test")] = True
    
    pipeline = BookProcessingPipeline(
        book_service=book_service,
        embedding_provider=embedding_provider,
        chunking_strategy=chunking_strategy
    )
    
    mock_session = Mock()
    
    await pipeline.process_book_from_url(
        "http://example.com/test.pdf",
        100,
        mock_session
    )
    
    # Should not have saved anything
    assert len(book_service.saved_books) == 0
    # Should not have called embedding provider
    assert embedding_provider.call_count == 0


@pytest.mark.asyncio
async def test_pipeline_processes_new_book():
    """Test pipeline processes new book through complete workflow."""
    book_service = MockBookService()
    embedding_provider = MockEmbeddingProvider()
    chunking_strategy = MockChunkingStrategy()
    
    pipeline = BookProcessingPipeline(
        book_service=book_service,
        embedding_provider=embedding_provider,
        chunking_strategy=chunking_strategy
    )
    
    # Mock PDF document
    mock_pdf = Mock()
    mock_pdf.metadata = {"title": "Test Book", "author": "Test Author"}
    mock_pdf.__len__ = Mock(return_value=2)
    mock_pdf.__getitem__ = Mock()
    mock_pdf.close = Mock()
    
    # Mock page text extraction
    page1_mock = Mock()
    page1_mock.get_text.return_value = "This is page one text."
    page2_mock = Mock()
    page2_mock.get_text.return_value = "This is page two text."
    
    mock_pdf.__getitem__.side_effect = [page1_mock, page2_mock]
    
    # Mock session and fetch
    mock_session = Mock()
    
    with patch.object(pipeline, '_fetch_pdf', return_value=mock_pdf):
        await pipeline.process_book_from_url(
            "http://example.com/test.pdf",
            10,
            mock_session
        )
    
    # Should have saved one book
    assert len(book_service.saved_books) == 1
    
    saved_book, table_name = book_service.saved_books[0]
    assert saved_book["pdf-url"] == "http://example.com/test.pdf"
    assert saved_book["titel"] == "Test Book"
    assert saved_book["forfatter"] == "Test Author"
    assert saved_book["sider"] == 2
    assert table_name == "chunks_test"
    
    # Should have generated embeddings
    assert embedding_provider.call_count > 0
    
    # Should have closed PDF
    mock_pdf.close.assert_called_once()


@pytest.mark.asyncio
async def test_pipeline_handles_fetch_failure():
    """Test pipeline handles PDF fetch failure gracefully."""
    book_service = MockBookService()
    embedding_provider = MockEmbeddingProvider()
    chunking_strategy = MockChunkingStrategy()
    
    pipeline = BookProcessingPipeline(
        book_service=book_service,
        embedding_provider=embedding_provider,
        chunking_strategy=chunking_strategy
    )
    
    mock_session = Mock()
    
    with patch.object(pipeline, '_fetch_pdf', return_value=None):
        # Should not raise exception
        await pipeline.process_book_from_url(
            "http://example.com/invalid.pdf",
            100,
            mock_session
        )
    
    # Should not have saved anything
    assert len(book_service.saved_books) == 0
    # Should not have called embedding provider
    assert embedding_provider.call_count == 0


@pytest.mark.asyncio
async def test_pipeline_defensive_chunk_text_fix():
    """Test pipeline applies defensive fix for chunk_text data types."""
    book_service = MockBookService()
    embedding_provider = MockEmbeddingProvider()
    
    # Mock strategy that returns list instead of string (triggering defensive fix)
    chunking_strategy = Mock()
    chunking_strategy.process_document.return_value = [
        (1, ["word1", "word2", "word3"]),  # Invalid: list instead of string
        (2, "valid string chunk")  # Valid: string
    ]
    
    pipeline = BookProcessingPipeline(
        book_service=book_service,
        embedding_provider=embedding_provider,
        chunking_strategy=chunking_strategy
    )
    
    # Mock PDF
    mock_pdf = Mock()
    mock_pdf.metadata = {"title": "Test"}
    mock_pdf.__len__ = Mock(return_value=2)
    mock_pdf.close = Mock()
    
    mock_session = Mock()
    
    with patch.object(pipeline, '_fetch_pdf', return_value=mock_pdf):
        with patch.object(pipeline, '_extract_text_by_page', return_value={1: "text1", 2: "text2"}):
            await pipeline.process_book_from_url(
                "http://example.com/test.pdf",
                10,
                mock_session
            )
    
    # Should have saved one book
    assert len(book_service.saved_books) == 1
    
    saved_book, _ = book_service.saved_books[0]
    
    # Check that chunk text was fixed
    assert saved_book["chunks"][0] == (1, "word1 word2 word3")  # List converted to string
    assert saved_book["chunks"][1] == (2, "valid string chunk")  # String left as-is


@pytest.mark.asyncio 
async def test_pipeline_processes_exception_handling():
    """Test pipeline properly propagates exceptions for error tracking."""
    book_service = MockBookService()
    embedding_provider = MockEmbeddingProvider()
    chunking_strategy = MockChunkingStrategy()
    
    pipeline = BookProcessingPipeline(
        book_service=book_service,
        embedding_provider=embedding_provider,
        chunking_strategy=chunking_strategy
    )
    
    mock_session = Mock()
    
    # Mock _fetch_pdf to raise exception
    with patch.object(pipeline, '_fetch_pdf', side_effect=Exception("Network error")):
        with pytest.raises(Exception) as exc_info:
            await pipeline.process_book_from_url(
                "http://example.com/test.pdf",
                100,
                mock_session
            )
        
        assert "Network error" in str(exc_info.value)
