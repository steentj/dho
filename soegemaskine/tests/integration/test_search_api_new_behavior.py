"""
Integration tests for the updated search API response with new behavior.

These tests are written in TDD style and should FAIL initially since the 
new behavior has not been implemented yet. They test the full end-to-end
behavior of the search API.
"""
import pytest
import os
from unittest.mock import patch
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add the searchapi directory to the path for imports
searchapi_path = Path(__file__).parent.parent.parent / "searchapi"
sys.path.insert(0, str(searchapi_path))

try:
    from searchapi.dhosearch import app
    FASTAPI_AVAILABLE = True
except ImportError as e:
    pytest.skip(f"Could not import FastAPI app: {e}", allow_module_level=True)
    FASTAPI_AVAILABLE = False

    
    def test_search_api_returns_empty_when_no_results_under_threshold(self):
        """Test that API returns empty results when no matches are under threshold.
        """
        # All results above threshold
        mock_results = [
            ("book1.pdf", "Book One", "Author One", 1, "chunk 1", 0.8),
            ("book2.pdf", "Book Two", "Author Two", 2, "chunk 2", 0.9),
        ]
        
        with patch.dict(os.environ, {"DISTANCE_THRESHOLD": "0.5"}):
            with patch('searchapi.dhosearch.find_nærmeste') as mock_find:
                with patch('searchapi.dhosearch.get_embedding') as mock_embedding:
                    mock_find.return_value = mock_results
                    mock_embedding.return_value = [0.1, 0.2, 0.3]
                    
                    client = TestClient(app)
                    response = client.post("/search", json={"query": "test query"})
                    
                    assert response.status_code == 200
                    results = response.json()
                    
                    assert len(results) == 0, f"Expected 0 results when all distances > threshold, got {len(results)}"


@pytest.mark.integration
@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI app not available")
class TestSearchAPIIntegrationResultGrouping:
    """Integration tests for result grouping by book"""
    
    def test_search_api_groups_multiple_chunks_from_same_book(self):
        """Test that API groups multiple chunks from the same book into one result.
        
        This test should FAIL because current API returns separate results for each chunk.
        """
        # Multiple chunks from same books
        mock_results = [
            ("book1.pdf", "Historical Events", "John Doe", 1, "First chunk about events", 0.1),
            ("book1.pdf", "Historical Events", "John Doe", 5, "Second chunk about events", 0.2),
            ("book1.pdf", "Historical Events", "John Doe", 10, "Third chunk about events", 0.3),
            ("book2.pdf", "War Stories", "Jane Smith", 3, "War chunk one", 0.15),
            ("book2.pdf", "War Stories", "Jane Smith", 8, "War chunk two", 0.25),
        ]
        
        with patch.dict(os.environ, {"DISTANCE_THRESHOLD": "0.5"}):
            with patch('searchapi.dhosearch.find_nærmeste') as mock_find:
                with patch('searchapi.dhosearch.get_embedding') as mock_embedding:
                    mock_find.return_value = mock_results
                    mock_embedding.return_value = [0.1, 0.2, 0.3]
                    
                    client = TestClient(app)
                    response = client.post("/search", json={"query": "historical events"})
                    
                    assert response.status_code == 200
                    results = response.json()
                    
                    # Current implementation returns 5 separate results
                    # New implementation should return 2 grouped results (2 unique books)
                    # This assertion should FAIL
                    assert len(results) == 2, f"Expected 2 grouped results (2 books), got {len(results)}"
                    
                    # Find the grouped result for book1
                    book1_result = next((r for r in results if "Historical Events" in r.get("titel", "")), None)
                    assert book1_result is not None, "Should have grouped result for Historical Events"
                    
                    # Check that chunks are combined (this should FAIL)
                    chunk_content = book1_result.get("chunk", book1_result.get("combined_chunks", ""))
                    assert "First chunk about events" in chunk_content, "Should contain first chunk"
                    assert "Second chunk about events" in chunk_content, "Should contain second chunk" 
                    assert "Third chunk about events" in chunk_content, "Should contain third chunk"
    
    def test_search_api_includes_page_information_for_grouped_results(self):
        """Test that grouped results include page information.
        """
        mock_results = [
            ("manual.pdf", "User Manual", "Tech Writer", 12, "Setup instructions", 0.1),
            ("manual.pdf", "User Manual", "Tech Writer", 45, "Configuration details", 0.2),
            ("manual.pdf", "User Manual", "Tech Writer", 67, "Troubleshooting guide", 0.3),
        ]
        
        with patch.dict(os.environ, {"DISTANCE_THRESHOLD": "0.5"}):
            with patch('searchapi.dhosearch.find_nærmeste') as mock_find:
                with patch('searchapi.dhosearch.get_embedding') as mock_embedding:
                    mock_find.return_value = mock_results
                    mock_embedding.return_value = [0.1, 0.2, 0.3]
                    
                    client = TestClient(app)
                    response = client.post("/search", json={"query": "manual"})
                    
                    assert response.status_code == 200
                    results = response.json()
                    
                    # Should have 1 grouped result
                    assert len(results) == 1, f"Expected 1 grouped result, got {len(results)}"
                    
                    result = results[0]
                    
                    # These fields should NOT exist in current implementation
                    # So these assertions should FAIL
                    assert "pages" in result, "Result should include pages array"
                    assert isinstance(result["pages"], list), "pages should be a list"
                    assert 12 in result["pages"], "Should include page 12"
                    assert 45 in result["pages"], "Should include page 45" 
                    assert 67 in result["pages"], "Should include page 67"


