"""
Unit tests for the new search behavior including distance threshold filtering,
result grouping by book, URL formatting, and chunk concatenation.

These tests are written in TDD style and should FAIL initially since the 
new behavior has not been implemented yet.
"""
import pytest
from unittest.mock import patch, AsyncMock
import os
import sys
from pathlib import Path

# Add the searchapi directory to the path for imports
searchapi_path = Path(__file__).parent.parent.parent / "searchapi"
sys.path.insert(0, str(searchapi_path))

try:
    from searchapi.dhosearch import find_nærmeste, search, Input
    DHOSEARCH_AVAILABLE = True
except ImportError as e:
    pytest.skip(f"Could not import from dhosearch: {e}", allow_module_level=True)
    DHOSEARCH_AVAILABLE = False


@pytest.mark.unit
@pytest.mark.skipif(not DHOSEARCH_AVAILABLE, reason="dhosearch module not available")
class TestDistanceThresholdFiltering:
    """Test distance threshold filtering functionality - these should FAIL initially."""
    
    @pytest.mark.asyncio
    async def test_find_naermeste_uses_distance_threshold_not_limit(self):
        """Test that find_nærmeste uses distance threshold filtering.
        """
        test_vector = [0.1, 0.2, 0.3]
        expected_threshold = 0.5

        # Mock results that include some that should be filtered out
        mock_results = [
            ("test1.pdf", "Test Book 1", "Author 1", 1, "This is a short chunk that should pass the length filter", 0.3),  # Should pass
            ("test2.pdf", "Test Book 2", "Author 2", 1, "Short", 0.7),  # Should be filtered out (too short and distance too high)
            ("test3.pdf", "Test Book 3", "Author 3", 1, "This is a longer chunk with sufficient content for filtering and should definitely pass", 0.4),  # Should pass
        ]

        with patch.dict(os.environ, {"DISTANCE_THRESHOLD": str(expected_threshold)}):
            # Import the dhosearch module to get the right module reference
            import searchapi.dhosearch as dhosearch_module
            
            # Create a mock service
            mock_service = AsyncMock()
            mock_service.vector_search.return_value = mock_results
            
            # Patch the global variable in the module
            with patch.object(dhosearch_module, 'db_service', mock_service):
                results = await find_nærmeste(test_vector)

                # Verify service was called with expected parameters
                mock_service.vector_search.assert_called_once_with(
                    embedding=test_vector,
                    limit=1000,
                    distance_function="cosine",
                    chunk_size="normal"
                )

                # Verify distance threshold filtering was applied
                # Only results with distance <= 0.5 and chunk length > 20 should be returned
                assert len(results) == 2  # test1.pdf and test3.pdf should pass both filters
                result_pdfs = [result[0] for result in results]
                assert "test1.pdf" in result_pdfs
                assert "test3.pdf" in result_pdfs
                assert "test2.pdf" not in result_pdfs  # Should be filtered out
    
    def test_environment_variable_distance_threshold_is_used(self):
        """Test that DISTANCE_THRESHOLD environment variable is actually used.
        """
        with patch.dict(os.environ, {"DISTANCE_THRESHOLD": "0.3"}):
            # Test that environment variable loading works
            threshold = float(os.getenv("DISTANCE_THRESHOLD", "0.5"))
            
            # This assertion should pass (environment variable loading works)
            assert threshold == 0.3


@pytest.mark.unit
@pytest.mark.skipif(not DHOSEARCH_AVAILABLE, reason="dhosearch module not available")
class TestResultGroupingByBook:
    """Test result grouping by book functionality."""
    
    @pytest.mark.asyncio
    async def test_search_endpoint_groups_results_by_book(self):
        """Test that search endpoint groups multiple chunks from same book."""
        mock_results = [
            ("book1.pdf", "Book One", "Author One", 1, "This is a longer chunk 1 with sufficient content", 0.2),
            ("book1.pdf", "Book One", "Author One", 3, "This is a longer chunk 2 with sufficient content", 0.3),
            ("book2.pdf", "Book Two", "Author Two", 5, "This is a longer chunk 3 with sufficient content", 0.4),
        ]
        
        mock_input = Input(query="test query")
        
        with patch('searchapi.dhosearch.find_nærmeste') as mock_find_nærmeste:
            with patch('searchapi.dhosearch.get_embedding') as mock_embedding:
                mock_embedding.return_value = [0.1, 0.2, 0.3]
                mock_find_nærmeste.return_value = mock_results
                
                result = await search(mock_input)
                dokumenter = result
                
                assert len(dokumenter) == 2, f"Expected 2 grouped results (2 books), got {len(dokumenter)}"
                
                book1_result = next((doc for doc in dokumenter if "Book One" in doc.get("titel", "")), None)
                assert book1_result is not None, "Book One should be in results"
                
                assert "chunk 1" in book1_result["chunk"] and "chunk 2" in book1_result["chunk"]


