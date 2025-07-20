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


async def process_book(book_url, chunk_size, book_service, session, embedding_provider: EmbeddingProvider, chunking_strategy: ChunkingStrategy):
    """Behandl en enkelt bog fra URL til database using dependency injection and pipeline pattern."""
    from .book_processing_pipeline import BookProcessingPipeline
    
    # Create pipeline with injected dependencies
    pipeline = BookProcessingPipeline(
        book_service=book_service,
        embedding_provider=embedding_provider,
        chunking_strategy=chunking_strategy
    )
    
    # Delegate to pipeline
    await pipeline.process_book_from_url(book_url, chunk_size, session)

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

    # Initialize database service using pool service (preferred for concurrent processing)
    from database.postgresql_service import create_postgresql_pool_service
    book_service = await create_postgresql_pool_service()

    try:
        logging.info("Database connection pool created using factory pattern")

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
        # Cleanup database service
        await book_service.disconnect()
        logging.info("Database connection pool closed")


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
    'process_book',
    'main',
    'semaphore_guard'
]

if __name__ == "__main__":
    asyncio.run(main())
