# Revised Implementation Plan: Streamline Adding Books to Vector Database

## Overview
Wrap the existing `opret_bøger.py` functionality (which works excellently) with containerization, batch input processing, and monitoring - without changing the core processing logic.

## Current Environment Variables (from existing code)
```bash
# Database Configuration
POSTGRES_DB=database_name
POSTGRES_USER=username  
POSTGRES_PASSWORD=password

# Embedding Configuration
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=text-embedding-ada-002  # Used by OpenAIEmbeddingProvider
PROVIDER=openai  # or "dummy" for testing

# Processing Configuration
CHUNK_SIZE=500  # Max tokens per chunk
URL_FILE=books.txt  # Input file name
```

## Revised Implementation Plan

### Phase 1: Minimal Wrapper Creation

#### Task 1.1: Create Wrapper Script
- **File**: `create_embeddings/book_processor_wrapper.py`
````python
# filepath: create_embeddings/book_processor_wrapper.py
import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

# Import ALL existing functionality from opret_bøger
from opret_bøger import (
    main as opret_main,
    indlæs_urls,
    process_book,
    EmbeddingProviderFactory
)

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
        """Setup logging using existing opret_bøger pattern"""
        log_file = self.output_dir / f"opret_bøger_{datetime.now():%Y-%m-%d_%H-%M-%S}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file, encoding="utf-8"),
                logging.StreamHandler(),
            ],
        )
        # Keep existing logger configuration
        logging.getLogger("openai").setLevel(logging.WARNING)
        logging.getLogger("aiohttp").setLevel(logging.WARNING)
    
    def update_status(self, status: str = "running"):
        """Update processing status file"""
        status_data = {
            "status": status,
            "total_books": self.total_count,
            "processed": self.processed_count,
            "failed": self.failed_count,
            "last_updated": datetime.now().isoformat(),
            "embedding_model": os.getenv("OPENAI_MODEL", "unknown"),
            "provider": os.getenv("PROVIDER", "unknown")
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
                                                  pool, session, embedding_provider):
        """Wrapper around existing process_book with monitoring"""
        try:
            # Use EXISTING process_book function unchanged
            await process_book(book_url, chunk_size, pool, session, embedding_provider)
            self.processed_count += 1
            logging.info(f"✓ Successfully processed: {book_url}")
            
        except Exception as e:
            self.failed_count += 1
            self.failed_books.append({
                "url": book_url,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            logging.error(f"✗ Failed to process {book_url}: {e}")
        
        # Update status after each book
        self.update_status()
    
    async def process_books_from_file(self, input_file: str):
        """Process books using existing opret_bøger logic with monitoring"""
        # Set environment variable for existing code
        os.environ["URL_FILE"] = input_file
        
        # Use existing URL loading function
        script_dir = Path("/app/input")
        url_file_path = script_dir / input_file
        
        if not url_file_path.exists():
            raise FileNotFoundError(f"Input file not found: {url_file_path}")
        
        # Use EXISTING indlæs_urls function
        book_urls = indlæs_urls(str(url_file_path))
        self.total_count = len(book_urls)
        
        logging.info(f"Processing {self.total_count} books using existing opret_bøger logic")
        
        # Use EXISTING environment setup
        from dotenv import load_dotenv
        load_dotenv(override=True)
        
        database = os.getenv("POSTGRES_DB")
        db_user = os.getenv("POSTGRES_USER") 
        db_password = os.getenv("POSTGRES_PASSWORD")
        api_key = os.getenv("OPENAI_API_KEY")
        provider = os.getenv("PROVIDER")
        chunk_size = int(os.getenv("CHUNK_SIZE"))
        
        # Use EXISTING embedding provider factory
        embedding_provider = EmbeddingProviderFactory.create_provider(provider, api_key)
        
        self.update_status("starting")
        
        # Use EXISTING database and session setup pattern
        import asyncpg
        import aiohttp
        import ssl
        from aiohttp import TCPConnector
        
        try:
            # Use EXISTING connection setup (but point to Docker database)
            db_host = os.getenv("POSTGRES_HOST", "postgres")  # Docker service name
            async with asyncpg.create_pool(
                host=db_host, database=database, user=db_user, password=db_password
            ) as pool:
                ssl_context = ssl.create_default_context()
                async with aiohttp.ClientSession(
                    connector=TCPConnector(ssl=ssl_context)
                ) as session:
                    
                    # Use EXISTING semaphore pattern  
                    semaphore = asyncio.Semaphore(5)
                    
                    # Create tasks using our monitoring wrapper
                    tasks = [
                        asyncio.create_task(
                            self.semaphore_guard_with_monitoring(
                                semaphore, url, chunk_size, pool, session, embedding_provider
                            )
                        )
                        for url in book_urls
                    ]
                    
                    await asyncio.gather(*tasks, return_exceptions=True)
                    
                    self.update_status("completed")
                    self.save_failed_books()
                    
                    logging.info(f"Processing completed: {self.processed_count} successful, {self.failed_count} failed")
                    
        except Exception as e:
            logging.exception(f"Fatal error in processing: {e}")
            self.update_status("error")
            raise
    
    async def semaphore_guard_with_monitoring(self, semaphore, url, chunk_size, pool, session, embedding_provider):
        """Use existing semaphore pattern with monitoring"""
        async with semaphore:
            await self.process_single_book_with_monitoring(
                url, chunk_size, pool, session, embedding_provider
            )
    
    async def retry_failed_books(self):
        """Retry previously failed books"""
        failed_file = self.failed_dir / "failed_books.json"
        
        if not failed_file.exists():
            logging.info("No failed books file found")
            return
        
        with open(failed_file) as f:
            failed_data = json.load(f)
        
        if not failed_data:
            logging.info("No failed books to retry")
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
        
        logging.info(f"Retrying {len(retry_urls)} failed books")
        
        # Process using existing logic
        await self.process_books_from_file("../output/retry_urls.txt")

def main():
    """Main entry point with argument parsing"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Streamlined book processor using existing opret_bøger logic')
    parser.add_argument('--input-file', help='Input file with book URLs')
    parser.add_argument('--retry-failed', action='store_true', help='Retry previously failed books')
    parser.add_argument('--validate-config', action='store_true', help='Validate configuration')
    
    args = parser.parse_args()
    
    wrapper = BookProcessorWrapper()
    wrapper.setup_logging()
    
    if args.validate_config:
        # Validate existing environment variables
        required_vars = ["POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", 
                        "OPENAI_API_KEY", "PROVIDER", "CHUNK_SIZE"]
        missing = [var for var in required_vars if not os.getenv(var)]
        
        if missing:
            print(f"Missing required environment variables: {missing}")
            sys.exit(1)
        else:
            print("✅ All required environment variables are set")
            print(f"Embedding Model: {os.getenv('OPENAI_MODEL', 'default')}")
            print(f"Provider: {os.getenv('PROVIDER')}")
            print(f"Chunk Size: {os.getenv('CHUNK_SIZE')}")
            sys.exit(0)
    
    if args.retry_failed:
        asyncio.run(wrapper.retry_failed_books())
    elif args.input_file:
        asyncio.run(wrapper.process_books_from_file(args.input_file))
    else:
        print("Error: Either --input-file or --retry-failed must be specified")
        sys.exit(1)

if __name__ == "__main__":
    main()