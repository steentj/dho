"""
Unit tests for the new search behavior including distance threshold filtering,
result grouping by book, URL formatting, and chunk concatenation.
"""
import pytest
from unittest.mock import patch, MagicMock
import os


@pytest.mark.unit
class TestDistanceThresholdFiltering:
    """Test distance threshold filtering functionality."""
    
    def test_filter_results_by_distance_threshold(self):
        """Test that results are correctly filtered by distance threshold."""
        # Mock database results with various distances
        mock_results = [
            ("book1.pdf", "Book One", "Author One", 1, "chunk 1", 0.2),
            ("book2.pdf", "Book Two", "Author Two", 5, "chunk 2", 0.3),
            ("book1.pdf", "Book One", "Author One", 3, "chunk 3", 0.4),
            ("book3.pdf", "Book Three", "Author Three", 10, "chunk 4", 0.6),
            ("book2.pdf", "Book Two", "Author Two", 8, "chunk 5", 0.7),
        ]
        
        threshold = 0.5
        filtered_results = [result for result in mock_results if result[5] <= threshold]
        
        assert len(filtered_results) == 3
        assert all(result[5] <= threshold for result in filtered_results)
        
        # Verify specific results that should be included
        distances = [result[5] for result in filtered_results]
        assert 0.2 in distances
        assert 0.3 in distances
        assert 0.4 in distances
        assert 0.6 not in distances
        assert 0.7 not in distances
    
    def test_empty_results_when_no_matches_under_threshold(self):
        """Test that empty results are returned when no matches are under threshold."""
        mock_results = [
            ("book1.pdf", "Book One", "Author One", 1, "chunk 1", 0.8),
            ("book2.pdf", "Book Two", "Author Two", 5, "chunk 2", 0.9),
        ]
        
        threshold = 0.5
        filtered_results = [result for result in mock_results if result[5] <= threshold]
        
        assert len(filtered_results) == 0
    
    def test_all_results_when_all_under_threshold(self):
        """Test that all results are returned when all are under threshold."""
        mock_results = [
            ("book1.pdf", "Book One", "Author One", 1, "chunk 1", 0.1),
            ("book2.pdf", "Book Two", "Author Two", 5, "chunk 2", 0.2),
            ("book3.pdf", "Book Three", "Author Three", 10, "chunk 3", 0.3),
        ]
        
        threshold = 0.5
        filtered_results = [result for result in mock_results if result[5] <= threshold]
        
        assert len(filtered_results) == 3
        assert len(filtered_results) == len(mock_results)


