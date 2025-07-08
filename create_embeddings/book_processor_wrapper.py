import asyncio
import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import logging

# Add the parent directory to the Python path for absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import ALL existing functionality from opret_bøger using absolute imports
from create_embeddings.opret_bøger import (
    indlæs_urls,
    process_book,
)
from create_embeddings.providers import EmbeddingProviderFactory
from create_embeddings.chunking import ChunkingStrategyFactory
from create_embeddings.logging_config import setup_logging

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
                                                  service, session, process_func, chunking_strategy):
        """Wrapper around existing process_book with monitoring, now with injectable chunking strategy and database service"""
        try:
            # Use provided process function or default to process_book
            if process_func:
                await process_func(book_url, chunk_size, service, session, chunking_strategy)
            else:
                # For the default case, we need an embedding provider
                # This is mainly for backward compatibility with existing calls
                await process_book(book_url, chunk_size, service, session, None, chunking_strategy)
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
    
    async def create_mock_service(self):
        """Create a mock service for testing."""
        from database.postgresql import PostgreSQLConnection
        
        class DummyConnection:
            async def __aenter__(self): return self
            async def __aexit__(self, exc_type, exc, tb): return False
            async def close(self): pass
            async def execute(self, *args, **kwargs): return None
            async def fetchone(self, *args, **kwargs): return None
            async def fetchall(self, *args, **kwargs): return []
            async def fetchval(self, *args, **kwargs): return None
            
        # Create dummy connection wrapped in PostgreSQL interface
        connection = PostgreSQLConnection(DummyConnection())
        
        # Create service that uses the dummy connection
        from database.postgresql_service import PostgreSQLService
        service = PostgreSQLService()
        service._connection = connection
        service._book_repository = service._factory.create_book_repository(connection)
        service._search_repository = service._factory.create_search_repository(connection)
        
        return service
        
    async def process_books_from_file(self, input_file: str):
        """Process books using existing opret_bøger logic with monitoring and injectable chunking strategy"""
        # Validate configuration before starting processing
        try:
            config = validate_config()
            logging.info(f"Konfiguration valideret: {config['provider']} provider, {config['chunking_strategy']} chunking")
        except ValueError as e:
            logging.error(f"Konfigurationsfejl: {e}")
            raise
        
        # Handle both test and production environments
        if os.path.exists("/app/input"):
            input_file_path = Path("/app/input") / input_file
        else:
            # For test environment, use the current directory
            input_file_path = Path(input_file)
            
        if not input_file_path.exists():
            raise FileNotFoundError(f"Inputfil ikke fundet: {input_file_path}")
            
        book_urls = indlæs_urls(str(input_file_path))
        self.total_count = len(book_urls)
        logging.info(f"Behandler {self.total_count} bøger ved hjælp af eksisterende opret_bøger logik")
        
        # Mock load_dotenv in test environment
        from dotenv import load_dotenv
        load_dotenv(override=True)
        
        # Get configuration
        api_key = os.getenv("OPENAI_API_KEY")
        provider = os.getenv("PROVIDER", "dummy")  # Default to dummy in test environment
        chunk_size = int(os.getenv("CHUNK_SIZE", "500"))
        chunking_strategy_name = os.getenv("CHUNKING_STRATEGY", "sentence_splitter")

        # Create providers
        embedding_provider = EmbeddingProviderFactory.create_provider(provider, api_key)
        chunking_strategy = ChunkingStrategyFactory.create_strategy(chunking_strategy_name)
        
        self.update_status("starter")
        import aiohttp
        import ssl
        from aiohttp import TCPConnector
        
        try:
            if os.path.exists("/app/input"):
                # Production mode - use real service
                from database.postgresql_service import create_postgresql_service
                service = await create_postgresql_service()
            else:
                # Test mode - use mock service
                service = await self.create_mock_service()
            
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
                            semaphore, url, chunk_size, service, session, embedding_provider, chunking_strategy
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
    
    async def semaphore_guard_with_monitoring(self, semaphore, url, chunk_size, service, session, embedding_provider, chunking_strategy):
        """Use existing semaphore pattern with monitoring and injectable chunking strategy"""
        async with semaphore:
            # Create a wrapper function that includes the embedding_provider and service
            async def process_with_embedding(book_url, chunk_size, service, session, chunking_strategy):
                return await process_book(book_url, chunk_size, service, session, embedding_provider, chunking_strategy)
            
            await self.process_single_book_with_monitoring(
                url, chunk_size, service, session, process_with_embedding, chunking_strategy
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

def validate_config():
    """Omfattende konfigurationsvalidering"""
    # Base påkrævede variabler
    required_vars = ["POSTGRES_HOST", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"]
    
    # Provider-specifik validering
    provider = os.getenv("PROVIDER", "ollama")
    print(f"Validerer konfiguration for PROVIDER={provider}")
    if provider == "openai":
        required_vars.extend(["OPENAI_API_KEY"])
    elif provider == "ollama":
        required_vars.extend(["OLLAMA_BASE_URL", "OLLAMA_MODEL"])
    elif provider != "dummy":
        raise ValueError(f"Ukendt PROVIDER: {provider}. Skal være en af: openai, ollama, dummy")
    
    # Validér chunking strategy
    chunking_strategy = os.getenv("CHUNKING_STRATEGY", "sentence_splitter")
    valid_strategies = ["sentence_splitter", "word_overlap"]
    if chunking_strategy not in valid_strategies:
        raise ValueError(f"Ugyldig CHUNKING_STRATEGY: {chunking_strategy}. Skal være en af: {valid_strategies}")
    
    # Validér CHUNK_SIZE
    chunk_size = os.getenv("CHUNK_SIZE", "500")
    try:
        chunk_size_int = int(chunk_size)
        if chunk_size_int <= 0:
            raise ValueError("CHUNK_SIZE skal være et positivt tal")
    except ValueError as e:
        if "invalid literal" in str(e):
            raise ValueError(f"CHUNK_SIZE skal være et tal, ikke '{chunk_size}'")
        raise
    
    # Validér LOG_LEVEL hvis sat
    log_level = os.getenv("LOG_LEVEL")
    if log_level:
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if log_level.upper() not in valid_log_levels:
            raise ValueError(f"Ugyldig LOG_LEVEL: {log_level}. Skal være en af: {valid_log_levels}")
    
    # Tjek for manglende variabler
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise ValueError(f"Manglende påkrævede miljøvariabler: {missing}")
    
    # Cross-validation: Tjek at provider-specifikke variabler matcher valgt provider
    cross_validation_warnings = []
    
    # Tjek for OpenAI variabler når provider ikke er OpenAI
    if provider != "openai":
        openai_vars = ["OPENAI_API_KEY", "OPENAI_MODEL"]
        set_openai_vars = [var for var in openai_vars if os.getenv(var)]
        if set_openai_vars:
            cross_validation_warnings.append(
                f"OpenAI variabler {set_openai_vars} er sat, men PROVIDER={provider}. "
                f"Disse variabler vil blive ignoreret."
            )
    
    # Tjek for Ollama variabler når provider ikke er Ollama
    if provider != "ollama":
        ollama_vars = ["OLLAMA_BASE_URL", "OLLAMA_MODEL"]
        set_ollama_vars = [var for var in ollama_vars if os.getenv(var)]
        if set_ollama_vars:
            cross_validation_warnings.append(
                f"Ollama variabler {set_ollama_vars} er sat, men PROVIDER={provider}. "
                f"Disse variabler vil blive ignoreret."
            )
    
    # Tjek for manglende provider-specifikke variabler i relation til satte variabler
    if provider == "dummy":
        # Hvis dummy provider er valgt, men andre provider vars er sat, advar
        all_provider_vars = ["OPENAI_API_KEY", "OPENAI_MODEL", "OLLAMA_BASE_URL", "OLLAMA_MODEL"]
        set_provider_vars = [var for var in all_provider_vars if os.getenv(var)]
        if set_provider_vars:
            cross_validation_warnings.append(
                f"Provider variabler {set_provider_vars} er sat, men PROVIDER=dummy. "
                f"Overej at ændre PROVIDER til 'openai' eller 'ollama' for at bruge disse konfigurationer."
            )
    
    # Log cross-validation warnings
    if cross_validation_warnings:
        import logging
        for warning in cross_validation_warnings:
            logging.warning(f"Cross-validation advarsel: {warning}")
    
    # Returner valideret konfiguration for debugging
    return {
        "provider": provider,
        "chunking_strategy": chunking_strategy,
        "chunk_size": chunk_size_int,
        "log_level": log_level,
        "required_vars_present": len(required_vars) - len(missing)
    }

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
        try:
            config = validate_config()
            print("✅ Alle påkrævede miljøvariabler er sat og gyldige")
            print(f"Udbyder: {config['provider']}")
            print(f"Chunking Strategy: {config['chunking_strategy']}")
            print(f"Chunk Størrelse: {config['chunk_size']}")
            if config['log_level']:
                print(f"Log Level: {config['log_level']}")
            if config['provider'] == 'openai':
                print(f"OpenAI Model: {os.getenv('OPENAI_MODEL', 'text-embedding-3-small')}")
            elif config['provider'] == 'ollama':
                print(f"Ollama URL: {os.getenv('OLLAMA_BASE_URL')}")
                print(f"Ollama Model: {os.getenv('OLLAMA_MODEL')}")
            sys.exit(0)
        except ValueError as e:
            print(f"❌ Konfigurationsfejl: {e}")
            sys.exit(1)
    
    if args.retry_failed:
        asyncio.run(wrapper.retry_failed_books())
    elif args.input_file:
        asyncio.run(wrapper.process_books_from_file(args.input_file))
    else:
        print("Fejl: Enten --input-file eller --retry-failed skal angives")
        sys.exit(1)

if __name__ == "__main__":
    main()