@pytest.mark.integration
@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI app not available")
class TestSearchAPIIntegrationURLFormatting:
    """Integration tests for URL formatting"""
    
    def test_search_api_provides_separate_user_and_internal_urls(self):
        """Test that API provides both user-facing and internal URLs.
        """
        mock_results = [
            ("document.pdf", "Important Document", "Author", 42, "Document content", 0.1),
        ]

        with patch.dict(os.environ, {"DISTANCE_THRESHOLD": "0.5"}):
            with patch('searchapi.dhosearch.find_nærmeste') as mock_find:
                with patch('searchapi.dhosearch.get_embedding') as mock_embedding:
                    with patch('searchapi.dhosearch.lifespan') as mock_lifespan:
                        mock_lifespan.return_value.__aenter__.return_value = None
                        mock_lifespan.return_value.__aexit__.return_value = None
                    mock_find.return_value = mock_results
                    mock_embedding.return_value = [0.1, 0.2, 0.3]
                    
                    client = TestClient(app)
                    response = client.post("/search", json={"query": "document"})
                    
                    assert response.status_code == 200
                    results = response.json()
                    
                    assert len(results) > 0
                    result = results[0]
                    
                    # Check both URL formats are present
                    assert "pdf_navn" in result, "Should have user-facing URL"
                    assert "internal_url" in result, "Should have internal URL"
                    assert "#page=42" in result["internal_url"], "Internal URL should include page number"
                    assert "#page=" not in result["pdf_navn"], "User-facing URL should not include page number"
                    
                    # Current pdf_navn includes page number, new implementation should not
                    # This assertion should FAIL
                    assert "#page=" not in result["pdf_navn"], "User-facing pdf_navn should not include page number"
                    assert result["pdf_navn"] == "document.pdf", "User-facing URL should be clean filename"
    
    def test_search_api_user_facing_urls_consistent_across_grouped_results(self):
        """Test that user-facing URLs are consistent when grouping results from same book.
        
        This test should FAIL because current implementation doesn't group results.
        """        
        mock_results = [
            ("report.pdf", "Annual Report", "Company", 5, "Financial data", 0.1),
            ("report.pdf", "Annual Report", "Company", 12, "Market analysis", 0.2),
            ("report.pdf", "Annual Report", "Company", 28, "Future outlook", 0.3),
        ]

        with patch.dict(os.environ, {"DISTANCE_THRESHOLD": "0.5"}):
            with patch('searchapi.dhosearch.find_nærmeste') as mock_find:
                with patch('searchapi.dhosearch.get_embedding') as mock_embedding:
                    with patch('searchapi.dhosearch.lifespan') as mock_lifespan:
                        mock_lifespan.return_value.__aenter__.return_value = None
                        mock_lifespan.return_value.__aexit__.return_value = None
                        mock_find.return_value = mock_results
                        mock_embedding.return_value = [0.1, 0.2, 0.3]
                    
                    client = TestClient(app)
                    response = client.post("/search", json={"query": "report"})
                    
                    assert response.status_code == 200
                    results = response.json()
                    
                    # Should be grouped into 1 result
                    # This assertion should FAIL because current implementation doesn't group
                    assert len(results) == 1, f"Expected 1 grouped result, got {len(results)}"
                    
                    result = results[0]
                    assert result["pdf_navn"] == "report.pdf", "User-facing URL should be clean"
                    assert "#page=" not in result["pdf_navn"], "User-facing URL should not have page fragment"


