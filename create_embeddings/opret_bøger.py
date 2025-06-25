import asyncio
import aiohttp
import ssl
from aiohttp import TCPConnector
import fitz  # PyMuPDF
from dotenv import load_dotenv
import os
import logging
from create_embeddings.logging_config import setup_logging
from create_embeddings.chunking import ChunkingStrategy, ChunkingStrategyFactory

# Import our new dependency injection system
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from database import BookService, PostgreSQLService

# Import embedding providers from the new providers package
from .providers import (
    EmbeddingProvider,
    EmbeddingProviderFactory
)
# Import classes for backward compatibility - these are re-exported
from .providers import OpenAIEmbeddingProvider, DummyEmbeddingProvider

def indlæs_urls(file_path):
    """Læs URL'er fra filen."""
    with open(file_path, "r") as file:
        return [line.strip() for line in file.readlines() if line.strip()]


async def fetch_pdf(url, session) -> fitz.Document:
    """Hent en PDF fra en URL."""
    try:
        async with session.get(url, timeout=30) as response:
            if response.status == 200:
                raw_pdf = await response.read()
                # Retter åbningsmetoden for PyMuPDF
                return fitz.open(stream=raw_pdf, filetype="pdf")
            else:
                logging.error(
                    f"Fejl ved hentning af {url}: Statuskode {response.status}"
                )
                return None
    except aiohttp.ClientError as e:
        logging.exception(f"Netværksfejl ved hentning af {url}: {e}")
        return None


def extract_text_by_page(pdf) -> dict:
    """Udtræk tekst fra hver side i PDF'en."""
    pages_text = {}
    for page_num in range(len(pdf)):
        text = pdf[page_num].get_text()
        # Rens tekst for bløde linjeskift mv.
        pages_text[page_num + 1] = (
            text.replace(" \xad\n", "")
            .replace("\xad\n", "")
            .replace("-\n", "")
            .replace("- \n", "")
        )
    return pages_text


async def save_book(book, book_service: BookService):
    """Gem bogens metadata, tekst og embeddings i databasen using dependency injection."""
    try:
        # Create book metadata using the service
        book_id = await book_service.create_book(
            pdf_navn=book["pdf-url"],
            titel=book["titel"],
            forfatter=book["forfatter"],
            antal_sider=book["sider"]
        )

        # Save chunks using the service
        for (page_num, chunk_text), embedding in zip(
            book["chunks"], book["embeddings"]
        ):
            await book_service.create_chunk(
                book_id=book_id,
                sidenr=page_num,
                chunk=chunk_text,
                embedding=embedding
            )
            
        logging.info(f"Successfully saved book {book['titel']} with {len(book['chunks'])} chunks")
        
    except Exception as e:
        logging.exception(
            f"Fejl ved indsættelse af bog {book['pdf-url']} i databasen: {e}"
        )
        raise

async def parse_book(pdf, book_url, chunk_size, embedding_provider: EmbeddingProvider, chunking_strategy: ChunkingStrategy):
    """Udtræk tekst fra PDF, opdel i chunks, generer embeddings."""
    try:
        metadata = pdf.metadata or {}  # Håndter manglende metadata
        book = {
            "pdf-url": book_url,
            "titel": metadata.get("title", "Ukendt Titel"),
            "forfatter": metadata.get("author", "Ukendt Forfatter"),
            "sider": len(pdf),
            "chunks": [],
            "embeddings": [],
        }

        pdf_pages = extract_text_by_page(pdf)

        # Check if we're using WordOverlapChunkingStrategy for cross-page chunking
        from create_embeddings.chunking import WordOverlapChunkingStrategy
        if isinstance(chunking_strategy, WordOverlapChunkingStrategy):
            # Cross-page chunking: concatenate all pages and track page boundaries
            page_chunks = _process_cross_page_chunking(pdf_pages, chunk_size, chunking_strategy, book["titel"])
            
            for page_num, chunk_text in page_chunks:
                if chunk_text.strip():  # Ignorer tomme chunks
                    book["chunks"].append((page_num, chunk_text))
                    embedding = await embedding_provider.get_embedding(chunk_text)
                    book["embeddings"].append(embedding)
        else:
            # Traditional page-by-page chunking for other strategies
            for page_num, page_text in pdf_pages.items():
                for chunk in chunking_strategy.chunk_text(page_text, chunk_size, book["titel"]):
                    if chunk.strip():  # Ignorer tomme chunks
                        book["chunks"].append((page_num, chunk))
                        embedding = await embedding_provider.get_embedding(chunk)
                        book["embeddings"].append(embedding)
    finally:
        pdf.close()  # Luk PDF for at frigøre ressourcer

    return book


