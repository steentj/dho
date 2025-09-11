"""MANUEL CHUNKING TEST (ingen database writes)
=================================================

Formål:
    Sammenligne output fra de to chunking strategier (sentence_splitter & word_overlap)
    på en rigtig PDF og generere Markdown-tabeller med chunk-metadata.

Kørsel (anbefalet – uden coverage krav):
    pytest -m manual create_embeddings/tests/manual/test_manual_real_pdf_chunking.py --no-cov -s

Alternativ (kun én strategi):
    pytest -m manual -k sentence_splitter --no-cov -s
    pytest -m manual -k word_overlap --no-cov -s

Hvorfor --no-cov?
    Den globale coverage threshold (80%) er ikke relevant for manuelle artefakt-tests.
    Uden --no-cov kan en session med kun manuelle tests give "No data collected" fejl.

Input PDF:
    Filen forventes at ligge i samme mappe som denne test: Foråret1945.pdf
    Skift FIL_NAVN variablen nedenfor hvis du bruger en anden fil (placer den i samme mappe).

Output:
    Markdown filer genereres i: create_embeddings/tests/manual/output/
    Filnavne: chunks_{strategy}_{timestamp}.md

Indhold i Markdown tabel:
    - Løbenummer
    - Startside
    - Antal ord og tegn
    - Preview (første 120 tegn)
    - Om titel-prefix findes (kun sentence_splitter)
    - Embedding dimension & kald-antal

Sikkerhed / Isolation:
    - Ingen database writes (NoOpBookService)
    - Ingen eksterne embedding API kald (MockEmbeddingProvider)
    - Skip hvis PDF mangler

Note om test discovery:
    Filen matcher mønsteret test_*.py og opdages automatisk under create_embeddings/tests.
    -k parameter er kun nødvendig hvis du vil filtrere specifikke tests.
Auto-skip ved manglende PDF:
    Hvis input-PDF ikke findes ved import, bliver hele testfilen markeret som SKIPPED med forklaring.
"""
from pathlib import Path
import sys
import pytest
import fitz

# Defensive: ensure the directory that directly contains the 'create_embeddings' package
# is on sys.path. We walk upwards until we find a folder containing create_embeddings/__init__.py
try:  # pragma: no cover (manual runtime guard)
    _test_file = Path(__file__).resolve()
    for _parent in _test_file.parents:
        if (_parent / 'create_embeddings' / '__init__.py').exists():
            if str(_parent) not in sys.path:
                sys.path.insert(0, str(_parent))
            break
    else:
        print('[manual-test-warning] Fandt ikke create_embeddings pakke ved opstigning af stier.')
except Exception as _e:  # pragma: no cover
    print(f"[manual-test-warning] Undtagelse under sys.path injektion: {_e}")

from create_embeddings.chunking import SentenceSplitterChunkingStrategy, WordOverlapChunkingStrategy
from create_embeddings.book_processing_pipeline import BookProcessingPipeline
from create_embeddings.book_service_interface import IBookService

