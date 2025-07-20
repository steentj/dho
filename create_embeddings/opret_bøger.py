import asyncio
import aiohttp
import ssl
from aiohttp import TCPConnector
import fitz  # PyMuPDF
from dotenv import load_dotenv
import os
import logging
import sys
from pathlib import Path
from create_embeddings.logging_config import setup_logging
from create_embeddings.chunking import ChunkingStrategy, ChunkingStrategyFactory

# Import our new dependency injection system
sys.path.append(str(Path(__file__).parent.parent))

# Import embedding providers from the new providers package
from create_embeddings.providers import (
    EmbeddingProvider,
    EmbeddingProviderFactory
)
# Import classes for backward compatibility - these are re-exported
from create_embeddings.providers import OpenAIEmbeddingProvider, DummyEmbeddingProvider

# Set up logger for this module
logger = logging.getLogger(__name__)

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
    except Exception as e:
        # Catch all exceptions (network errors, timeouts, etc.) and handle gracefully
        logging.error(f"Fejl ved hentning af {url}: {e}")
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


async def save_book(book, book_service, embedding_provider: EmbeddingProvider):
    """Gem bogens metadata, tekst og embeddings i databasen using dependency injection."""
    try:
        # Get the provider-specific table name
        table_name = embedding_provider.get_table_name()
        
        # DEFENSIVE FIX: Ensure chunk_text is always a string before passing to service
        # This prevents the "expected str, got list" PostgreSQL error
        fixed_book = book.copy()
        fixed_chunks = []
        
        for (page_num, chunk_text), embedding in zip(book["chunks"], book["embeddings"]):
            if isinstance(chunk_text, list):
                # Join list elements into a single string
                chunk_text = " ".join(str(item) for item in chunk_text)
                logger.warning(f"Fixed chunk_text data type: converted list to string for page {page_num}")
            elif not isinstance(chunk_text, str):
                # Convert any other type to string
                chunk_text = str(chunk_text)
                logger.warning(f"Fixed chunk_text data type: converted {type(chunk_text)} to string for page {page_num}")
            
            fixed_chunks.append((page_num, chunk_text))
        
        # Update the book with fixed chunks
        fixed_book["chunks"] = fixed_chunks
        
        # Use the BookService interface - no more magic string detection!
        await book_service.save_book_with_chunks(fixed_book, table_name)
            
        logging.info(f"Successfully saved book {book['titel']} with {len(book['chunks'])} chunks to {table_name} table")
        
    except Exception as e:
        book_url = book.get("pdf_url") or book.get("url") or book.get("pdf-url")
        logging.exception(
            f"Fejl ved indsættelse af bog {book_url} i databasen: {e}"
        )
        raise


async def parse_book(pdf, book_url, chunk_size, embedding_provider: EmbeddingProvider, chunking_strategy: ChunkingStrategy):
    """Udtræk tekst fra PDF, opdel i chunks, generer embeddings."""
    try:
        metadata = pdf.metadata or {}  # Håndter manglende metadata
        book = {
            "pdf-url": book_url,  # Standard key used throughout the system
            "titel": metadata.get("title", "Ukendt Titel"),
            "forfatter": metadata.get("author", "Ukendt Forfatter"),
            "sider": len(pdf),
            "chunks": [],
            "embeddings": [],
        }

        pdf_pages = extract_text_by_page(pdf)

        # Use the strategy's process_document method to handle all chunking logic
        for page_num, chunk_text in chunking_strategy.process_document(pdf_pages, chunk_size, book["titel"]):
            book["chunks"].append((page_num, chunk_text))
            embedding = await embedding_provider.get_embedding(chunk_text)
            book["embeddings"].append(embedding)

    finally:
        pdf.close()  # Luk PDF for at frigøre ressourcer

    return book


async def process_book(book_url, chunk_size, book_service, session, embedding_provider: EmbeddingProvider, chunking_strategy: ChunkingStrategy):
    """Behandl en enkelt bog fra URL til database using dependency injection."""
    try:
        # Check if book already exists with embeddings for this provider
        has_embeddings = await book_service.book_exists_with_provider(book_url, embedding_provider.get_provider_name())
        if has_embeddings:
            logging.info(f"Bogen {book_url} er allerede behandlet med {embedding_provider.get_provider_name()} provider - springer over")
            return

        # If book doesn't exist or embeddings don't exist for this provider, fetch PDF and process it
        try:
            pdf = await fetch_pdf(book_url, session)
        except Exception as e:
            # Handle network errors gracefully - treat like fetch_pdf returning None
            logging.warning(f"Netværksfejl ved hentning af PDF fra {book_url}: {e}")
            pdf = None
        
        if pdf:
            book = await parse_book(pdf, book_url, chunk_size, embedding_provider, chunking_strategy)
            await save_book(book, book_service, embedding_provider)
            logging.info(f"{book['titel']} fra {book_url} er behandlet og gemt i databasen")
        else:
            logging.warning(f"Kunne ikke hente PDF fra {book_url}")
            # Don't raise exception - just log and continue
            
    except Exception as e:
        logging.exception(f"Fejl ved behandling af {book_url}: {type(e).__name__}")
        raise  # Re-raise the exception so the wrapper can count it as failed

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

    # Initialize database service using appropriate pattern based on environment
    # Use pool service for production (concurrent processing), single connection for tests
    use_pool_service = os.getenv("USE_POOL_SERVICE", "true").lower() == "true"
    
    # Detect if we're in a test environment by checking for typical test markers
    in_test_environment = (
        os.getenv("TESTING", "false").lower() == "true" or
        os.getenv("PYTEST_CURRENT_TEST") is not None or
        'pytest' in os.getenv("_", "") or
        'test' in os.getenv("_", "")
    )
    
    if use_pool_service and not in_test_environment:
        # Production mode: use connection pool for concurrent processing
        from database.postgresql_service import create_postgresql_pool_service
        pool_service = await create_postgresql_pool_service()
        service_to_use = pool_service
    else:
        # Test mode or single connection mode: use original logic
        from database.factory import create_database_factory
        
        db_factory = create_database_factory()
        db_connection = await db_factory.create_connection()
        book_service = db_factory.create_book_repository(db_connection)
        service_to_use = book_service

    try:
        # Database service is established
        if use_pool_service and not in_test_environment:
            logging.info("Database connection pool created using factory pattern")
        else:
            logging.info("Database connection created using factory pattern")

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
                        process_book, semaphore, url, chunk_size, service_to_use, session, embedding_provider, chunking_strategy
                    )
                )
                for url in book_urls
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

    except Exception as e:
        logging.exception(f"Fatal fejl i hovedprogrammet: {type(e).__name__}")
    finally:
        # Cleanup database service
        if use_pool_service and not in_test_environment:
            await pool_service.disconnect()
            logging.info("Database connection pool closed")
        else:
            await db_connection.close()
            logging.info("Database connection closed")


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
