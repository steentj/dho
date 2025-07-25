"""
Book Processing Orchestrator for DHO Semantic Search System.

This module implements the orchestration layer that coordinates the complete
book processing workflow, including dependency injection setup, resource
management, and concurrent processing coordination.

Creation date/time: 20. juli 2025, 15:45
Last Modified date/time: 20. juli 2025, 15:45
"""

import asyncio
import aiohttp
import ssl
import logging
from typing import List
from aiohttp import TCPConnector

from .book_processing_pipeline import BookProcessingPipeline
from .providers import EmbeddingProvider, EmbeddingProviderFactory
from .chunking import ChunkingStrategy, ChunkingStrategyFactory
from database.postgresql_service import create_postgresql_pool_service

logger = logging.getLogger(__name__)


class BookProcessingOrchestrator:
    """
    Orchestrates the complete book processing workflow.
    
    This class is responsible for:
    - Setting up all dependencies (database, providers, strategies)
    - Managing resources (HTTP sessions, database connections)
    - Coordinating concurrent processing of multiple books
    """
    
    def __init__(
        self, 
        database_url: str,
        provider_name: str,
        api_key: str,
        chunking_strategy_name: str,
        chunk_size: int,
        concurrency_limit: int = 5
    ):
        """
        Initialize the book processing orchestrator.
        
        Args:
            database_url: Database connection URL
            provider_name: Embedding provider name (openai, ollama, dummy)
            api_key: API key for the embedding provider
            chunking_strategy_name: Chunking strategy name
            chunk_size: Maximum tokens per chunk
            concurrency_limit: Maximum concurrent processing tasks
        """
        self.database_url = database_url
        self.provider_name = provider_name
        self.api_key = api_key
        self.chunking_strategy_name = chunking_strategy_name
        self.chunk_size = chunk_size
        self.concurrency_limit = concurrency_limit
        
        # Dependencies - initialized during setup
        self.embedding_provider: EmbeddingProvider = None
        self.chunking_strategy: ChunkingStrategy = None
        self.book_service = None
        
    async def setup_dependencies(self) -> None:
        """Initialize all dependencies using factories."""
        try:
            # Initialize embedding provider
            self.embedding_provider = EmbeddingProviderFactory.create_provider(
                self.provider_name, 
                self.api_key
            )
            logger.info(f"Initialized embedding provider: {self.provider_name}")
            
            # Initialize chunking strategy
            self.chunking_strategy = ChunkingStrategyFactory.create_strategy(
                self.chunking_strategy_name
            )
            logger.info(f"Initialized chunking strategy: {self.chunking_strategy_name}")
            
            # Initialize database service using pool service (preferred for concurrent processing)
            self.book_service = await create_postgresql_pool_service()
            logger.info("Database connection pool created")
            
        except Exception as e:
            logger.exception(f"Failed to setup dependencies: {type(e).__name__}")
            raise
    
    async def cleanup_resources(self) -> None:
        """Clean up all resources."""
        try:
            if self.book_service:
                await self.book_service.disconnect()
                logger.info("Database connection pool closed")
        except Exception as e:
            logger.exception(f"Error during cleanup: {type(e).__name__}")
    
    async def process_books_from_urls(self, book_urls: List[str]) -> None:
        """
        Process multiple books from URLs with controlled concurrency.
        
        Args:
            book_urls: List of PDF URLs to process
        """
        if not book_urls:
            logger.warning("No book URLs provided")
            return
            
        logger.info(f"Starting processing of {len(book_urls)} books with concurrency limit {self.concurrency_limit}")
        
        # Create HTTP session with SSL configuration
        ssl_context = ssl.create_default_context()
        
        async with aiohttp.ClientSession(
            connector=TCPConnector(ssl=ssl_context)
        ) as session:
            # Create semaphore for controlling concurrency
            semaphore = asyncio.Semaphore(self.concurrency_limit)
            
            # Create processing tasks
            tasks = [
                asyncio.create_task(
                    self._process_book_with_semaphore(
                        semaphore, url, session
                    )
                )
                for url in book_urls
            ]
            
            # Execute all tasks and collect results (including exceptions)
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log summary
            successful = sum(1 for result in results if not isinstance(result, Exception))
            failed = len(results) - successful
            
            logger.info(
                f"Processing completed: {successful} successful, {failed} failed out of {len(book_urls)} total"
            )
    
    async def _process_book_with_semaphore(
        self, 
        semaphore: asyncio.Semaphore, 
        book_url: str, 
        session: aiohttp.ClientSession
    ) -> None:
        """
        Process a single book with semaphore guard for concurrency control.
        
        Args:
            semaphore: Semaphore for controlling concurrent access
            book_url: URL of the book to process
            session: HTTP session for requests
        """
        async with semaphore:
            try:
                # Create pipeline for this book
                pipeline = BookProcessingPipeline(
                    book_service=self.book_service,
                    embedding_provider=self.embedding_provider,
                    chunking_strategy=self.chunking_strategy
                )
                
                # Process the book
                await pipeline.process_book_from_url(
                    book_url, 
                    self.chunk_size, 
                    session
                )
                
            except Exception as e:
                logger.exception(f"Failed to process book {book_url}: {type(e).__name__}")
                raise


class BookProcessingApplication:
    """
    Application layer for book processing.
    
    This class handles the high-level application workflow:
    - Configuration loading and validation
    - URL file reading
    - Orchestrator setup and execution
    """
    

    
    @staticmethod
    async def run_book_processing(
        database_url: str,
        provider_name: str,
        api_key: str,
        chunking_strategy_name: str,
        chunk_size: int,
        url_file_path: str,
        concurrency_limit: int = 5
    ) -> None:
        """
        Run the complete book processing application.
        
        This is the main application entry point that coordinates the entire workflow.
        
        Args:
            database_url: Database connection URL
            provider_name: Embedding provider name
            api_key: API key for embedding provider
            chunking_strategy_name: Chunking strategy name
            chunk_size: Maximum tokens per chunk
            url_file_path: Path to file containing book URLs
            concurrency_limit: Maximum concurrent processing tasks
        """
        orchestrator = None
        
        try:
            # Load book URLs using BookProcessingPipeline static method
            book_urls = BookProcessingPipeline.load_urls_from_file(url_file_path)
            
            if not book_urls:
                logger.warning("No URLs to process")
                return
            
            # Create and setup orchestrator
            orchestrator = BookProcessingOrchestrator(
                database_url=database_url,
                provider_name=provider_name,
                api_key=api_key,
                chunking_strategy_name=chunking_strategy_name,
                chunk_size=chunk_size,
                concurrency_limit=concurrency_limit
            )
            
            # Setup all dependencies
            await orchestrator.setup_dependencies()
            
            # Process all books
            await orchestrator.process_books_from_urls(book_urls)
            
            logger.info("Book processing application completed successfully")
            
        except Exception as e:
            logger.exception(f"Book processing application failed: {type(e).__name__}")
            raise
            
        finally:
            # Ensure cleanup always happens
            if orchestrator:
                await orchestrator.cleanup_resources()