@pytest.mark.integration
@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI app not available")
class TestSearchAPIIntegrationChunkConcatenation:
    """Integration tests for chunk concatenation - these should FAIL initially."""
    
    def test_search_api_concatenates_chunks_with_separators(self):
        """Test that API concatenates chunks from same book with clear separators.
        
        This test should FAIL because current API returns individual chunks.
        """
        mock_results = [
            ("guide.pdf", "Travel Guide", "Author", 10, "Introduction to the city", 0.1),
            ("guide.pdf", "Travel Guide", "Author", 25, "Best restaurants to visit", 0.2),
            ("guide.pdf", "Travel Guide", "Author", 40, "Transportation options", 0.3),
        ]
        
        with patch.dict(os.environ, {"DISTANCE_THRESHOLD": "0.5"}):
            with patch('searchapi.dhosearch.find_nærmeste') as mock_find:
                with patch('searchapi.dhosearch.get_embedding') as mock_embedding:
                    mock_find.return_value = mock_results
                    mock_embedding.return_value = [0.1, 0.2, 0.3]
                    
                    client = TestClient(app)
                    response = client.post("/search", json={"query": "travel guide"})
                    
                    assert response.status_code == 200
                    results = response.json()
                    
                    # Should be grouped into 1 result
                    assert len(results) == 1, f"Expected 1 grouped result, got {len(results)}"
                    
                    result = results[0]
                    chunk_content = result.get("chunk", result.get("combined_chunks", ""))
                    
                    # These assertions should FAIL because chunks aren't concatenated in current implementation
                    assert "Introduction to the city" in chunk_content, "Should contain first chunk"
                    assert "Best restaurants to visit" in chunk_content, "Should contain second chunk"
                    assert "Transportation options" in chunk_content, "Should contain third chunk"
                    assert "---" in chunk_content, "Should have separators between chunks"
                    
                    # Verify proper separation
                    separator_count = chunk_content.count("---")
                    assert separator_count == 2, f"Should have 2 separators for 3 chunks, got {separator_count}"
    
    def test_search_api_includes_page_info_in_concatenated_chunks(self):
        """Test that concatenated chunks include page information.
        """
        mock_results = [
            ("manual.pdf", "Software Manual", "Dev Team", 15, "Installation steps", 0.1),
            ("manual.pdf", "Software Manual", "Dev Team", 32, "Configuration settings", 0.2),
        ]
        
        with patch.dict(os.environ, {"DISTANCE_THRESHOLD": "0.5"}):
            with patch('searchapi.dhosearch.find_nærmeste') as mock_find:
                with patch('searchapi.dhosearch.get_embedding') as mock_embedding:
                    mock_find.return_value = mock_results
                    mock_embedding.return_value = [0.1, 0.2, 0.3]
                    
                    client = TestClient(app)
                    response = client.post("/search", json={"query": "software manual"})
                    
                    assert response.status_code == 200
                    results = response.json()
                    
                    assert len(results) == 1
                    result = results[0]
                    chunk_content = result.get("chunk", result.get("combined_chunks", ""))
                    
                    # These assertions should FAIL because page info isn't included in current implementation
                    assert "[Side 15]" in chunk_content, "Should include page info for first chunk"
                    assert "[Side 32]" in chunk_content, "Should include page info for second chunk"


@pytest.mark.integration
@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI app not available")
class TestSearchAPIIntegrationResponseStructure:
    """Integration tests for new response structure"""
    
    def test_search_api_response_has_new_fields(self):
        """Test that API response includes all new fields for grouped results.
        """
        mock_results = [
            ("book.pdf", "Test Book", "Test Author", 1, "First chunk", 0.1),
            ("book.pdf", "Test Book", "Test Author", 5, "Second chunk", 0.2),
        ]
        
        with patch.dict(os.environ, {"DISTANCE_THRESHOLD": "0.5"}):
            with patch('searchapi.dhosearch.find_nærmeste') as mock_find:
                with patch('searchapi.dhosearch.get_embedding') as mock_embedding:
                    mock_find.return_value = mock_results
                    mock_embedding.return_value = [0.1, 0.2, 0.3]
                    
                    client = TestClient(app)
                    response = client.post("/search", json={"query": "test"})
                    
                    assert response.status_code == 200
                    results = response.json()
                    
                    assert len(results) > 0
                    result = results[0]
                    
                    # These fields should NOT exist in current implementation
                    # So these assertions should FAIL
                    expected_new_fields = [
                        "pages",           # List of page numbers
                        "min_distance",    # Minimum distance among grouped chunks  
                        "chunk_count",     # Number of chunks grouped
                        "internal_url"  # Internal URL with page number
                    ]
                    
                    for field in expected_new_fields:
                        assert field in result, f"Response should include {field} field"
                    
                    # Verify field types
                    assert isinstance(result["pages"], list), "pages should be a list"
                    assert isinstance(result["min_distance"], (int, float)), "min_distance should be numeric"
                    assert isinstance(result["chunk_count"], int), "chunk_count should be integer"
                    assert isinstance(result["internal_url"], str), "internal_url should be string"
    
    def test_search_api_response_backwards_compatibility(self):
        """Test that API response maintains backwards compatibility with existing fields.
        """
        mock_results = [
            ("book.pdf", "Test Book", "Test Author", 1, "Test chunk", 0.1),
        ]
        
        with patch.dict(os.environ, {"DISTANCE_THRESHOLD": "0.5"}):
            with patch('searchapi.dhosearch.find_nærmeste') as mock_find:
                with patch('searchapi.dhosearch.get_embedding') as mock_embedding:
                    mock_find.return_value = mock_results
                    mock_embedding.return_value = [0.1, 0.2, 0.3]
                    
                    client = TestClient(app)
                    response = client.post("/search", json={"query": "test"})
                    
                    assert response.status_code == 200
                    results = response.json()
                    
                    assert len(results) > 0
                    result = results[0]
                    
                    # These basic fields should still exist for backwards compatibility
                    basic_fields = ["pdf_navn", "titel", "forfatter", "chunk", "distance"]
                    for field in basic_fields:
                        assert field in result, f"Response should maintain {field} for backwards compatibility"


