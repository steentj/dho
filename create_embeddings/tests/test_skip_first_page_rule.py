import unittest.mock as mock
import pytest

from create_embeddings.book_processing_pipeline import BookProcessingPipeline
from create_embeddings.chunking import SentenceSplitterChunkingStrategy, WordOverlapChunkingStrategy
from create_embeddings.book_service_interface import IBookService


class DummyBookService(IBookService):
    async def save_book_with_chunks(self, book, table_name: str) -> int:  # pragma: no cover - trivial
        return 1

    async def book_exists_with_provider(self, pdf_url: str, provider_name: str) -> bool:  # pragma: no cover - trivial
        return False


class DummyEmbeddingProvider:
    def __init__(self):
        self.calls = 0

    async def get_embedding(self, text: str):
        self.calls += 1
        return [0.0] * 16  # small dimension for speed

    async def has_embeddings_for_book(self, book_id: int, db_service) -> bool:  # pragma: no cover
        return False

    def get_provider_name(self) -> str:  # pragma: no cover - simple
        return "dummy"

    def get_table_name(self) -> str:  # pragma: no cover - simple
        return "chunks_dummy"


async def _run_pipeline(mock_pdf, strategy):
    provider = DummyEmbeddingProvider()
    service = DummyBookService()
    pipeline = BookProcessingPipeline(service, provider, strategy)
    return await pipeline.parse_pdf_to_book_data(mock_pdf, "test-url", chunk_size=200)


@pytest.mark.asyncio
async def test_multi_page_pdf_skips_first_page_word_overlap():
    """Multi-page PDF should skip page 1 (cover) for WordOverlap strategy."""
    mock_pdf = mock.MagicMock()
    mock_pdf.metadata = {"title": "Bog", "author": "Forfatter"}
    mock_pdf.__len__ = mock.MagicMock(return_value=3)

    p1 = mock.MagicMock()
    p1.get_text.return_value = "Forside tekst irrelevant." * 5
    p2 = mock.MagicMock()
    p2.get_text.return_value = "Side to indhold." * 30
    p3 = mock.MagicMock()
    p3.get_text.return_value = "Side tre indhold." * 30
    mock_pdf.__getitem__ = mock.MagicMock(side_effect=[p1, p2, p3])

    result = await _run_pipeline(mock_pdf, WordOverlapChunkingStrategy())

    pages = {page for page, _ in result["chunks"]}
    assert 1 not in pages, "Første side må ikke være med for multi-page PDF"
    assert pages.issubset({2, 3})


@pytest.mark.asyncio
async def test_multi_page_pdf_skips_first_page_sentence_splitter():
    """Multi-page PDF should skip page 1 (cover) for SentenceSplitter strategy."""
    mock_pdf = mock.MagicMock()
    mock_pdf.metadata = {"title": "Bog", "author": "Forfatter"}
    mock_pdf.__len__ = mock.MagicMock(return_value=2)

    p1 = mock.MagicMock()
    p1.get_text.return_value = "Forside kort tekst."
    p2 = mock.MagicMock()
    p2.get_text.return_value = "Anden side indhold. Flere sætninger her."
    mock_pdf.__getitem__ = mock.MagicMock(side_effect=[p1, p2])

    result = await _run_pipeline(mock_pdf, SentenceSplitterChunkingStrategy())

    pages = {page for page, _ in result["chunks"]}
    assert 1 not in pages
    assert pages == {2}


@pytest.mark.asyncio
async def test_single_page_pdf_is_not_skipped():
    """Single-page PDF must not remove its only page."""
    mock_pdf = mock.MagicMock()
    mock_pdf.metadata = {"title": "Enkelt", "author": "Forfatter"}
    mock_pdf.__len__ = mock.MagicMock(return_value=1)

    p1 = mock.MagicMock()
    p1.get_text.return_value = "Enkelt side indhold her med flere ord." * 5
    mock_pdf.__getitem__ = mock.MagicMock(side_effect=[p1])

    result = await _run_pipeline(mock_pdf, WordOverlapChunkingStrategy())

    pages = {page for page, _ in result["chunks"]}
    assert pages == {1}, "Single-page dokument skal beholde side 1"
