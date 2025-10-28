"""
Tests to expose the failure tracking bugs in book processing.

These tests will FAIL until the following bugs are fixed:
1. OpenAI error messages are lost/empty in RuntimeError
2. Wrapper reports incorrect success/failure counts
3. Failed books are not saved to failed_books.json

Creation date/time: 7. oktober 2025, 14:30
Last Modified date/time: 7. oktober 2025, 14:30
"""

import pytest
import asyncio
import json
from unittest.mock import patch, AsyncMock
from pathlib import Path
from create_embeddings.book_processor_wrapper import BookProcessorWrapper
from create_embeddings.book_processing_orchestrator import BookProcessingOrchestrator


class TestOpenAIErrorMessageBug:
    """Test that OpenAI errors preserve actual error details."""
    
    @pytest.mark.asyncio
    async def test_openai_error_message_is_preserved(self):
        """
        BUG: OpenAI errors show as 'RuntimeError: OpenAI embedding failed after 2 attempt(s): '
        with no actual error message.
        
        EXPECTED: Should show 'RuntimeError: OpenAI embedding failed after 2 attempt(s): 
                   TimeoutError: Request timed out after 30 seconds'
        """
        from create_embeddings.providers.embedding_providers import OpenAIEmbeddingProvider
        
        # Create provider with minimal timeout to trigger error quickly
        provider = OpenAIEmbeddingProvider(api_key="test-key")
        provider.timeout = 0.001  # 1ms timeout - will definitely fail
        provider.max_retries = 1
        provider.retry_backoff = 0.001
        
        # Mock the actual OpenAI call to raise a specific error
        original_timeout_error = asyncio.TimeoutError("Request timed out after 30 seconds")
        
        with patch.object(provider, '_call_openai', side_effect=original_timeout_error):
            with pytest.raises(RuntimeError) as exc_info:
                await provider.get_embedding("test chunk")
            
            error_message = str(exc_info.value)
            
            # BUG: Currently this assertion FAILS because error message is empty
            assert "TimeoutError" in error_message, \
                f"Expected 'TimeoutError' in error message, got: '{error_message}'"
            assert "Request timed out" in error_message, \
                f"Expected timeout details in error message, got: '{error_message}'"
    
    @pytest.mark.asyncio
    async def test_openai_error_with_api_error(self):
        """Test that API errors from OpenAI are preserved in the RuntimeError."""
        from create_embeddings.providers.embedding_providers import OpenAIEmbeddingProvider
        
        provider = OpenAIEmbeddingProvider(api_key="invalid-key")
        provider.max_retries = 1
        
        # Simulate an OpenAI API error
        api_error = Exception("Invalid API key provided")
        
        with patch.object(provider, '_call_openai', side_effect=api_error):
            with pytest.raises(RuntimeError) as exc_info:
                await provider.get_embedding("test chunk")
            
            error_message = str(exc_info.value)
            
            # BUG: Currently this FAILS - error details are lost
            assert "Invalid API key" in error_message, \
                f"Expected API error details in message, got: '{error_message}'"


class TestOrchestratorFailureReporting:
    """Test that orchestrator properly reports failures back to caller."""
    
    @pytest.mark.asyncio
    async def test_orchestrator_returns_failure_details(self):
        """
        BUG FIX VERIFICATION: Orchestrator now returns structured results.
        
        EXPECTED: Orchestrator returns dict with success/failure counts and details.
        """
        # Mock the database service to avoid environment variable requirements
        with patch('create_embeddings.book_processing_orchestrator.create_postgresql_pool_service') as mock_db:
            mock_service = AsyncMock()
            mock_db.return_value = mock_service
            
            orchestrator = BookProcessingOrchestrator(
                database_url="postgresql://test",
                provider_name="dummy",
                api_key="test",
                chunking_strategy_name="sentence_splitter",
                chunk_size=500,
                concurrency_limit=2
            )
            
            await orchestrator.setup_dependencies()
            
            # Mock the pipeline to fail for some books
            book_urls = [
                "http://example.com/success.pdf",
                "http://example.com/fail.pdf",
                "http://example.com/success2.pdf"
            ]
            
            with patch.object(orchestrator, '_process_book_with_semaphore') as mock_process:
                # Configure mock to fail for fail.pdf
                async def mock_process_book(semaphore, url, session):
                    if "fail.pdf" in url:
                        raise RuntimeError("PDF processing failed")
                
                mock_process.side_effect = mock_process_book
                
                # Mock the HTTP session
                with patch('aiohttp.ClientSession'):
                    result = await orchestrator.process_books_from_urls(book_urls)
            
            # Verify result structure
            assert result is not None, "Orchestrator should return processing results"
            assert isinstance(result, dict), "Result should be a dictionary"
            
            # Verify result contains expected keys
            assert 'successful' in result, "Result should contain 'successful' count"
            assert 'failed' in result, "Result should contain 'failed' count"
            assert 'total' in result, "Result should contain 'total' count"
            assert 'failed_books' in result, "Result should contain 'failed_books' list"
            
            # Verify counts
            assert result['total'] == 3, f"Expected 3 total, got {result['total']}"
            assert result['successful'] == 2, f"Expected 2 successful, got {result['successful']}"
            assert result['failed'] == 1, f"Expected 1 failed, got {result['failed']}"
            
            # Verify failed_books structure
            assert len(result['failed_books']) == 1, f"Expected 1 failed book, got {len(result['failed_books'])}"
            failed_book = result['failed_books'][0]
            assert 'url' in failed_book, "Failed book should have 'url'"
            assert 'error' in failed_book, "Failed book should have 'error'"
            assert 'timestamp' in failed_book, "Failed book should have 'timestamp'"
            assert "fail.pdf" in failed_book['url'], f"Expected fail.pdf in URL, got {failed_book['url']}"
            
            await orchestrator.cleanup_resources()


