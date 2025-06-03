"""
Integration tests for the updated search API behavior.
These tests will fail until the new behavior is implemented in the actual API.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import sys
from pathlib import Path

# Add the searchapi directory to the path for imports
searchapi_path = Path(__file__).parent.parent.parent / "searchapi"
sys.path.insert(0, str(searchapi_path))

try:
    from searchapi.dhosearch import app
    FASTAPI_AVAILABLE = True
except ImportError as e:
    pytest.skip(f"Could not import from dhosearch: {e}", allow_module_level=True)
    FASTAPI_AVAILABLE = False


@pytest.mark.integration
@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not available")
class TestUpdatedSearchAPIBehavior:
    """Test the updated search API behavior - these tests will fail initially."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    @patch.dict('os.environ', {'DISTANCE_THRESHOLD': '0.5'})
    @patch('searchapi.dhosearch.find_nærmeste')
    @patch('searchapi.dhosearch.get_embedding')
    def test_search_uses_distance_threshold_not_limit_5(self, mock_get_embedding, mock_find_nearest):
        """Test that search uses distance threshold instead of LIMIT 5."""
        # Mock embedding response
        mock_get_embedding.return_value = [0.1] * 1536
        
        # Mock database results - only results under threshold 0.5 (SQL filters out 0.6)
        mock_find_nearest.return_value = [
            ("book1.pdf", "Title 1", "Author 1", 1, "chunk1", 0.1),
            ("book2.pdf", "Title 2", "Author 2", 2, "chunk2", 0.2),
            ("book3.pdf", "Title 3", "Author 3", 3, "chunk3", 0.3),
            ("book4.pdf", "Title 4", "Author 4", 4, "chunk4", 0.4),
            ("book5.pdf", "Title 5", "Author 5", 5, "chunk5", 0.45),
            ("book6.pdf", "Title 6", "Author 6", 6, "chunk6", 0.49),
            # ("book7.pdf", "Title 7", "Author 7", 7, "chunk7", 0.6),  # Filtered out by SQL
        ]
        
        response = self.client.post("/search", json={"query": "test query"})
        
        assert response.status_code == 200
        results = response.json()  # No need for json.loads() since FastAPI returns proper JSON
        
        # Should return 6 results (all under 0.5 threshold), not limited to 5
        assert len(results) == 6  # This will fail with current implementation
        
        # Should not include result with distance 0.6
        distances = [result["distance"] for result in results]
        assert 0.6 not in distances
    
    @patch('searchapi.dhosearch.find_nærmeste')
    @patch('searchapi.dhosearch.get_embedding')
    def test_search_groups_results_by_book(self, mock_get_embedding, mock_find_nearest):
        """Test that search groups multiple chunks from same book."""
        mock_get_embedding.return_value = [0.1] * 1536
        
        # Mock results with multiple chunks from same book
        mock_find_nearest.return_value = [
            ("book1.pdf", "Title 1", "Author 1", 1, "##Title 1##chunk1 text", 0.2),
            ("book1.pdf", "Title 1", "Author 1", 3, "##Title 1##chunk2 text", 0.4),
            ("book2.pdf", "Title 2", "Author 2", 5, "##Title 2##chunk3 text", 0.3),
        ]
        
        response = self.client.post("/search", json={"query": "test query"})
        
        assert response.status_code == 200
        results = response.json()
        
        # Should return 2 grouped results (one per book), not 3 individual chunks
        assert len(results) == 2  # This will fail with current implementation
        
        # Find the result for "Title 1"
        title1_result = next((r for r in results if r["titel"] == "Title 1"), None)
        assert title1_result is not None
        
        # Should contain concatenated chunks
        assert "---" in title1_result["chunk"]  # This will fail
        assert "chunk1 text" in title1_result["chunk"]
        assert "chunk2 text" in title1_result["chunk"]
        
        # Should contain page numbers as array
        assert "pages" in title1_result  # Updated to match actual field name
        assert title1_result["pages"] == [1, 3]  # Both page numbers
    
    @patch('searchapi.dhosearch.find_nærmeste')  
    @patch('searchapi.dhosearch.get_embedding')
    def test_search_returns_both_url_types(self, mock_get_embedding, mock_find_nearest):
        """Test that search returns both user-facing and internal URLs."""
        mock_get_embedding.return_value = [0.1] * 1536
        
        mock_find_nearest.return_value = [
            ("book1.pdf", "Title 1", "Author 1", 5, "##Title 1##chunk text", 0.3),
        ]
        
        response = self.client.post("/search", json={"query": "test query"})
        
        assert response.status_code == 200
        results = response.json()
        
        assert len(results) == 1
        result = results[0]
        
        # Should have user-facing URL without page number
        assert "pdf_navn" in result  # User-facing URL
        assert result["pdf_navn"] == "book1.pdf"  # No page number
        
        # Should have internal URL with page number
        assert "internal_url" in result  # Internal URL with page number
        assert result["internal_url"] == "book1.pdf#page=5"  # With page number
    
    @patch('searchapi.dhosearch.find_nærmeste')
    @patch('searchapi.dhosearch.get_embedding') 
    def test_search_sql_uses_distance_threshold(self, mock_get_embedding, mock_find_nearest):
        """Test that the SQL query uses distance threshold instead of LIMIT 5."""
        mock_get_embedding.return_value = [0.1] * 1536
        mock_find_nearest.return_value = []
        
        response = self.client.post("/search", json={"query": "test query"})
        
        # Verify that find_nærmeste was called (which contains the SQL)
        mock_find_nearest.assert_called_once()
        
        # The actual SQL change will be tested when we modify find_nærmeste
        # For now, this test documents that the SQL should change
        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not available")
