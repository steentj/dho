"""
Book Processing Pipeline for DHO Semantic Search System.

This module implements the pipeline pattern to orchestrate book processing operations:
fetch → parse → save. It separates orchestration from individual operations,
providing a clean single-responsibility approach to book processing.

Creation date/time: 20. juli 2025, 14:30
Last Modified date/time: 20. juli 2025, 14:30
"""

import logging
from typing import Dict, Any, List
import aiohttp
import fitz  # PyMuPDF

from .book_service_interface import IBookService
from .providers import EmbeddingProvider
from .chunking import ChunkingStrategy

logger = logging.getLogger(__name__)


class BookProcessingPipeline:
    """
    Pipeline for orchestrating book processing operations.
    
    This class coordinates the fetch → parse → save workflow for book processing,
    separating orchestration concerns from individual operations.
    """
    
    @staticmethod
    def load_urls_from_file(file_path: str) -> List[str]:
        """
        Load book URLs from a file.
        
        Args:
            file_path: Path to the file containing URLs
            
        Returns:
            List of URLs to process
        """
        logger.info(f"Loading URLs from {file_path}")
        with open(file_path, "r") as file:
            urls = [line.strip() for line in file.readlines() if line.strip()]
        logger.info(f"Loaded {len(urls)} URLs to process")
        return urls
    
    def __init__(
        self, 
        book_service: IBookService,
        embedding_provider: EmbeddingProvider,
        chunking_strategy: ChunkingStrategy
    ):
        """
        Initialize the book processing pipeline.
        
        Args:
            book_service: Service for database operations
            embedding_provider: Provider for generating embeddings
            chunking_strategy: Strategy for text chunking
        """
        self.book_service = book_service
        self.embedding_provider = embedding_provider
        self.chunking_strategy = chunking_strategy
    
    async def process_book_from_url(
        self, 
        book_url: str, 
        chunk_size: int, 
        session: aiohttp.ClientSession
    ) -> None:
        """
        Process a complete book from URL to database.
        
        This is the main pipeline orchestration method that coordinates:
        1. Check if book already exists with embeddings for this provider
        2. Fetch PDF from URL
        3. Parse PDF and generate embeddings
        4. Save to database
        
        Args:
            book_url: URL of the PDF to process
            chunk_size: Maximum size for text chunks
            session: HTTP session for fetching PDFs
        """
        try:
            # Check if book already exists with embeddings for this provider
            has_embeddings = await self.book_service.book_exists_with_provider(
                book_url, 
                self.embedding_provider.get_provider_name()
            )
            
            if has_embeddings:
                logger.info(
                    f"Bogen {book_url} er allerede behandlet med "
                    f"{self.embedding_provider.get_provider_name()} provider - springer over"
                )
                return
            
            # Fetch PDF
            pdf = await self.fetch_pdf(book_url, session)
            if not pdf:
                logger.warning(f"Kunne ikke hente PDF fra {book_url}")
                return
            
            # Parse PDF and generate embeddings
            try:
                book_data = await self.parse_pdf_to_book_data(pdf, book_url, chunk_size)
                
                # Save to database
                await self.save_book_data(book_data)
                
                logger.info(
                    f"{book_data['titel']} fra {book_url} er behandlet og gemt i databasen"
                )
                
            finally:
                pdf.close()  # Ensure PDF resources are freed
                
        except Exception as e:
            logger.exception(f"Fejl ved behandling af {book_url}: {type(e).__name__}")
            raise
    
    async def fetch_pdf(self, url: str, session: aiohttp.ClientSession) -> fitz.Document:
        """
        Fetch a PDF from a URL.
        
        Args:
            url: PDF URL to fetch
            session: HTTP session for the request
            
        Returns:
            fitz.Document: The PDF document, or None if fetch failed
        """
        try:
            async with session.get(url, timeout=30) as response:
                if response.status == 200:
                    raw_pdf = await response.read()
                    return fitz.open(stream=raw_pdf, filetype="pdf")
                else:
                    logger.error(
                        f"Fejl ved hentning af {url}: Statuskode {response.status}"
                    )
                    return None
        except Exception as e:
            logger.error(f"Fejl ved hentning af {url}: {e}")
            return None
    
    async def parse_pdf_to_book_data(
        self, 
        pdf: fitz.Document, 
        book_url: str, 
        chunk_size: int
    ) -> Dict[str, Any]:
        """
        Parse PDF document into structured book data with embeddings.
        
        Args:
            pdf: PDF document to parse
            book_url: Original URL of the PDF
            chunk_size: Maximum tokens per chunk
            
        Returns:
            Dict containing book metadata, chunks, and embeddings
        """
        metadata = pdf.metadata or {}
        book = {
            "pdf-url": book_url,  # Standard key used throughout the system
            "titel": metadata.get("title", "Ukendt Titel"),
            "forfatter": metadata.get("author", "Ukendt Forfatter"),
            "sider": len(pdf),
            "chunks": [],
            "embeddings": [],
        }
        
        # Extract text from all pages
        pdf_pages = self.extract_text_by_page(pdf)
        
        # Use the chunking strategy to process the document
        for page_num, chunk_text in self.chunking_strategy.process_document(
            pdf_pages, chunk_size, book["titel"]
        ):
            book["chunks"].append((page_num, chunk_text))
            embedding = await self.embedding_provider.get_embedding(chunk_text)
            book["embeddings"].append(embedding)
        
        return book
    
    def extract_text_by_page(self, pdf: fitz.Document) -> Dict[int, str]:
        """
        Extract text from each page in the PDF.
        
        Args:
            pdf: PDF document to extract text from
            
        Returns:
            Dict mapping page numbers to their text content
        """
        pages_text = {}
        for page_num in range(len(pdf)):
            text = pdf[page_num].get_text()
            # Clean text of soft line breaks etc.
            pages_text[page_num + 1] = (
                text.replace(" \xad\n", "")
                .replace("\xad\n", "")
                .replace("-\n", "")
                .replace("- \n", "")
            )
        return pages_text
    
    async def save_book_data(self, book_data: Dict[str, Any]) -> None:
        """
        Save book data to database.
        
        Args:
            book_data: Complete book data with chunks and embeddings
        """
        # Get the provider-specific table name
        table_name = self.embedding_provider.get_table_name()
        
        # Save using the book service interface
        await self.book_service.save_book_with_chunks(book_data, table_name)
        
        logger.info(
            f"Successfully saved book {book_data['titel']} with "
            f"{len(book_data['chunks'])} chunks to {table_name} table"
        )
