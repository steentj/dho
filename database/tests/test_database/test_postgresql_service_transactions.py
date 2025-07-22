"""
Unit tests for PostgreSQL service transaction management and provider-aware operations.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from database.postgresql_service import PostgreSQLService


@pytest.mark.unit
class TestPostgreSQLServiceTransactions:
    """Test PostgreSQL service transaction management."""
    
    @pytest.fixture
    def service_with_mocks(self):
        """Create a service with all necessary mocks."""
        service = PostgreSQLService()
        mock_connection = AsyncMock()
        mock_book_repo = AsyncMock()
        mock_search_repo = AsyncMock()
        
        service._connection = mock_connection
        service._book_repository = mock_book_repo
        service._search_repository = mock_search_repo
        
        return service, mock_connection, mock_book_repo, mock_search_repo
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_transaction_context_manager(self, service_with_mocks):
        """Test transaction context manager correctly delegates to connection."""
        service, mock_connection, _, _ = service_with_mocks
        
        # Setup mock transaction
        mock_connection.transaction = MagicMock()
        mock_connection.transaction.return_value.__aenter__ = AsyncMock()
        mock_connection.transaction.return_value.__aexit__ = AsyncMock()
        
        # Use transaction context manager
        async with service.transaction():
            # Do something in transaction
            pass
        
        # Verify transaction was created and managed
        mock_connection.transaction.assert_called_once()
        mock_connection.transaction.return_value.__aenter__.assert_called_once()
        mock_connection.transaction.return_value.__aexit__.assert_called_once()
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_transaction_context_manager_error_handling(self, service_with_mocks):
        """Test transaction context manager handles errors correctly."""
        service, mock_connection, _, _ = service_with_mocks
        
        # Setup mock transaction
        mock_connection.transaction = MagicMock()
        mock_connection.transaction.return_value.__aenter__ = AsyncMock()
        mock_connection.transaction.return_value.__aexit__ = AsyncMock(return_value=False)  # Return False to let exceptions propagate
        
        # Define test error
        test_error = RuntimeError("Test error")
        
        # Use transaction context manager with exception
        try:
            async with service.transaction():
                raise test_error
            pytest.fail("Exception should have been raised")
        except RuntimeError as e:
            assert str(e) == "Test error"
        
        # Verify transaction was created and managed with error
        mock_connection.transaction.assert_called_once()
        mock_connection.transaction.return_value.__aenter__.assert_called_once()
        # Verify __aexit__ was called with the exception details
        args, _ = mock_connection.transaction.return_value.__aexit__.call_args
        assert args[0] is RuntimeError  # Exception type
        assert str(args[1]) == "Test error"  # Exception instance
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_transaction_context_manager_not_connected(self):
        """Test transaction context manager fails when not connected."""
        service = PostgreSQLService()
        
        # Should raise exception when not connected
        with pytest.raises(RuntimeError, match="PostgreSQL service is not connected"):
            async with service.transaction():
                pass


@pytest.mark.unit
class TestPostgreSQLServiceProviderAware:
    """Test provider-aware operations in PostgreSQL service."""
    
    @pytest.fixture
    def service_with_mocks(self):
        """Create a service with all necessary mocks."""
        service = PostgreSQLService()
        mock_connection = AsyncMock()
        mock_book_repo = AsyncMock()
        mock_search_repo = AsyncMock()
        
        service._connection = mock_connection
        service._book_repository = mock_book_repo
        service._search_repository = mock_search_repo
        
        return service, mock_connection, mock_book_repo, mock_search_repo
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_vector_search_provider_selection_openai(self, service_with_mocks):
        """Test vector search uses the correct table for OpenAI provider."""
        service, _, _, mock_search_repo = service_with_mocks
        embedding = [0.1, 0.2, 0.3]
        
        await service.vector_search(embedding, provider_name="openai")
        
        # Verify search repository was called with correct parameters
        mock_search_repo.vector_search.assert_called_once_with(
            embedding, 10, "cosine", "normal", "openai"
        )
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_vector_search_provider_selection_ollama(self, service_with_mocks):
        """Test vector search uses the correct table for Ollama provider."""
        service, _, _, mock_search_repo = service_with_mocks
        embedding = [0.1, 0.2, 0.3]
        
        await service.vector_search(embedding, provider_name="ollama")
        
        # Verify search repository was called with correct parameters
        mock_search_repo.vector_search.assert_called_once_with(
            embedding, 10, "cosine", "normal", "ollama"
        )
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_vector_search_provider_selection_dummy(self, service_with_mocks):
        """Test vector search uses the correct table for dummy provider."""
        service, _, _, mock_search_repo = service_with_mocks
        embedding = [0.1, 0.2, 0.3]
        
        await service.vector_search(embedding, provider_name="dummy")
        
        # Verify search repository was called with correct parameters
        mock_search_repo.vector_search.assert_called_once_with(
            embedding, 10, "cosine", "normal", "dummy"
        )
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_vector_search_custom_parameters(self, service_with_mocks):
        """Test vector search with custom parameters."""
        service, _, _, mock_search_repo = service_with_mocks
        embedding = [0.1, 0.2, 0.3]
        
        await service.vector_search(
            embedding, 
            limit=5, 
            distance_function="l2", 
            chunk_size="large",
            provider_name="openai"
        )
        
        # Verify search repository was called with correct parameters
        mock_search_repo.vector_search.assert_called_once_with(
            embedding, 5, "l2", "large", "openai"
        )


@pytest.mark.unit
class TestPostgreSQLServiceChunksOperations:
    """Test PostgreSQL service operations for chunks and embeddings."""
    
    @pytest.fixture
    def service_with_mocks(self):
        """Create a service with all necessary mocks."""
        service = PostgreSQLService()
        mock_connection = AsyncMock()
        mock_book_repo = AsyncMock()
        mock_search_repo = AsyncMock()
        
        service._connection = mock_connection
        service._book_repository = mock_book_repo
        service._search_repository = mock_search_repo
        
        return service, mock_connection, mock_book_repo, mock_search_repo
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_save_chunks_proper_delegation(self, service_with_mocks):
        """Test save_chunks correctly delegates to book repository."""
        service, _, mock_book_repo, _ = service_with_mocks
        
        book_id = 123
        chunks = [(1, "Test chunk", [0.1, 0.2, 0.3])]
        
        await service.save_chunks(book_id, chunks)
        
        # Verify repository method was called correctly
        mock_book_repo.save_chunks.assert_called_once_with(book_id, chunks, "chunks")
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_save_chunks_custom_table(self, service_with_mocks):
        """Test save_chunks with custom table name."""
        service, _, mock_book_repo, _ = service_with_mocks
        
        book_id = 123
        chunks = [(1, "Test chunk", [0.1, 0.2, 0.3])]
        
        await service.save_chunks(book_id, chunks, "chunks_ollama")
        
        # Verify repository method was called with custom table
        mock_book_repo.save_chunks.assert_called_once_with(book_id, chunks, "chunks_ollama")
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_save_chunks_not_connected(self):
        """Test save_chunks fails when not connected."""
        service = PostgreSQLService()
        
        book_id = 123
        chunks = [(1, "Test chunk", [0.1, 0.2, 0.3])]
        
        # Should raise exception when not connected
        with pytest.raises(RuntimeError, match="PostgreSQL service is not connected"):
            await service.save_chunks(book_id, chunks)
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_save_book_with_chunks_integration(self, service_with_mocks):
        """Test save_book_with_chunks integrates find/create and save_chunks correctly."""
        service, _, mock_book_repo, _ = service_with_mocks
        
        # Setup mocks
        mock_book_repo.find_book_by_url.return_value = None  # Book doesn't exist
        mock_book_repo.create_book.return_value = 456  # New book ID
        
        # Test data
        book_data = {
            "pdf_url": "test.pdf",
            "titel": "Test Book",  # Using the correct key as in the service
            "forfatter": "Test Author",  # Using the correct key as in the service
            "sider": 10,  # Using the correct key as in the service
            "chunks": [(1, "Test chunk")],  # Page number and text
            "embeddings": [[0.1, 0.2, 0.3]]  # Embeddings for chunks
        }
        
        # Call method
        result = await service.save_book_with_chunks(book_data, "chunks_test")
        
        # Verify
        assert result == 456
        mock_book_repo.find_book_by_url.assert_called_once_with("test.pdf")
        mock_book_repo.create_book.assert_called_once_with(
            pdf_url="test.pdf",
            title="Test Book",
            author="Test Author",
            pages=10
        )
        
        # Verify save_chunks was called with correctly formatted data
        expected_chunks = [(1, "Test chunk", [0.1, 0.2, 0.3])]
        mock_book_repo.save_chunks.assert_called_once_with(456, expected_chunks, "chunks_test")
    
    @pytest.mark.asyncio
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    async def test_save_book_with_chunks_existing_book(self, service_with_mocks):
        """Test save_book_with_chunks with existing book."""
        service, _, mock_book_repo, _ = service_with_mocks
        
        # Setup mocks
        mock_book_repo.find_book_by_url.return_value = 123  # Book exists
        
        # Test data
        book_data = {
            "pdf_url": "test.pdf",
            "title": "Test Book",
            "author": "Test Author",
            "pages": 10,
            "chunks": [(1, "Test chunk")],
            "embeddings": [[0.1, 0.2, 0.3]]
        }
        
        # Call method
        result = await service.save_book_with_chunks(book_data, "chunks_test")
        
        # Verify
        assert result == 123
        mock_book_repo.find_book_by_url.assert_called_once_with("test.pdf")
        mock_book_repo.create_book.assert_not_called()
        
        # Verify save_chunks was called with correctly formatted data
        expected_chunks = [(1, "Test chunk", [0.1, 0.2, 0.3])]
        mock_book_repo.save_chunks.assert_called_once_with(123, expected_chunks, "chunks_test")