def _process_cross_page_chunking(pdf_pages: dict, chunk_size: int, chunking_strategy, title: str) -> list[tuple[int, str]]:
    """
    Process text across multiple pages and return chunks with their starting page numbers.
    Returns list of (page_num, chunk_text) tuples.
    """
    # Build page markers and concatenated text
    full_text_parts = []
    page_markers = []  # Track where each page starts in the full text
    current_word_position = 0
    
    for page_num in sorted(pdf_pages.keys()):
        page_text = pdf_pages[page_num].strip()
        if page_text:
            page_markers.append((current_word_position, page_num))
            full_text_parts.append(page_text)
            current_word_position += len(page_text.split())
    
    # Concatenate all pages
    full_text = " ".join(full_text_parts)
    
    # Get chunks from the strategy
    chunks = list(chunking_strategy.chunk_text(full_text, chunk_size, title))
    
    # Determine starting page for each chunk
    result_chunks = []
    current_word_pos = 0
    
    for chunk in chunks:
        chunk_start_page = _find_starting_page(current_word_pos, page_markers)
        result_chunks.append((chunk_start_page, chunk))
        
        # Move position forward by the number of words in this chunk
        current_word_pos += len(chunk.split())
    
    return result_chunks


def _find_starting_page(word_position: int, page_markers: list[tuple[int, int]]) -> int:
    """
    Find which page a given word position starts on.
    page_markers is a list of (word_position, page_num) tuples.
    """
    if not page_markers:
        return 1
    
    # Find the last page marker that starts before or at the given position
    starting_page = page_markers[0][1]  # Default to first page
    
    for marker_pos, page_num in page_markers:
        if marker_pos <= word_position:
            starting_page = page_num
        else:
            break
    
    return starting_page


async def process_book(book_url, chunk_size, book_service: BookService, session, embedding_provider: EmbeddingProvider, chunking_strategy: ChunkingStrategy):
    """Behandl en enkelt bog fra URL til database using dependency injection."""
    try:
        # Check om bogen allerede findes i databasen FØRST
        existing_book = await book_service.get_book_by_pdf_navn(book_url)
        if existing_book:
            logging.info(f"Bogen {book_url} er allerede i databasen - springer over")
            return
        
        # Hvis bogen ikke findes, hent PDF og behandl den
        pdf = await fetch_pdf(book_url, session)
        
        if pdf:
            book = await parse_book(pdf, book_url, chunk_size, embedding_provider, chunking_strategy)
            await save_book(book, book_service)
            logging.info(f"{book['titel']} fra {book_url} er behandlet og gemt i databasen")
        else:
            logging.warning(f"Kunne ikke hente PDF fra {book_url}")
            
    except Exception as e:
        logging.exception(f"Fejl ved behandling af {book_url}: {type(e).__name__}")


async def main():
    """Hovedfunktion for at hente og behandle alle bøger using dependency injection."""
    load_dotenv(override=True)
    
    # Hent miljøvariabler
    database_url = os.getenv("DATABASE_URL")
    api_key = os.getenv("OPENAI_API_KEY")
    provider = os.getenv("PROVIDER", "openai")
    chunk_size = int(os.getenv("CHUNK_SIZE", "1000"))
    url_file = os.getenv("URL_FILE", "test_input.txt")
    chunking_strategy_name = os.getenv("CHUNKING_STRATEGY", "sentence_splitter")

    if not database_url:
        logging.error("DATABASE_URL environment variable is required")
        return

    # Initialize embedding provider
    embedding_provider = EmbeddingProviderFactory.create_provider(provider, api_key)

    # Initialize chunking strategy
    chunking_strategy = ChunkingStrategyFactory.create_strategy(chunking_strategy_name)

    # Configure logging using shared configuration
    setup_logging(log_dir=os.getenv("LOG_DIR"))

    script_dir = os.path.dirname(os.path.abspath(__file__))
    url_file_path = os.path.join(script_dir, url_file)
    book_urls = indlæs_urls(url_file_path)

    # Initialize database service using dependency injection
    db_service = PostgreSQLService(database_url)
    book_service = BookService(db_service)

    try:
        # Connect to database
        await db_service.connect()
        logging.info("Database service connected using dependency injection")

        # Create HTTP session
        ssl_context = ssl.create_default_context()
        async with aiohttp.ClientSession(
            connector=TCPConnector(ssl=ssl_context)
        ) as session:
            # Begræns antal samtidige opgaver
            semaphore = asyncio.Semaphore(5)
            tasks = [
                asyncio.create_task(
                    semaphore_guard(
                        process_book, semaphore, url, chunk_size, book_service, session, embedding_provider, chunking_strategy
                    )
                )
                for url in book_urls
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

    except Exception as e:
        logging.exception(f"Fatal fejl i hovedprogrammet: {type(e).__name__}")
    finally:
        # Cleanup database connection
        await db_service.disconnect()
        logging.info("Database service disconnected")


async def semaphore_guard(coro, semaphore, *args):
    """Hjælpefunktion til at begrænse samtidige opgaver."""
    async with semaphore:
        await coro(*args)


# Backward compatibility exports - these need to be available for existing code
__all__ = [
    'EmbeddingProvider',
    'OpenAIEmbeddingProvider', 
    'DummyEmbeddingProvider',
    'EmbeddingProviderFactory',
    'indlæs_urls',
    'fetch_pdf',
    'extract_text_by_page',
    'save_book',
    'parse_book',
    'process_book',
    'main',
    'semaphore_guard'
]

if __name__ == "__main__":
    asyncio.run(main())
