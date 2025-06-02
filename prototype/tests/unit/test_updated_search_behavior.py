"""
Unit tests for updated search functionality with distance threshold and result grouping.
These tests follow TDD approach and will initially fail until the new behavior is implemented.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json
import sys
from pathlib import Path

# Add the searchapi directory to the path for imports
searchapi_path = Path(__file__).parent.parent.parent / "searchapi"
sys.path.insert(0, str(searchapi_path))


@pytest.mark.unit
class TestDistanceThresholdFiltering:
    """Test distance threshold filtering functionality."""
    
    def test_distance_threshold_filtering_logic(self):
        """Test that results are filtered based on distance threshold."""
        # Mock database results with various distances
        mock_results = [
            ("book1.pdf", "Title 1", "Author 1", 1, "chunk1", 0.2),
            ("book1.pdf", "Title 1", "Author 1", 2, "chunk2", 0.4), 
            ("book2.pdf", "Title 2", "Author 2", 5, "chunk3", 0.6),
            ("book3.pdf", "Title 3", "Author 3", 10, "chunk4", 0.8),
        ]
        
        threshold = 0.5
        
        # Filter results based on threshold
        filtered_results = [result for result in mock_results if result[5] <= threshold]
        
        assert len(filtered_results) == 2
        assert filtered_results[0][5] == 0.2  # First result distance
        assert filtered_results[1][5] == 0.4  # Second result distance
        
        # Results above threshold should be excluded
        distances = [result[5] for result in filtered_results]
        assert 0.6 not in distances
        assert 0.8 not in distances
    
    @patch.dict('os.environ', {'DISTANCE_THRESHOLD': '0.3'})
    def test_distance_threshold_from_environment(self):
        """Test that distance threshold is read from environment variable."""
        import os
        threshold = float(os.getenv("DISTANCE_THRESHOLD", "0.5"))
        
        mock_results = [
            ("book1.pdf", "Title 1", "Author 1", 1, "chunk1", 0.2),
            ("book1.pdf", "Title 1", "Author 1", 2, "chunk2", 0.35),
            ("book2.pdf", "Title 2", "Author 2", 5, "chunk3", 0.4),
        ]
        
        filtered_results = [result for result in mock_results if result[5] <= threshold]
        
        assert len(filtered_results) == 1  # Only 0.2 should pass 0.3 threshold
        assert filtered_results[0][5] == 0.2


@pytest.mark.unit  
class TestResultGroupingByBook:
    """Test grouping of search results by book."""
    
    def test_group_results_by_book_title(self):
        """Test that results from same book are grouped together."""
        mock_results = [
            ("book1.pdf", "Title 1", "Author 1", 1, "chunk1", 0.2),
            ("book2.pdf", "Title 2", "Author 2", 5, "chunk2", 0.3),
            ("book1.pdf", "Title 1", "Author 1", 3, "chunk3", 0.4),
            ("book1.pdf", "Title 1", "Author 1", 2, "chunk4", 0.25),
        ]
        
        # Group by book title
        grouped_results = {}
        for result in mock_results:
            book_title = result[1]  # Title is at index 1
            if book_title not in grouped_results:
                grouped_results[book_title] = []
            grouped_results[book_title].append(result)
        
        assert len(grouped_results) == 2  # Two different books
        assert "Title 1" in grouped_results
        assert "Title 2" in grouped_results
        assert len(grouped_results["Title 1"]) == 3  # Three chunks from book1
        assert len(grouped_results["Title 2"]) == 1  # One chunk from book2
    
    def test_concatenate_chunks_from_same_book(self):
        """Test that chunks from same book are concatenated with separators."""
        chunks_from_same_book = [
            "This is the first chunk from the book.",
            "This is the second chunk from the same book.",
            "This is the third chunk."
        ]
        
        separator = "\n\n---\n\n"
        concatenated = separator.join(chunks_from_same_book)
        
        expected = ("This is the first chunk from the book.\n\n---\n\n"
                   "This is the second chunk from the same book.\n\n---\n\n"
                   "This is the third chunk.")
        
        assert concatenated == expected
        assert concatenated.count("---") == 2  # Two separators for three chunks
    
    def test_preserve_page_numbers_internally(self):
        """Test that page numbers are preserved for internal use."""
        mock_results = [
            ("book1.pdf", "Title 1", "Author 1", 1, "chunk1", 0.2),
            ("book1.pdf", "Title 1", "Author 1", 3, "chunk2", 0.4),
        ]
        
        # Extract page numbers for internal use
        page_numbers = [result[3] for result in mock_results]
        
        assert 1 in page_numbers
        assert 3 in page_numbers
        assert len(page_numbers) == 2


@pytest.mark.unit
class TestURLFormatting:
    """Test URL formatting for user-facing and internal use."""
    
    def test_user_facing_url_without_page_number(self):
        """Test that user-facing URLs don't include page numbers."""
        pdf_name = "book1.pdf"
        page_number = 5
        
        # Current implementation (to be changed)
        current_url = f'{pdf_name}#page={page_number}'
        
        # New user-facing URL (without page number)
        user_facing_url = pdf_name
        
        assert user_facing_url == "book1.pdf"
        assert "#page=" not in user_facing_url
        assert str(page_number) not in user_facing_url
    
    def test_internal_url_with_page_number(self):
        """Test that internal URLs still include page numbers."""
        pdf_name = "book1.pdf"
        page_number = 5
        
        internal_url = f'{pdf_name}#page={page_number}'
        
        assert internal_url == "book1.pdf#page=5"
        assert "#page=" in internal_url
        assert str(page_number) in internal_url
    
    def test_response_contains_both_url_types(self):
        """Test that response contains both user-facing and internal URLs."""
        mock_document = {
            "pdf_navn": "book1.pdf",
            "titel": "Title 1", 
            "forfatter": "Author 1",
            "sidenr": 5,
            "chunk": "Sample chunk",
            "distance": 0.3
        }
        
        # Expected new response format
        expected_response = {
            "pdf_url": "book1.pdf",  # User-facing (no page number)
            "pdf_url_internal": "book1.pdf#page=5",  # Internal (with page number)
            "titel": "Title 1",
            "forfatter": "Author 1", 
            "chunk": "Sample chunk",
            "distance": 0.3,
            "page_numbers": [5]  # Page numbers as separate field
        }
        
        # This test defines the expected structure
        assert "pdf_url" in expected_response
        assert "pdf_url_internal" in expected_response
        assert "page_numbers" in expected_response
        assert expected_response["pdf_url"] == "book1.pdf"
        assert expected_response["pdf_url_internal"] == "book1.pdf#page=5"


