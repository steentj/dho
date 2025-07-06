"""
Test for the Ollama database table issue.

This test reproduces the issue where the chunks_nomic table has
id bigint PRIMARY KEY instead of id BIGSERIAL PRIMARY KEY,
causing INSERT failures when saving chunks.
"""
import pytest
from unittest.mock import AsyncMock
from create_embeddings.providers.embedding_providers import OllamaEmbeddingProvider
from create_embeddings.opret_bøger import save_book
from database.postgresql_service import BookService


@pytest.mark.integration 
class TestOllamaDatabaseIssue:
    """Test the Ollama database table schema issue."""
    
    @pytest.fixture
    def ollama_provider(self):
        """Create an Ollama embedding provider."""
        return OllamaEmbeddingProvider(
            base_url="http://localhost:11434",
            model="nomic-embed-text"
        )
    
    @pytest.fixture
    def mock_postgresql_service(self):
        """Create a mock PostgreSQL service that simulates the database issue."""
        service = AsyncMock()
        
        # Mock successful book operations
        service.find_book_by_url.return_value = None
        service.create_book.return_value = 123
        
        # Mock the save_chunks method to simulate the database error
        # that occurs when trying to INSERT without providing an ID
        # into a table with id bigint PRIMARY KEY (not SERIAL)
        async def failing_save_chunks(book_id, chunks_with_embeddings, table_name):
            if table_name == "chunks_nomic":
                # Simulate the PostgreSQL error when ID is not provided
                # for a bigint PRIMARY KEY column without DEFAULT
                raise Exception(
                    'null value in column "id" violates not-null constraint'
                )
            # Other tables work fine
            return None
            
        service.save_chunks.side_effect = failing_save_chunks
        
        # Mock transaction context manager
        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def mock_transaction():
            yield
        service.transaction = mock_transaction
        
        return service
    
    @pytest.fixture
    def book_service(self, mock_postgresql_service):
        """Create a BookService with mocked PostgreSQL service."""
        return BookService(mock_postgresql_service)
    
    @pytest.mark.asyncio
    async def test_ollama_chunks_nomic_table_id_issue(self, book_service, ollama_provider):
        """
        Test that saving to chunks_nomic table fails due to ID column issue.
        
        This test reproduces the actual problem: the chunks_nomic table has
        'id bigint PRIMARY KEY' instead of 'id BIGSERIAL PRIMARY KEY',
        so PostgreSQL doesn't auto-generate IDs, causing INSERT failures.
        """
        book_data = {
            "pdf-url": "https://example.com/test-book.pdf",
            "titel": "Test Book",
            "forfatter": "Test Author",
            "sider": 10,
            "chunks": [(1, "Test chunk for Ollama")],
            "embeddings": [[0.1, 0.2, 0.3]]
        }
        
        # This should fail because chunks_nomic table has the wrong ID column definition
        with pytest.raises(Exception, match='null value in column "id" violates not-null constraint'):
            await save_book(book_data, book_service, ollama_provider)
    
    @pytest.mark.asyncio 
    async def test_openai_chunks_table_works_fine(self, book_service):
        """
        Test that saving to chunks table (OpenAI) works fine.
        
        This shows that the issue is specific to chunks_nomic table,
        not a general problem with the save_book function.
        """
        from create_embeddings.providers.embedding_providers import DummyEmbeddingProvider
        
        # Use dummy provider that uses "chunks" table (like OpenAI)
        dummy_provider = DummyEmbeddingProvider()
        
        book_data = {
            "pdf-url": "https://example.com/test-book.pdf", 
            "titel": "Test Book",
            "forfatter": "Test Author",
            "sider": 10,
            "chunks": [(1, "Test chunk for OpenAI/Dummy")],
            "embeddings": [[0.1, 0.2, 0.3]]
        }
        
        # This should work fine because chunks table has proper SERIAL ID
        await save_book(book_data, book_service, dummy_provider)
        
        # Verify it was called with the right table
        book_service._service.save_chunks.assert_called_once()
        call_args = book_service._service.save_chunks.call_args
        assert call_args[0][2] == "chunks"  # table_name
    
    @pytest.mark.asyncio
    async def test_table_name_mapping_is_correct(self, ollama_provider):
        """
        Test that OllamaEmbeddingProvider correctly maps to chunks_nomic table.
        
        This confirms the provider is correctly configured to use the problematic table.
        """
        assert ollama_provider.get_table_name() == "chunks_nomic"
        assert ollama_provider.get_provider_name() == "ollama"

    @pytest.mark.asyncio
    async def test_simulated_database_fix_validation(self, book_service):
        """
        Test how the fix should work - chunks_nomic table with proper BIGSERIAL.
        
        This test simulates what should happen after fixing the table schema.
        """
        from create_embeddings.providers.embedding_providers import OllamaEmbeddingProvider
        
        # Create a working mock that simulates the fixed table
        service = book_service._service
        
        # Reset the side_effect to make save_chunks work for all tables
        async def working_save_chunks(book_id, chunks_with_embeddings, table_name):
            # After fix, all tables should work
            return None
            
        service.save_chunks.side_effect = working_save_chunks
        
        ollama_provider = OllamaEmbeddingProvider()
        
        book_data = {
            "pdf-url": "https://example.com/fixed-test-book.pdf",
            "titel": "Fixed Test Book", 
            "forfatter": "Test Author",
            "sider": 10,
            "chunks": [(1, "Test chunk after fix")],
            "embeddings": [[0.1, 0.2, 0.3]]
        }
        
        # After fix, this should work without raising an exception
        await save_book(book_data, book_service, ollama_provider)
        
        # Verify it was saved to the correct table
        service.save_chunks.assert_called()
        call_args = service.save_chunks.call_args
        assert call_args[0][2] == "chunks_nomic"  # table_name