# -------- Configuration --------
_THIS_DIR = Path(__file__).parent
FIL_NAVN = "Foråret1945.pdf"  # Skift hvis du vil bruge en anden fil placeret i samme mappe
REAL_PDF_PATH = _THIS_DIR / FIL_NAVN
OUTPUT_DIR = Path("create_embeddings/tests/manual/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Hvis PDF mangler: tydelig skip (samlede test tælles, men køres ikke)
pytestmark = pytest.mark.skipif(
    not REAL_PDF_PATH.exists(),
    reason=f"Manuel PDF mangler: {REAL_PDF_PATH}. Placer filen eller ret FIL_NAVN."
)

# -------- Mock Implementations (No DB Writes) --------
class NoOpBookService(IBookService):
    """Implements interface but performs no persistence. Returns synthetic IDs."""
    def __init__(self):
        self._next_id = 1

    async def save_book_with_chunks(self, book: dict, table_name: str) -> int:
        # Return synthetic ID only; no persistence.
        book_id = self._next_id
        self._next_id += 1
        return book_id

    async def book_exists_with_provider(self, pdf_url: str, provider_name: str) -> bool:
        return False

class MockEmbeddingProvider:
    """Deterministic, lightweight embedding provider (no external calls)."""
    def __init__(self, dim: int = 32):
        self.dim = dim
        self.calls = 0

    async def get_embedding(self, text: str):
        self.calls += 1
        # Simple deterministic vector based on length
        base = len(text) % 10 / 10.0
        return [base + (i / self.dim) for i in range(self.dim)]

    async def has_embeddings_for_book(self, book_id: int, db_service) -> bool:
        return False

    def get_provider_name(self) -> str:
        return "mock_manual"

    def get_table_name(self) -> str:
        return "chunks_mock_manual"

# -------- Helper Functions --------

def _load_pdf(pdf_path: Path):
    if not pdf_path.exists():
        pytest.skip(f"Real PDF missing: {pdf_path}. Please provide a PDF for manual test.")
    return fitz.open(pdf_path)

async def _process(pdf_path: Path, strategy_name: str, strategy, chunk_size: int = 400):
    pdf = _load_pdf(pdf_path)
    try:
        provider = MockEmbeddingProvider()
        service = NoOpBookService()
        pipeline = BookProcessingPipeline(
            book_service=service,
            embedding_provider=provider,
            chunking_strategy=strategy,
        )
        book_data = await pipeline.parse_pdf_to_book_data(pdf, str(pdf_path), chunk_size)
        return book_data, provider
    finally:
        pdf.close()

def _write_markdown(book_data: dict, provider: MockEmbeddingProvider, strategy_name: str):
    from datetime import datetime as _dt
    timestamp = _dt.now().strftime("%Y%m%d_%H%M%S")
    md_path = OUTPUT_DIR / f"chunks_{strategy_name}_{timestamp}.md"

    lines: list[str] = []
    lines.append(f"# Chunk Resultat - Strategy: {strategy_name}\n")
    lines.append(f"Kilde PDF: `{book_data['pdf-url']}`  ")
    lines.append(f"Titel: {book_data['titel']}  ")
    lines.append(f"Forfatter: {book_data['forfatter']}  ")
    lines.append(f"Antal sider: {book_data['sider']}  ")
    lines.append(f"Antal chunks: {len(book_data['chunks'])}  ")
    lines.append(f"Embedding dimension: {len(book_data['embeddings'][0]) if book_data['embeddings'] else 0}  ")
    lines.append(f"Embedding kald: {provider.calls}\n")

    lines.append("| # | Side | Ord | Tegn | Preview (første 120 tegn) | Har titelprefix | Embedding-længde |")
    lines.append("|---|------|-----|------|---------------------------|-----------------|------------------|")

    for idx, ((page_num, chunk_text), emb) in enumerate(zip(book_data['chunks'], book_data['embeddings']), start=1):
        words = len(chunk_text.split())
        chars = len(chunk_text)
        preview = chunk_text[:120].replace("|", "\\|").replace("\n", " ")
        has_title_prefix = chunk_text.startswith(f"##{book_data['titel']}##")
        lines.append(
            f"| {idx} | {page_num} | {words} | {chars} | {preview} | {has_title_prefix} | {len(emb)} |"
        )

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Markdown resultat skrevet: {md_path}")

# -------- Tests (Manual) --------

@pytest.mark.manual
@pytest.mark.integration
@pytest.mark.asyncio
async def test_manual_real_pdf_sentence_splitter():
    """Manuel test: sentence_splitter strategi. Ingen DB writes."""
    strategy = SentenceSplitterChunkingStrategy()
    book_data, provider = await _process(REAL_PDF_PATH, "sentence_splitter", strategy, chunk_size=400)

    # Minimum sanity assertions (no persistence side-effects)
    assert len(book_data['chunks']) == len(book_data['embeddings'])
    assert provider.calls == len(book_data['chunks'])

    # Ensure title-prefix present for all chunks in this strategy
    for _, c in book_data['chunks']:
        assert c.startswith(f"##{book_data['titel']}##")

    _write_markdown(book_data, provider, "sentence_splitter")

@pytest.mark.manual
@pytest.mark.integration
@pytest.mark.asyncio
async def test_manual_real_pdf_word_overlap():
    """Manuel test: word_overlap strategi. Ingen DB writes."""
    strategy = WordOverlapChunkingStrategy()
    book_data, provider = await _process(REAL_PDF_PATH, "word_overlap", strategy, chunk_size=400)

    assert len(book_data['chunks']) == len(book_data['embeddings'])
    assert provider.calls == len(book_data['chunks'])

    # Ensure NO title-prefix for this strategy
    for _, c in book_data['chunks']:
        assert not c.startswith(f"##{book_data['titel']}##")

    _write_markdown(book_data, provider, "word_overlap")