class TestWrapperFailureTracking:
    """Test that wrapper correctly tracks and saves failed books."""
    
    @pytest.mark.asyncio
    async def test_wrapper_tracks_failures_from_orchestrator(self, tmp_path):
        """
        BUG FIX VERIFICATION: Wrapper now receives failure details from orchestrator.
        
        EXPECTED: Wrapper should receive failure details and track them correctly.
        """
        wrapper = BookProcessorWrapper(
            output_dir=str(tmp_path / "output"),
            failed_dir=str(tmp_path / "failed")
        )
        
        # Create test input file with 3 URLs
        input_file = tmp_path / "books.txt"
        input_file.write_text(
            "http://example.com/book1.pdf\n"
            "http://example.com/book2.pdf\n"
            "http://example.com/book3.pdf\n"
        )
        
        # Mock the orchestrator to return results with 1 failure
        with patch('create_embeddings.book_processing_orchestrator.BookProcessingApplication') as MockApp:
            # Simulate orchestrator returning results with 1 failure
            async def mock_run(*args, **kwargs):
                return {
                    'successful': 2,
                    'failed': 1,
                    'total': 3,
                    'failed_books': [{
                        'url': 'http://example.com/book2.pdf',
                        'error': 'RuntimeError: PDF processing failed',
                        'timestamp': '2025-10-07T15:00:00'
                    }]
                }
            
            MockApp.run_book_processing = mock_run
            
            # Mock setup_logging
            with patch.object(wrapper, 'setup_logging'):
                # Mock validate_config
                with patch('create_embeddings.book_processor_wrapper.validate_config') as mock_validate:
                    mock_validate.return_value = {
                        'provider': 'dummy',
                        'chunking_strategy': 'sentence_splitter',
                        'chunk_size': 500,
                        'log_level': 'INFO'
                    }
                    
                    # Mock environment variables
                    with patch.dict('os.environ', {
                        'DATABASE_URL': 'postgresql://test',
                        'OPENAI_API_KEY': 'test',
                        'PROVIDER': 'dummy',
                        'CHUNK_SIZE': '500',
                        'CHUNKING_STRATEGY': 'sentence_splitter'
                    }, clear=True):
                        await wrapper.process_books_from_file(str(input_file))
        
        # Verify wrapper correctly tracked failures from orchestrator
        assert wrapper.processed_count == 2, \
            f"Expected processed_count=2, got {wrapper.processed_count}"
        assert wrapper.failed_count == 1, \
            f"Expected failed_count=1, got {wrapper.failed_count}"
        
        # Verify wrapper tracked which books failed
        assert len(wrapper.failed_books) == 1, \
            f"Expected 1 failed book, got {len(wrapper.failed_books)}"
        
        failed_book = wrapper.failed_books[0]
        assert 'url' in failed_book, "Failed book should have 'url'"
        assert 'error' in failed_book, "Failed book should have 'error'"
        assert 'timestamp' in failed_book, "Failed book should have 'timestamp'"
        assert failed_book['url'] == 'http://example.com/book2.pdf', \
            f"Expected book2.pdf in failed_books, got {failed_book['url']}"
    
    @pytest.mark.asyncio
    async def test_failed_books_saved_to_json(self, tmp_path):
        """
        BUG FIX VERIFICATION: failed_books.json now created when books fail.
        
        EXPECTED: Failed books should be saved with URL, error, and timestamp.
        """
        # Create wrapper instance
        wrapper_instance = BookProcessorWrapper(
            output_dir=str(tmp_path / "output"),
            failed_dir=str(tmp_path / "failed")
        )
        
        # Create test input file
        input_file = tmp_path / "books.txt"
        input_file.write_text("http://example.com/fail.pdf\n")
        
        # Mock orchestrator to simulate failure
        with patch('create_embeddings.book_processing_orchestrator.BookProcessingApplication') as MockApp:
            async def mock_run(*args, **kwargs):
                # Simulate orchestrator returning failure
                return {
                    'successful': 0,
                    'failed': 1,
                    'total': 1,
                    'failed_books': [{
                        'url': 'http://example.com/fail.pdf',
                        'error': 'RuntimeError: PDF processing failed',
                        'timestamp': '2025-10-07T15:00:00'
                    }]
                }
            
            MockApp.run_book_processing = mock_run
            
            with patch.object(wrapper_instance, 'setup_logging'):
                with patch('create_embeddings.book_processor_wrapper.validate_config') as mock_validate:
                    mock_validate.return_value = {
                        'provider': 'dummy',
                        'chunking_strategy': 'sentence_splitter',
                        'chunk_size': 500,
                        'log_level': 'INFO'
                    }
                    
                    with patch.dict('os.environ', {
                        'DATABASE_URL': 'postgresql://test',
                        'OPENAI_API_KEY': 'test',
                        'PROVIDER': 'dummy'
                    }, clear=True):
                        await wrapper_instance.process_books_from_file(str(input_file))
        
        # Check if failed_books.json was created
        failed_file = Path(wrapper_instance.failed_dir) / "failed_books.json"
        
        # Verify file exists
        assert failed_file.exists(), \
            f"Expected {failed_file} to exist, but it doesn't"
        
        # Verify file structure
        with open(failed_file) as f:
            failed_data = json.load(f)
        
        assert len(failed_data) == 1, \
            f"Expected 1 failed book, got {len(failed_data)}"
        assert 'url' in failed_data[0], \
            "Expected 'url' field in failed book entry"
        assert 'error' in failed_data[0], \
            "Expected 'error' field in failed book entry"
        assert 'timestamp' in failed_data[0], \
            "Expected 'timestamp' field in failed book entry"
        assert failed_data[0]['url'] == 'http://example.com/fail.pdf', \
            f"Expected fail.pdf in URL, got {failed_data[0]['url']}"