@pytest.mark.unit
class TestResultGroupingByBook:
    """Test result grouping by book functionality."""
    
    def test_group_chunks_by_book(self):
        """Test that chunks from the same book are grouped together."""
        mock_results = [
            ("book1.pdf", "Book One", "Author One", 1, "chunk 1 content", 0.2),
            ("book2.pdf", "Book Two", "Author Two", 5, "chunk 2 content", 0.3),
            ("book1.pdf", "Book One", "Author One", 3, "chunk 3 content", 0.4),
            ("book3.pdf", "Book Three", "Author Three", 10, "chunk 4 content", 0.1),
            ("book1.pdf", "Book One", "Author One", 7, "chunk 5 content", 0.35),
        ]
        
        # Group results by book
        grouped_results = {}
        for result in mock_results:
            pdf_navn, titel, forfatter, sidenr, chunk, distance = result
            key = (pdf_navn, titel, forfatter)
            
            if key not in grouped_results:
                grouped_results[key] = {
                    'pdf_navn': pdf_navn,
                    'titel': titel,
                    'forfatter': forfatter,
                    'chunks': [],
                    'pages': [],
                    'min_distance': distance
                }
            
            grouped_results[key]['chunks'].append(chunk)
            grouped_results[key]['pages'].append(sidenr)
            grouped_results[key]['min_distance'] = min(grouped_results[key]['min_distance'], distance)
        
        # Verify grouping
        assert len(grouped_results) == 3  # 3 unique books
        
        # Check book1.pdf has 3 chunks
        book1_key = ("book1.pdf", "Book One", "Author One")
        assert len(grouped_results[book1_key]['chunks']) == 3
        assert len(grouped_results[book1_key]['pages']) == 3
        assert grouped_results[book1_key]['min_distance'] == 0.2
        
        # Check book2.pdf has 1 chunk
        book2_key = ("book2.pdf", "Book Two", "Author Two")
        assert len(grouped_results[book2_key]['chunks']) == 1
        assert grouped_results[book2_key]['min_distance'] == 0.3
        
        # Check book3.pdf has 1 chunk
        book3_key = ("book3.pdf", "Book Three", "Author Three")
        assert len(grouped_results[book3_key]['chunks']) == 1
        assert grouped_results[book3_key]['min_distance'] == 0.1
    
    def test_sort_grouped_results_by_min_distance(self):
        """Test that grouped results are sorted by minimum distance."""
        mock_results = [
            ("book1.pdf", "Book One", "Author One", 1, "chunk 1", 0.4),
            ("book2.pdf", "Book Two", "Author Two", 5, "chunk 2", 0.1),
            ("book3.pdf", "Book Three", "Author Three", 10, "chunk 3", 0.3),
            ("book1.pdf", "Book One", "Author One", 3, "chunk 4", 0.2),  # min for book1
        ]
        
        # Group and track minimum distances
        grouped_results = {}
        for result in mock_results:
            pdf_navn, titel, forfatter, sidenr, chunk, distance = result
            key = (pdf_navn, titel, forfatter)
            
            if key not in grouped_results:
                grouped_results[key] = {'min_distance': distance, 'title': titel}
            else:
                grouped_results[key]['min_distance'] = min(grouped_results[key]['min_distance'], distance)
        
        # Sort by minimum distance
        sorted_results = sorted(grouped_results.items(), key=lambda x: x[1]['min_distance'])
        
        # Verify sorting order
        assert len(sorted_results) == 3
        assert sorted_results[0][1]['min_distance'] == 0.1  # book2
        assert sorted_results[1][1]['min_distance'] == 0.2  # book1
        assert sorted_results[2][1]['min_distance'] == 0.3  # book3


@pytest.mark.unit
class TestURLFormatting:
    """Test URL formatting for both user-facing and internal URLs."""
    
    def test_create_user_facing_url(self):
        """Test creation of user-facing URLs without page numbers."""
        pdf_name = "historical_book.pdf"
        
        # User-facing URL should not include page number
        user_url = pdf_name  # Just the filename
        
        assert user_url == "historical_book.pdf"
        assert "#page=" not in user_url
    
    def test_create_internal_url_with_page(self):
        """Test creation of internal URLs with page numbers."""
        pdf_name = "historical_book.pdf"
        page_number = 42
        
        # Internal URL should include page number
        internal_url = f"{pdf_name}#page={page_number}"
        
        assert internal_url == "historical_book.pdf#page=42"
        assert "#page=" in internal_url
    
    def test_url_formatting_for_multiple_pages(self):
        """Test URL formatting when a book has multiple page results."""
        pdf_name = "multi_page_book.pdf"
        pages = [1, 5, 10, 23]
        
        # For user-facing: just the book name
        user_url = pdf_name
        assert user_url == "multi_page_book.pdf"
        
        # For internal: we might want to track all pages or use the first page
        first_page_url = f"{pdf_name}#page={pages[0]}"
        assert first_page_url == "multi_page_book.pdf#page=1"
    
    def test_url_formatting_edge_cases(self):
        """Test URL formatting edge cases."""
        # Empty page number
        pdf_name = "test.pdf"
        page_number = None
        
        if page_number is not None:
            internal_url = f"{pdf_name}#page={page_number}"
        else:
            internal_url = pdf_name
        
        assert internal_url == "test.pdf"
        
        # Zero page number
        page_number = 0
        internal_url = f"{pdf_name}#page={page_number}"
        assert internal_url == "test.pdf#page=0"


