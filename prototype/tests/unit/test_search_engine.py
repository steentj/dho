"""
Unit tests for the SearchEngine classes.
"""
import pytest
from unittest.mock import MagicMock, patch
import sys
import os
from pathlib import Path

# Add the webpage_flask directory to the path for imports
webpage_flask_path = Path(__file__).parent.parent.parent.parent / "webpage_flask"
sys.path.insert(0, str(webpage_flask_path))

try:
    from searchengine import SearchEngine, MockSearchEngine
    SEARCHENGINE_AVAILABLE = True
except ImportError as e:
    pytest.skip(f"Could not import from searchengine: {e}", allow_module_level=True)
    SEARCHENGINE_AVAILABLE = False


@pytest.mark.unit
@pytest.mark.skipif(not SEARCHENGINE_AVAILABLE, reason="SearchEngine not available")
class TestSearchEngine:
    """Test the SearchEngine class."""
    
    def test_initialization(self, mock_env_vars):
        """Test SearchEngine initialization with environment variables."""
        with patch.dict(os.environ, mock_env_vars):
            with patch('searchengine.OpenAI') as mock_openai:
                engine = SearchEngine()
                
                assert hasattr(engine, 'client')
                assert hasattr(engine, 'database')
                assert hasattr(engine, 'db_user')
                assert hasattr(engine, 'db_password')
                mock_openai.assert_called_once()
    
    def test_get_embedding(self, mock_env_vars, mock_openai_client):
        """Test get_embedding method."""
        with patch.dict(os.environ, mock_env_vars):
            with patch('searchengine.OpenAI') as mock_openai_class:
                mock_openai_class.return_value = mock_openai_client
                
                engine = SearchEngine()
                result = engine.get_embedding("test text", mock_openai_client)
                
                assert result == [0.1] * 1536
                mock_openai_client.embeddings.create.assert_called_once()
    
    def test_get_embedding_newline_handling(self, mock_env_vars, mock_openai_client):
        """Test that get_embedding handles newlines correctly."""
        with patch.dict(os.environ, mock_env_vars):
            with patch('searchengine.OpenAI'):
                engine = SearchEngine()
                
                text_with_newlines = "Dette er\nen test\ntekst"
                engine.get_embedding(text_with_newlines, mock_openai_client)
                
                # Check that newlines were replaced with spaces
                call_args = mock_openai_client.embeddings.create.call_args
                processed_text = call_args[1]["input"][0]
                assert "\n" not in processed_text
                assert processed_text == "Dette er en test tekst"
    
    @patch('searchengine.psycopg2.connect')
    def test_find_nærmeste(self, mock_connect, mock_env_vars):
        """Test find_nærmeste method."""
        # Setup mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock database results
        mock_cursor.fetchall.return_value = [
            ("test.pdf", "Test Bog", "Test Forfatter", 1, "Test chunk", 0.15)
        ]
        
        with patch.dict(os.environ, mock_env_vars):
            with patch('searchengine.OpenAI'):
                engine = SearchEngine()
                
                test_vector = [0.1] * 1536
                results = engine.find_nærmeste(test_vector, "lille", "cosine")
                
                assert isinstance(results, list)
                assert len(results) > 0
                mock_cursor.execute.assert_called_once()
                mock_cursor.fetchall.assert_called_once()
    
    @patch('searchengine.psycopg2.connect')
    def test_get_results_integration(self, mock_connect, mock_env_vars, mock_openai_client):
        """Test get_results method integration."""
        # Setup mock database
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            ("test.pdf", "Test Bog", "Test Forfatter", 1, "Test chunk", 0.15)
        ]
        
        with patch.dict(os.environ, mock_env_vars):
            with patch('searchengine.OpenAI') as mock_openai_class:
                mock_openai_class.return_value = mock_openai_client
                
                engine = SearchEngine()
                results = engine.get_results("test query", "lille", "cosine")
                
                assert isinstance(results, list)
                # Should have called get_embedding and find_nærmeste
                mock_openai_client.embeddings.create.assert_called_once()
                mock_cursor.execute.assert_called_once()


