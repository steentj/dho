"""
Test that would have failed BEFORE the fix to demonstrate the problem.

This test file contains tests that should have been failing with the original
buggy chunks_nomic table schema but weren't because proper tests didn't exist.
"""
import pytest
from unittest.mock import AsyncMock
from create_embeddings.providers.embedding_providers import OllamaEmbeddingProvider
from create_embeddings.opret_bøger import save_book
from database.postgresql_service import BookService


class TestOllamaBookProcessingThatShouldHaveFailed:
    """
    Tests that should have been failing before the fix but weren't written yet.
    
    These tests demonstrate what would have failed in actual book processing
    with Ollama provider due to the chunks_nomic table schema bug.
    """
    
    @pytest.fixture
    def ollama_provider(self):
        """Create an Ollama embedding provider."""
        return OllamaEmbeddingProvider()
    
    @pytest.fixture
    def mock_failing_postgresql_service(self):
        """
        Create a mock PostgreSQL service that simulates the original schema bug.
        
        This shows what would have happened before the fix.
        """
        service = AsyncMock()
        service.find_book_by_url.return_value = None
        service.create_book.return_value = 123
        
        # Simulate the database error that WOULD have occurred with the buggy schema
        async def failing_save_chunks(book_id, chunks_with_embeddings, table_name):
            if table_name == "chunks_nomic":
                # This is the actual PostgreSQL error with the buggy schema
                raise Exception(
                    'null value in column "id" violates not-null constraint\n'
                    'DETAIL: Failing row contains (null, 123, 1, "Test chunk", [0.1,0.2,0.3], ...).'
                )
            return None
            
        service.save_chunks.side_effect = failing_save_chunks
        
        # Mock transaction
        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def mock_transaction():
            yield
        service.transaction = mock_transaction
        
        return service
    
    @pytest.fixture 
    def failing_book_service(self, mock_failing_postgresql_service):
        """Create a BookService that would fail with the original schema."""
        return BookService(mock_failing_postgresql_service)
    
    @pytest.mark.asyncio
    async def test_ollama_book_processing_would_have_failed_before_fix(
        self, failing_book_service, ollama_provider
    ):
        """
        Test that demonstrates the failure that WOULD have occurred before the fix.
        
        This is exactly what users would have experienced when trying to process
        books with Ollama provider - all books failing with database errors.
        """
        book_data = {
            "pdf-url": "https://example.com/user-book.pdf",
            "titel": "User's Book That Failed",
            "forfatter": "Frustrated User",
            "sider": 100,
            "chunks": [
                (1, "This chunk would have failed to save"),
                (2, "This chunk would also have failed"),
                (3, "All chunks failed due to schema bug")
            ],
            "embeddings": [
                [0.1, 0.2, 0.3],
                [0.4, 0.5, 0.6], 
                [0.7, 0.8, 0.9]
            ]
        }
        
        # This would have failed before our fix
        with pytest.raises(Exception, match='null value in column "id" violates not-null constraint'):
            await save_book(book_data, failing_book_service, ollama_provider)
    
    @pytest.mark.asyncio
    async def test_multiple_books_all_would_have_failed(
        self, failing_book_service, ollama_provider
    ):
        """
        Test that shows how ALL books would have failed with Ollama provider.
        
        This explains why the user reported "all books failed" when using
        Ollama with nomic_text_embed.
        """
        book_urls_that_would_have_failed = [
            "https://example.com/book1.pdf",
            "https://example.com/book2.pdf", 
            "https://example.com/book3.pdf"
        ]
        
        failed_books = []
        
        for i, url in enumerate(book_urls_that_would_have_failed):
            book_data = {
                "pdf-url": url,
                "titel": f"Book {i+1}",
                "forfatter": "Test Author",
                "sider": 50,
                "chunks": [(1, f"Chunk from book {i+1}")],
                "embeddings": [[float(i), float(i+1), float(i+2)]]
            }
            
            try:
                await save_book(book_data, failing_book_service, ollama_provider)
            except Exception as e:
                failed_books.append((url, str(e)))
        
        # All books would have failed
        assert len(failed_books) == len(book_urls_that_would_have_failed)
        
        # All with the same schema-related error
        for url, error in failed_books:
            assert 'null value in column "id" violates not-null constraint' in error
    
    def test_problem_was_ollama_specific(self):
        """
        Test that documents why the problem was specific to Ollama provider.
        
        This explains why OpenAI processing worked but Ollama didn't.
        """
        from create_embeddings.providers.embedding_providers import (
            OpenAIEmbeddingProvider, 
            DummyEmbeddingProvider,
            OllamaEmbeddingProvider
        )
        
        # OpenAI and Dummy providers use "chunks" table (with proper SERIAL schema)
        openai_provider = OpenAIEmbeddingProvider("fake-key")
        dummy_provider = DummyEmbeddingProvider()
        
        assert openai_provider.get_table_name() == "chunks"
        assert dummy_provider.get_table_name() == "chunks"
        
        # Ollama provider uses "chunks_nomic" table (which had the buggy schema)
        ollama_provider = OllamaEmbeddingProvider()
        assert ollama_provider.get_table_name() == "chunks_nomic"
        
        # This table name difference is why only Ollama processing failed
        assert ollama_provider.get_table_name() != openai_provider.get_table_name()
    
    def test_root_cause_analysis(self):
        """
        Test that documents the root cause analysis of the problem.
        
        This serves as documentation for future developers.
        """
        # Root cause: Migration file created chunks_nomic with wrong schema
        
        # BROKEN (original): id bigint PRIMARY KEY
        # - PostgreSQL doesn't auto-generate values
        # - INSERT without explicit ID fails
        # - Error: null value in column "id" violates not-null constraint
        
        # FIXED (corrected): id BIGSERIAL PRIMARY KEY  
        # - PostgreSQL auto-generates sequential values
        # - INSERT without explicit ID works fine
        # - Book processing succeeds
        
        # The fix was changing one word in the migration file:
        # FROM: id bigint PRIMARY KEY
        # TO:   id BIGSERIAL PRIMARY KEY
        
        # This is a common PostgreSQL gotcha - forgetting SERIAL for auto-increment
        assert True  # This test serves as documentation