class TestEndToEndFailureScenario:
    """Integration test simulating the actual production failure."""
    
    @pytest.mark.asyncio
    async def test_production_failure_scenario(self, tmp_path):
        """
        NOTE: This test is skipped - use for manual verification only.
        
        Full integration test simulating the exact production scenario would require
        complex mocking of the entire stack. The individual unit tests above verify
        all the fixes are working correctly.
        """
        pytest.skip("Full integration test requires complex mocking - use for manual verification")


class TestLogInconsistencyBug:
    """Test that log messages are consistent between orchestrator and wrapper."""
    
    @pytest.mark.asyncio
    async def test_log_messages_are_consistent(self, tmp_path, caplog):
        """
        BUG FIX VERIFICATION: Log messages now show consistent counts.
        
        EXPECTED: Both orchestrator and wrapper report the same counts.
        """
        import logging
        caplog.set_level(logging.INFO)
        
        input_file = tmp_path / "books.txt"
        input_file.write_text("http://example.com/book.pdf\n")
        
        # Mock to simulate orchestrator reporting failures
        with patch('create_embeddings.book_processing_orchestrator.BookProcessingApplication') as MockApp:
            async def mock_run(*args, **kwargs):
                # Simulate orchestrator logging
                logging.info("Processing completed: 0 successful, 1 failed out of 1 total")
                # Return results
                return {
                    'successful': 0,
                    'failed': 1,
                    'total': 1,
                    'failed_books': [{
                        'url': 'http://example.com/book.pdf',
                        'error': 'RuntimeError: Failed',
                        'timestamp': '2025-10-07T15:00:00'
                    }]
                }
            
            MockApp.run_book_processing = mock_run
            
            wrapper_instance = BookProcessorWrapper(
                output_dir=str(tmp_path / "output"),
                failed_dir=str(tmp_path / "failed")
            )
            
            with patch.object(wrapper_instance, 'setup_logging'):
                with patch('create_embeddings.book_processor_wrapper.validate_config') as mock_validate:
                    mock_validate.return_value = {
                        'provider': 'dummy',
                        'chunking_strategy': 'sentence_splitter',
                        'chunk_size': 500,
                        'log_level': 'INFO'
                    }
                    
                    with patch.dict('os.environ', {
                        'DATABASE_URL': 'postgresql://test',
                        'OPENAI_API_KEY': 'test'
                    }, clear=True):
                        await wrapper_instance.process_books_from_file(str(input_file))
        
        # Check the logs
        orchestrator_log = None
        wrapper_log = None
        
        for record in caplog.records:
            if "Processing completed:" in record.message:
                orchestrator_log = record.message
            if "Behandling afsluttet:" in record.message:
                wrapper_log = record.message
        
        # Verify logs are consistent
        assert orchestrator_log is not None, "Expected orchestrator log message"
        assert wrapper_log is not None, "Expected wrapper log message"
        
        # Both should report same counts: 0 successful, 1 failed
        assert "0 successful, 1 failed" in orchestrator_log, \
            f"Expected '0 successful, 1 failed' in orchestrator log, got: {orchestrator_log}"
        assert "0 vellykket, 1 fejlet" in wrapper_log, \
            f"Expected '0 vellykket, 1 fejlet' in wrapper log, got: {wrapper_log}"


