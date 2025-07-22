import asyncio
import os
import logging
import sys
from pathlib import Path
from create_embeddings.logging_config import setup_logging
from create_embeddings.chunking import ChunkingStrategy

# Import our new dependency injection system
sys.path.append(str(Path(__file__).parent.parent))

# Import embedding providers from the new providers package
from create_embeddings.providers import EmbeddingProvider


# Set up logger for this module
logger = logging.getLogger(__name__)

def indlæs_urls(file_path):
    """Læs URL'er fra filen."""
    with open(file_path, "r") as file:
        return [line.strip() for line in file.readlines() if line.strip()]


async def process_book(book_url, chunk_size, book_service, session, embedding_provider: EmbeddingProvider, chunking_strategy: ChunkingStrategy):
    """Behandl en enkelt bog fra URL til database using dependency injection and pipeline pattern."""
    from .tests.test_utils import process_book_adapter
    
    # Use the adapter to maintain backward compatibility
    await process_book_adapter(
        book_url=book_url,
        chunk_size=chunk_size,
        book_service=book_service,
        session=session,
        embedding_provider=embedding_provider,
        chunking_strategy=chunking_strategy
    )

async def main():
    """Hovedfunktion for at hente og behandle alle bøger using dependency injection."""
    from dotenv import load_dotenv
    from .book_processing_orchestrator import BookProcessingApplication
    
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
    
    # Configure logging using shared configuration
    setup_logging(log_dir=os.getenv("LOG_DIR"))
    
    # Calculate URL file path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    url_file_path = os.path.join(script_dir, url_file)
    
    # Delegate to application orchestrator
    try:
        await BookProcessingApplication.run_book_processing(
            database_url=database_url,
            provider_name=provider,
            api_key=api_key,
            chunking_strategy_name=chunking_strategy_name,
            chunk_size=chunk_size,
            url_file_path=url_file_path,
            concurrency_limit=5
        )
    except Exception as e:
        logging.exception(f"Fatal fejl i hovedprogrammet: {type(e).__name__}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