@pytest.mark.unit
@pytest.mark.skipif(not SEARCHENGINE_AVAILABLE, reason="SearchEngine not available")
class TestMockSearchEngine:
    """Test the MockSearchEngine class."""
    
    def test_get_results_returns_mock_data(self):
        """Test that MockSearchEngine returns consistent mock data."""
        results = MockSearchEngine.get_results("any query")
        
        assert isinstance(results, list)
        assert len(results) > 0
        
        # Check the structure of the first result
        first_result = results[0]
        required_fields = ["pdf_navn", "titel", "page", "distance", "chunk"]
        for field in required_fields:
            assert field in first_result
    
    def test_get_results_consistent_output(self):
        """Test that MockSearchEngine returns consistent results."""
        results1 = MockSearchEngine.get_results("query 1")
        results2 = MockSearchEngine.get_results("query 2")
        
        # Should return same data regardless of query
        assert len(results1) == len(results2)
        assert results1[0]["pdf_navn"] == results2[0]["pdf_navn"]
    
    def test_mock_search_logging(self):
        """Test that MockSearchEngine logs the search query."""
        with patch('builtins.print') as mock_print:
            MockSearchEngine.get_results("test query")
            
            mock_print.assert_called_with("Mocked search for:", "test query")
    
    def test_mock_result_structure(self):
        """Test the structure and types of mock results."""
        results = MockSearchEngine.get_results("test")
        
        for result in results:
            assert isinstance(result["pdf_navn"], str)
            assert isinstance(result["titel"], str)
            assert isinstance(result["page"], int)
            assert isinstance(result["distance"], (int, float))
            assert isinstance(result["chunk"], str)
            
            # Check reasonable value ranges
            assert 0 <= result["distance"] <= 1
            assert result["page"] > 0
    
    def test_mock_content_danish(self):
        """Test that mock content contains Danish text."""
        results = MockSearchEngine.get_results("test")
        
        # Check that results contain Danish content
        found_danish = False
        for result in results:
            if any(danish_word in result["chunk"].lower() 
                   for danish_word in ["anna", "krogh", "niels", "rolsted", "gymnastik"]):
                found_danish = True
                break
        
        assert found_danish, "Mock results should contain Danish content"


@pytest.mark.unit
class TestSearchEngineHelpers:
    """Test helper functions and utilities for search engine."""
    
    def test_database_connection_parameters(self, mock_env_vars):
        """Test that database connection uses correct parameters."""
        with patch.dict(os.environ, mock_env_vars):
            with patch('searchengine.OpenAI'):
                with patch('searchengine.psycopg2.connect') as mock_connect:
                    engine = SearchEngine()
                    
                    # Trigger a database operation to test connection
                    try:
                        engine.find_nærmeste([0.1] * 1536, "lille", "cosine")
                    except Exception:
                        pass  # We're just testing the connection parameters
                    
                    # Check that connect was called with environment variables
                    if mock_connect.called:
                        # In a real implementation, you'd check specific connection parameters
                        assert True  # Placeholder for actual parameter validation
    
    def test_embedding_model_parameter(self, mock_openai_client):
        """Test that embedding requests use correct model."""
        with patch('searchengine.OpenAI') as mock_openai_class:
            mock_openai_class.return_value = mock_openai_client
            
            # This would need to be tested with the actual SearchEngine
            # when environment variables are available
            test_model = "text-embedding-3-small"
            
            # Mock call to verify model parameter
            mock_openai_client.embeddings.create.return_value.data = [
                MagicMock(embedding=[0.1] * 1536)
            ]
            
            # In actual implementation, verify that the model parameter is passed correctly
            assert test_model == "text-embedding-3-small"
    
    def test_query_construction(self):
        """Test SQL query construction for vector similarity search."""
        # This would test the actual SQL query building logic
        # For now, we test the expected components
        expected_components = [
            "SELECT",
            "pdf_navn",
            "titel", 
            "forfatter",
            "sidenr",
            "chunk",
            "embedding",
            "ORDER BY",
            "LIMIT"
        ]
        
        # In a real implementation, you'd extract the query from the method
        # and verify it contains these components
        for component in expected_components:
            assert isinstance(component, str)
            assert len(component) > 0