class TestCurrentBehaviorDocumentation:
    """Document current behavior that will be changed."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    @patch('searchapi.dhosearch.find_nærmeste')
    @patch('searchapi.dhosearch.get_embedding')
    def test_current_behavior_returns_individual_chunks(self, mock_get_embedding, mock_find_nearest):
        """Document current behavior: returns individual chunks, not grouped."""
        mock_get_embedding.return_value = [0.1] * 1536
        
        # Mock multiple chunks from same book
        mock_find_nearest.return_value = [
            ("book1.pdf", "Title 1", "Author 1", 1, "##Title 1##chunk1", 0.2),
            ("book1.pdf", "Title 1", "Author 1", 3, "##Title 1##chunk2", 0.4),
        ]
        
        response = self.client.post("/search", json={"query": "test query"})
        
        assert response.status_code == 200
        results = response.json()
        
        # Current behavior: returns 2 separate results for same book
        assert len(results) == 2
        
        # Both results are for same book but separate
        assert results[0]["titel"] == "Title 1" 
        assert results[1]["titel"] == "Title 1"
        assert results[0]["chunk"] != results[1]["chunk"]
    
    @patch('searchapi.dhosearch.find_nærmeste')
    @patch('searchapi.dhosearch.get_embedding')
    def test_current_url_format_with_page_numbers(self, mock_get_embedding, mock_find_nearest):
        """Document current URL format that includes page numbers."""
        mock_get_embedding.return_value = [0.1] * 1536
        
        mock_find_nearest.return_value = [
            ("book1.pdf", "Title 1", "Author 1", 5, "##Title 1##chunk", 0.3),
        ]
        
        response = self.client.post("/search", json={"query": "test query"})
        
        assert response.status_code == 200
        results = response.json()
        
        # Current behavior: pdf_navn includes page number
        assert results[0]["pdf_navn"] == "book1.pdf#page=5"
        
        # New fields don't exist yet
        assert "pdf_url" not in results[0]
        assert "pdf_url_internal" not in results[0] 
        assert "page_numbers" not in results[0]