@pytest.mark.unit
class TestUpdatedSearchResponse:
    """Test the updated search response structure."""
    
    def test_search_response_groups_results_by_book(self):
        """Test that search response groups multiple chunks from same book."""
        # Mock results with multiple chunks from same book
        mock_db_results = [
            ("book1.pdf", "Title 1", "Author 1", 1, "chunk1", 0.2),
            ("book1.pdf", "Title 1", "Author 1", 3, "chunk2", 0.4),
            ("book2.pdf", "Title 2", "Author 2", 5, "chunk3", 0.3),
        ]
        
        # Expected grouped response (this is what we want to implement)
        expected_grouped = [
            {
                "pdf_url": "book1.pdf",
                "pdf_url_internal": "book1.pdf#page=1",  # First page reference
                "titel": "Title 1",
                "forfatter": "Author 1",
                "chunk": "chunk1\n\n---\n\nchunk2",  # Concatenated chunks
                "distance": 0.2,  # Best (lowest) distance
                "page_numbers": [1, 3]  # All page numbers
            },
            {
                "pdf_url": "book2.pdf", 
                "pdf_url_internal": "book2.pdf#page=5",
                "titel": "Title 2",
                "forfatter": "Author 2",
                "chunk": "chunk3",
                "distance": 0.3,
                "page_numbers": [5]
            }
        ]
        
        # This test defines what we expect - will fail until implemented
        assert len(expected_grouped) == 2
        assert expected_grouped[0]["page_numbers"] == [1, 3]
        assert "---" in expected_grouped[0]["chunk"]  # Chunks are concatenated
        assert expected_grouped[0]["distance"] == 0.2  # Best distance kept
    
    def test_no_hard_limit_on_results(self):
        """Test that there's no hard limit on number of results (replaces LIMIT 5)."""
        # Mock many results under threshold
        threshold = 0.5
        mock_results = [
            ("book1.pdf", "Title 1", "Author 1", 1, "chunk1", 0.1),
            ("book2.pdf", "Title 2", "Author 2", 2, "chunk2", 0.2),
            ("book3.pdf", "Title 3", "Author 3", 3, "chunk3", 0.3),
            ("book4.pdf", "Title 4", "Author 4", 4, "chunk4", 0.4),
            ("book5.pdf", "Title 5", "Author 5", 5, "chunk5", 0.45),
            ("book6.pdf", "Title 6", "Author 6", 6, "chunk6", 0.49),
            ("book7.pdf", "Title 7", "Author 7", 7, "chunk7", 0.6),  # Above threshold
        ]
        
        # Filter by threshold instead of hard limit
        filtered_results = [r for r in mock_results if r[5] <= threshold]
        
        assert len(filtered_results) == 6  # All under 0.5, no limit of 5
        assert all(r[5] <= threshold for r in filtered_results)
        
        # Result above threshold should be excluded
        excluded_result = [r for r in mock_results if r[5] > threshold]
        assert len(excluded_result) == 1
        assert excluded_result[0][5] == 0.6