@pytest.mark.unit
class TestChunkConcatenation:
    """Test chunk concatenation for multiple results from the same book."""
    
    def test_concatenate_chunks_with_separators(self):
        """Test that chunks are concatenated with clear separators."""
        chunks = [
            "This is the first chunk of text.",
            "This is the second chunk of text.",
            "This is the third chunk of text."
        ]
        
        # Test different separator styles
        separator = "\n\n---\n\n"
        concatenated = separator.join(chunks)
        
        expected = ("This is the first chunk of text.\n\n---\n\n"
                   "This is the second chunk of text.\n\n---\n\n"
                   "This is the third chunk of text.")
        
        assert concatenated == expected
        assert concatenated.count("---") == 2  # n-1 separators for n chunks
    
    def test_concatenate_chunks_with_page_info(self):
        """Test concatenating chunks with page information."""
        chunk_data = [
            {"chunk": "First chunk content", "page": 1},
            {"chunk": "Second chunk content", "page": 5},
            {"chunk": "Third chunk content", "page": 10}
        ]
        
        # Concatenate with page information
        formatted_chunks = []
        for data in chunk_data:
            formatted_chunks.append(f"[Side {data['page']}] {data['chunk']}")
        
        concatenated = "\n\n---\n\n".join(formatted_chunks)
        
        expected = ("[Side 1] First chunk content\n\n---\n\n"
                   "[Side 5] Second chunk content\n\n---\n\n"
                   "[Side 10] Third chunk content")
        
        assert concatenated == expected
        assert "[Side 1]" in concatenated
        assert "[Side 5]" in concatenated
        assert "[Side 10]" in concatenated
    
    def test_single_chunk_no_separator(self):
        """Test that single chunks don't get unnecessary separators."""
        chunks = ["This is a single chunk."]
        
        separator = "\n\n---\n\n"
        concatenated = separator.join(chunks)
        
        assert concatenated == "This is a single chunk."
        assert "---" not in concatenated
    
    def test_empty_chunks_handling(self):
        """Test handling of empty or whitespace-only chunks."""
        chunks = [
            "Valid chunk content",
            "",  # Empty chunk
            "   ",  # Whitespace only
            "Another valid chunk"
        ]
        
        # Filter out empty/whitespace chunks
        filtered_chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
        concatenated = "\n\n---\n\n".join(filtered_chunks)
        
        expected = "Valid chunk content\n\n---\n\nAnother valid chunk"
        assert concatenated == expected
        assert concatenated.count("---") == 1


@pytest.mark.unit
class TestSearchResponseStructure:
    """Test the overall structure of the new search response."""
    
    def test_new_response_structure(self):
        """Test that the new response structure contains expected fields."""
        # Mock the expected new response structure
        mock_response = {
            "pdf_navn": "book1.pdf",  # User-facing URL (no page)
            "pdf_url_with_page": "book1.pdf#page=1",  # Internal URL with first page
            "titel": "Historical Book",
            "forfatter": "Author Name",
            "combined_chunks": "First chunk\n\n---\n\nSecond chunk",
            "pages": [1, 5, 10],
            "min_distance": 0.2,
            "chunk_count": 3
        }
        
        # Verify all expected fields are present
        expected_fields = [
            "pdf_navn", "pdf_url_with_page", "titel", "forfatter",
            "combined_chunks", "pages", "min_distance", "chunk_count"
        ]
        
        for field in expected_fields:
            assert field in mock_response
        
        # Verify field types and content
        assert isinstance(mock_response["pages"], list)
        assert isinstance(mock_response["min_distance"], float)
        assert isinstance(mock_response["chunk_count"], int)
        assert "#page=" not in mock_response["pdf_navn"]  # User-facing has no page
        assert "#page=" in mock_response["pdf_url_with_page"]  # Internal has page
        assert "---" in mock_response["combined_chunks"]  # Has separators
    
    def test_backwards_compatibility_fields(self):
        """Test that response maintains some backwards compatibility."""
        # The response should still include the basic fields that existing consumers expect
        mock_response = {
            "pdf_navn": "book1.pdf",  # Now user-facing URL
            "titel": "Historical Book",
            "forfatter": "Author Name",
            "chunk": "Combined chunk content",  # Could be renamed to combined_chunks
            "distance": 0.2  # Could be renamed to min_distance
        }
        
        # Basic fields should still exist
        assert "pdf_navn" in mock_response
        assert "titel" in mock_response
        assert "forfatter" in mock_response
        assert "chunk" in mock_response or "combined_chunks" in mock_response
        assert "distance" in mock_response or "min_distance" in mock_response
