import asyncio
import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import logging

# Import ALL existing functionality from opret_bøger
from .opret_bøger import (
    indlæs_urls,
    process_book,
)
from .providers import EmbeddingProviderFactory
from .chunking import ChunkingStrategyFactory
from .logging_config import setup_logging

class BookProcessorWrapper:
    """Wrapper around existing opret_bøger.py functionality"""
    
    def __init__(self, output_dir: str = "/app/output", failed_dir: str = "/app/failed"):
        self.output_dir = Path(output_dir)
        self.failed_dir = Path(failed_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.failed_dir.mkdir(exist_ok=True)
        
        # Progress tracking
        self.status_file = self.output_dir / "processing_status.json"
        self.processed_count = 0
        self.failed_count = 0
        self.total_count = 0
        self.failed_books = []
        
    def setup_logging(self):
        """Setup logging using shared configuration"""
        # Use shared logging configuration with the output directory
        setup_logging(log_dir=str(self.output_dir))
    
    def update_status(self, status: str = "kører"):
        """Update processing status file"""
        status_data = {
            "status": status,
            "total_boeger": self.total_count,
            "behandlet": self.processed_count,
            "fejlet": self.failed_count,
            "sidst_opdateret": datetime.now().isoformat(),
            "embedding_model": os.getenv("OPENAI_MODEL", "ukendt"),
            "udbyder": os.getenv("PROVIDER", "ukendt")
        }
        
        with open(self.status_file, 'w') as f:
            json.dump(status_data, f, indent=2)
    
    def save_failed_books(self):
        """Save failed books for retry"""
        if self.failed_books:
            failed_file = self.failed_dir / "failed_books.json"
            with open(failed_file, 'w') as f:
                json.dump(self.failed_books, f, indent=2)
    
    async def process_single_book_with_monitoring(self, book_url: str, chunk_size: int, 
                                                  pool, session, embedding_provider, chunking_strategy):
        """Wrapper around existing process_book with monitoring, now with injectable chunking strategy"""
        try:
            await process_book(book_url, chunk_size, pool, session, embedding_provider, chunking_strategy)
            self.processed_count += 1
            logging.info(f"✓ Bog behandlet: {book_url}")
        except Exception as e:
            self.failed_count += 1
            self.failed_books.append({
                "url": book_url,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            logging.error(f"✗ Fejl ved behandling af {book_url}: {e}")
        self.update_status()
    
    async def process_books_from_file(self, input_file: str):
        """Process books using existing opret_bøger logic with monitoring and injectable chunking strategy"""
        input_file_path = Path("/app/input") / input_file
        if not input_file_path.exists():
            raise FileNotFoundError(f"Inputfil ikke fundet: {input_file_path}")
        book_urls = indlæs_urls(str(input_file_path))
        self.total_count = len(book_urls)
        logging.info(f"Behandler {self.total_count} bøger ved hjælp af eksisterende opret_bøger logik")
        from dotenv import load_dotenv
        load_dotenv(override=True)
        database = os.getenv("POSTGRES_DB")
        db_user = os.getenv("POSTGRES_USER") 
        db_password = os.getenv("POSTGRES_PASSWORD")
        api_key = os.getenv("OPENAI_API_KEY")
        provider = os.getenv("PROVIDER")
        chunk_size = int(os.getenv("CHUNK_SIZE", "500"))
        chunking_strategy_name = os.getenv("CHUNKING_STRATEGY", "sentence_splitter")
        embedding_provider = EmbeddingProviderFactory.create_provider(provider, api_key)
        chunking_strategy = ChunkingStrategyFactory.create_strategy(chunking_strategy_name)
        self.update_status("starter")
        import asyncpg
        import aiohttp
        import ssl
        from aiohttp import TCPConnector
        try:
            db_host = os.getenv("POSTGRES_HOST", "postgres")
            async with asyncpg.create_pool(
                host=db_host, database=database, user=db_user, password=db_password
            ) as pool:
                ssl_context = ssl.create_default_context()
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                async with aiohttp.ClientSession(
                    connector=TCPConnector(ssl=ssl_context),
                    headers=headers
                ) as session:
                    semaphore = asyncio.Semaphore(5)
                    tasks = [
                        asyncio.create_task(
                            self.semaphore_guard_with_monitoring(
                                semaphore, url, chunk_size, pool, session, embedding_provider, chunking_strategy
                            )
                        )
                        for url in book_urls
                    ]
                    await asyncio.gather(*tasks, return_exceptions=True)
                    self.update_status("afsluttet")
                    self.save_failed_books()
                    logging.info(f"Behandling afsluttet: {self.processed_count} vellykket, {self.failed_count} fejlet")
        except Exception as e:
            logging.exception(f"Fatal fejl i behandlingen: {e}")
            self.update_status("fejl")
            raise
    
    async def semaphore_guard_with_monitoring(self, semaphore, url, chunk_size, pool, session, embedding_provider, chunking_strategy):
        """Use existing semaphore pattern with monitoring and injectable chunking strategy"""
        async with semaphore:
            await self.process_single_book_with_monitoring(
                url, chunk_size, pool, session, embedding_provider, chunking_strategy
            )
    
    async def retry_failed_books(self):
        """Retry previously failed books"""
        failed_file = self.failed_dir / "failed_books.json"
        
        if not failed_file.exists():
            logging.info("Ingen fejlede bøger fil fundet")
            return
        
        with open(failed_file) as f:
            failed_data = json.load(f)
        
        if not failed_data:
            logging.info("Ingen fejlede bøger at prøve igen")
            return
        
        # Create temporary URL file for retry
        retry_urls = [book["url"] for book in failed_data]
        retry_file = self.output_dir / "retry_urls.txt"
        
        with open(retry_file, 'w') as f:
            f.write('\n'.join(retry_urls))
        
        # Reset counters for retry
        self.failed_books = []
        self.processed_count = 0
        self.failed_count = 0
        
        logging.info(f"Prøver igen med {len(retry_urls)} fejlede bøger")
        
        # Copy retry file to input directory for processing
        retry_input_file = Path("/app/input") / "retry_urls.txt"
        retry_input_file.write_text('\n'.join(retry_urls))
        
        # Process using existing logic
        await self.process_books_from_file("retry_urls.txt")

def main():
    """Main entry point with argument parsing"""
    
    parser = argparse.ArgumentParser(description='Strømlinet bogbehandler der bruger eksisterende opret_bøger logik')
    parser.add_argument('--input-file', help='Inputfil med bog-URL\'er')
    parser.add_argument('--retry-failed', action='store_true', help='Prøv fejlede bøger igen')
    parser.add_argument('--validate-config', action='store_true', help='Valider konfiguration')
    
    args = parser.parse_args()
    
    wrapper = BookProcessorWrapper()
    wrapper.setup_logging()
    
    if args.validate_config:
        # Validate existing environment variables
        required_vars = ["POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", 
                        "OPENAI_API_KEY", "PROVIDER"]
        missing = [var for var in required_vars if not os.getenv(var)]
        
        if missing:
            print(f"Manglende påkrævede miljøvariabler: {missing}")
            sys.exit(1)
        else:
            print("✅ Alle påkrævede miljøvariabler er sat")
            print(f"Embedding Model: {os.getenv('OPENAI_MODEL', 'text-embedding-ada-002')}")
            print(f"Udbyder: {os.getenv('PROVIDER')}")
            print(f"Chunk Størrelse: {os.getenv('CHUNK_SIZE', '500')}")
            sys.exit(0)
    
    if args.retry_failed:
        asyncio.run(wrapper.retry_failed_books())
    elif args.input_file:
        asyncio.run(wrapper.process_books_from_file(args.input_file))
    else:
        print("Fejl: Enten --input-file eller --retry-failed skal angives")
        sys.exit(1)

if __name__ == "__main__":
    main()