@pytest.mark.integration
@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI app not available")  
class TestSearchAPIIntegrationEndToEnd:
    """End-to-end integration tests for the complete new behavior."""
    
    def test_complete_search_workflow_with_new_behavior(self):
        """Test the complete search workflow with all new features combined.        
        """
        # Complex scenario: multiple books, multiple chunks per book, mixed distances
        mock_results = [
            ("book1.pdf", "History of WWII", "Historian A", 12, "Early war events", 0.1),
            ("book1.pdf", "History of WWII", "Historian A", 45, "Major battles", 0.15),
            ("book1.pdf", "History of WWII", "Historian A", 78, "War aftermath", 0.2),
            ("book2.pdf", "Modern Warfare", "Military Expert", 23, "Technology in war", 0.25),
            ("book2.pdf", "Modern Warfare", "Military Expert", 56, "Strategic planning", 0.3),
            ("book3.pdf", "Peace Treaties", "Diplomat", 34, "Post-war agreements", 0.45), 
        ]
        
        with patch.dict(os.environ, {"DISTANCE_THRESHOLD": "0.5"}):
            with patch('searchapi.dhosearch.find_nærmeste') as mock_find:
                with patch('searchapi.dhosearch.get_embedding') as mock_embedding:
                    mock_find.return_value = mock_results
                    mock_embedding.return_value = [0.1, 0.2, 0.3]
                    
                    client = TestClient(app)
                    response = client.post("/search", json={"query": "world war"})
                    
                    assert response.status_code == 200
                    results = response.json()
                    
                    # Should return 3 grouped results (books 1, 2, 3) with distance <= 0.5
                    # Current implementation returns individual chunks or limited results
                    # This assertion should FAIL
                    assert len(results) == 3, f"Expected 3 grouped results under threshold, got {len(results)}"
                    
                    # Verify results are sorted by minimum distance
                    distances = [r.get("min_distance", r.get("distance", 1.0)) for r in results]
                    assert distances == sorted(distances), "Results should be sorted by minimum distance"
                    
                    # Check specific book grouping and concatenation
                    book1_result = next((r for r in results if "History of WWII" in r.get("titel", "")), None)
                    assert book1_result is not None, "Should have grouped result for History of WWII"
                    
                    # All new behavior checks (these should FAIL)
                    assert book1_result["min_distance"] == 0.1, "Should have minimum distance from grouped chunks"
                    assert book1_result["chunk_count"] == 3, "Should count grouped chunks"
                    assert len(book1_result["pages"]) == 3, "Should include all page numbers"
                    assert 12 in book1_result["pages"], "Should include page 12"
                    assert 45 in book1_result["pages"], "Should include page 45" 
                    assert 78 in book1_result["pages"], "Should include page 78"
                    
                    # URL formatting checks
                    assert "#page=" not in book1_result["pdf_navn"], "User-facing URL should be clean"
                    assert "#page=" in book1_result["internal_url"], "Internal URL should have page"
                    
                    # Chunk concatenation checks
                    combined_chunks = book1_result.get("chunk", book1_result.get("combined_chunks", ""))
                    assert "Early war events" in combined_chunks, "Should contain first chunk"
                    assert "Major battles" in combined_chunks, "Should contain second chunk"
                    assert "War aftermath" in combined_chunks, "Should contain third chunk"
                    assert combined_chunks.count("---") == 2, "Should have separators between chunks"