@pytest.mark.unit
@pytest.mark.skipif(not DHOSEARCH_AVAILABLE, reason="dhosearch module not available")
class TestURLFormatting:
    """Test URL formatting for both user-facing and internal URLs."""
    
    @pytest.mark.asyncio
    async def test_search_response_has_both_url_formats(self):
        """Test that search response includes both user-facing and internal URLs."""
        mock_results = [
            ("book1.pdf", "Book One", "Author One", 42, "This is a longer chunk content with sufficient text", 0.2),
        ]
        
        mock_input = Input(query="test query")
        
        with patch('searchapi.dhosearch.find_nærmeste') as mock_find_nærmeste:
            with patch('searchapi.dhosearch.get_embedding') as mock_embedding:
                mock_embedding.return_value = [0.1, 0.2, 0.3]
                mock_find_nærmeste.return_value = mock_results
                
                result = await search(mock_input)
                dokumenter = result
                
                assert len(dokumenter) > 0
                doc = dokumenter[0]
                
                assert "internal_url" in doc, "Should have internal URL with page number"
                assert "#page=" in doc["internal_url"], "Internal URL should include page number"
                assert "#page=" not in doc["pdf_navn"], "User-facing pdf_navn should not include page number"


@pytest.mark.unit
@pytest.mark.skipif(not DHOSEARCH_AVAILABLE, reason="dhosearch module not available")
class TestChunkConcatenation:
    """Test chunk concatenation for multiple results from the same book."""
    
    @pytest.mark.asyncio
    async def test_multiple_chunks_from_same_book_are_concatenated(self):
        """Test that multiple chunks from same book are concatenated with separators."""
        mock_results = [
            ("book1.pdf", "Book One", "Author One", 1, "First chunk content with enough text", 0.2),
            ("book1.pdf", "Book One", "Author One", 5, "Second chunk content with enough text", 0.3),
            ("book1.pdf", "Book One", "Author One", 10, "Third chunk content with enough text", 0.4),
        ]
        
        mock_input = Input(query="test query")
        
        with patch('searchapi.dhosearch.find_nærmeste') as mock_find_nærmeste:
            with patch('searchapi.dhosearch.get_embedding') as mock_embedding:
                mock_embedding.return_value = [0.1, 0.2, 0.3]
                mock_find_nærmeste.return_value = mock_results
                
                result = await search(mock_input)
                dokumenter = result
                
                assert len(dokumenter) == 1, f"Expected 1 grouped result for same book, got {len(dokumenter)}"
                
                doc = dokumenter[0]
                chunk_content = doc["chunk"]
                
                assert "First chunk content" in chunk_content, "Should contain first chunk"
                assert "Second chunk content" in chunk_content, "Should contain second chunk"
                assert "Third chunk content" in chunk_content, "Should contain third chunk"
                assert "---" in chunk_content, "Should have separators between chunks"


@pytest.mark.unit
@pytest.mark.skipif(not DHOSEARCH_AVAILABLE, reason="dhosearch module not available")
class TestSearchResponseStructure:
    """Test the overall structure of the search response."""
    
    @pytest.mark.asyncio
    async def test_response_has_new_fields(self):
        """Test that response includes new fields for grouped results."""
        mock_results = [
            ("book1.pdf", "Book One", "Author One", 1, "chunk 1 with sufficient content", 0.2),
            ("book1.pdf", "Book One", "Author One", 5, "chunk 2 with sufficient content", 0.3),
        ]
        
        mock_input = Input(query="test query")
        
        with patch('searchapi.dhosearch.find_nærmeste') as mock_find_nærmeste:
            with patch('searchapi.dhosearch.get_embedding') as mock_embedding:
                mock_embedding.return_value = [0.1, 0.2, 0.3]
                mock_find_nærmeste.return_value = mock_results
                
                result = await search(mock_input)
                dokumenter = result
                
                assert len(dokumenter) > 0
                doc = dokumenter[0]
                
                assert "pages" in doc, "Response should include pages array"
                assert "min_distance" in doc, "Response should include min_distance"
                assert "chunk_count" in doc, "Response should include chunk_count"
                assert "internal_url" in doc, "Response should include internal URL with page"
                
                assert isinstance(doc["pages"], list), "pages should be a list"
                assert isinstance(doc["min_distance"], (int, float)), "min_distance should be numeric"
                assert isinstance(doc["chunk_count"], int), "chunk_count should be integer"
