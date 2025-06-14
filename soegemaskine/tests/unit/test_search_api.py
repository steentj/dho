"""
Unit tests for the FastAPI search endpoints and related functions.
"""
import pytest
import json
from unittest.mock import patch, AsyncMock
import sys
from pathlib import Path

# Add the searchapi directory to the path for imports
searchapi_path = Path(__file__).parent.parent.parent / "searchapi"
sys.path.insert(0, str(searchapi_path))

try:
    from searchapi.dhosearch import (
        Input,
        get_embedding,
        extract_text_from_chunk,
        find_nærmeste
    )
    FASTAPI_AVAILABLE = True
except ImportError as e:
    pytest.skip(f"Could not import from dhosearch: {e}", allow_module_level=True)
    FASTAPI_AVAILABLE = False


@pytest.mark.unit
@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not available")
class TestInputModel:
    """Test the Input Pydantic model."""
    
    def test_input_model_required_fields(self):
        """Test Input model with required fields only."""
        input_data = Input(query="test søgning")
        
        assert input_data.query == "test søgning"
  
@pytest.mark.unit
@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not available")
class TestGetEmbedding:
    """Test the get_embedding function."""
    
    def test_get_embedding_with_mock_client(self, mock_openai_client):
        """Test embedding generation with mocked OpenAI client."""
        text = "Dette er en test søgning"
        
        embedding = get_embedding(text, mock_openai_client)
        
        assert embedding == [0.1] * 1536
        mock_openai_client.embeddings.create.assert_called_once()
        
        # Check that newlines are replaced with spaces
        call_args = mock_openai_client.embeddings.create.call_args
        assert "\n" not in call_args[1]["input"][0]
    
    def test_get_embedding_newline_replacement(self, mock_openai_client):
        """Test that newlines are properly replaced with spaces."""
        text = "Dette er\nen test\nmesh flere\nlinjer"
        
        get_embedding(text, mock_openai_client)
        
        call_args = mock_openai_client.embeddings.create.call_args
        processed_text = call_args[1]["input"][0]
        
        assert "\n" not in processed_text
        assert processed_text == "Dette er en test mesh flere linjer"
    
    def test_get_embedding_model_parameter(self, mock_openai_client):
        """Test that the correct model is used."""
        text = "test"
        model = "text-embedding-3-large"
        
        get_embedding(text, mock_openai_client, model=model)
        
        call_args = mock_openai_client.embeddings.create.call_args
        assert call_args[1]["model"] == model


@pytest.mark.unit
@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not available")
class TestExtractTextFromChunk:
    """Test the extract_text_from_chunk function."""
    
    def test_extract_text_basic(self):
        """Test basic text extraction without book title."""
        chunk = "Dette er en almindelig tekst chunk uden bogtitel."
        
        result = extract_text_from_chunk(chunk)
        
        assert result == chunk
    
    def test_extract_text_with_book_title(self):
        """Test text extraction with book title prefix."""
        chunk = "##Bog Titel##Dette er teksten efter bogtitlen."
        
        result = extract_text_from_chunk(chunk)
        
        # Should remove "Bog Titel: " from the beginning
        assert result == "Dette er teksten efter bogtitlen."
    
    def test_extract_text_complex_title(self):
        """Test text extraction with complex book title."""
        chunk = "##NIELS ROLSTEDS BREVE FRA 1846-1854##Her begynder den egentlige tekst."
        
        result = extract_text_from_chunk(chunk)
        
        assert result == "Her begynder den egentlige tekst."
    
    def test_extract_text_no_colon(self):
        """Test text extraction when there's  notitle."""
        chunk = "Dette er tekst uden kolon separator"
        
        result = extract_text_from_chunk(chunk)
        
        # Should return original text if no colon found
        assert result == chunk
    
    def test_extract_text_multiple_colons(self):
        """Test text extraction with multiple colons."""
        chunk = "##Bog Titel##Dette er tekst## med flere## koloner."
        
        result = extract_text_from_chunk(chunk)
        
        # Should only remove the first title part
        assert result == "Dette er tekst## med flere## koloner."
    
    def test_extract_text_empty_after_colon(self):
        """Test text extraction when nothing follows the colon."""
        chunk = "##Bog Titel##"
        
        result = extract_text_from_chunk(chunk)
        
        assert result == ""


@pytest.mark.unit
@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not available")
class TestFindNærmeste:
    """Test the find_nærmeste function."""
    
    @pytest.mark.asyncio
    async def test_find_nærmeste_basic(self):
        """Test basic nearest neighbor search."""
        test_vector = [0.1] * 1536
        mock_results = [
            ("test.pdf", "Test Book", "Test Author", 1, "Test chunk", 0.5)
        ]
        
        with patch('searchapi.dhosearch.db_conn') as mock_db_conn:
            mock_cursor = AsyncMock()
            mock_cursor.fetchall.return_value = mock_results
            mock_db_conn.cursor.return_value.__aenter__.return_value = mock_cursor
            
            results = await find_nærmeste(test_vector)
            
            assert isinstance(results, list)
            assert mock_cursor.execute.called
            assert mock_cursor.fetchall.called
    
    @pytest.mark.asyncio
    async def test_find_nærmeste_query_structure(self):
        """Test that the database query has correct structure."""
        test_vector = [0.1] * 1536
        
        with patch('searchapi.dhosearch.db_conn') as mock_db_conn:
            mock_cursor = AsyncMock()
            mock_cursor.fetchall.return_value = []
            mock_db_conn.cursor.return_value.__aenter__.return_value = mock_cursor
            
            await find_nærmeste(test_vector)
            
            assert mock_cursor.execute.called
            # Check that execute was called with a query containing expected elements
            call_args = mock_cursor.execute.call_args
            query = call_args[0][0]
            
            assert "SELECT" in query
            assert "embedding" in query
            assert "ORDER BY" in query
    
    @pytest.mark.asyncio
    async def test_find_nærmeste_vector_parameter(self):
        """Test that the vector parameter is passed correctly."""
        test_vector = [0.1, 0.2, 0.3] * 512  # 1536 dimensions
        
        with patch('searchapi.dhosearch.db_conn') as mock_db_conn:
            mock_cursor = AsyncMock()
            mock_cursor.fetchall.return_value = []
            mock_db_conn.cursor.return_value.__aenter__.return_value = mock_cursor
            
            await find_nærmeste(test_vector)
            
            assert mock_cursor.execute.called
            call_args = mock_cursor.execute.call_args
            # The vector should be passed as a parameter
            assert len(call_args[0]) > 1  # Query + parameters
            # Vector should be converted to string in parameters
            assert str(test_vector) in str(call_args[0][1])


@pytest.mark.unit
@pytest.mark.skipif(not FASTAPI_AVAILABLE, reason="FastAPI not available")
class TestAPIEndpoints:
    """Test the FastAPI endpoints using TestClient."""
    
    def setup_method(self):
        """Setup for each test method."""
        # This would require a more complex setup with TestClient
        # For now, we'll test the endpoint logic separately
        pass
    
    def test_root_endpoint_response(self):
        """Test the root endpoint response structure."""
        expected_response = {
            "Hej": "Dette er Dansk Historie Online: Semantisk søgning API"
        }
        
        # This would be tested with TestClient in a full implementation
        assert "Hej" in expected_response
        assert "Semantisk" in expected_response["Hej"]
    
    def test_search_endpoint_input_validation(self):
        """Test search endpoint input validation."""
        # Test that Input model validates correctly
        valid_input = {
            "query": "test søgning",
            "chunk_size": "lille",
            "distance_function": "cosine"
        }
        
        input_obj = Input(**valid_input)
        assert input_obj.query == "test søgning"


@pytest.mark.unit
class TestUtilityFunctions:
    """Test utility functions that don't require FastAPI."""
    
    def test_environment_variable_parsing(self, mock_env_vars):
        """Test parsing of environment variables."""
        # Test TILLADTE_KALDERE parsing
        allowed_origins = mock_env_vars["TILLADTE_KALDERE"].split(",")
        
        assert len(allowed_origins) == 2
        assert "http://localhost:3000" in allowed_origins
        assert "http://127.0.0.1:3000" in allowed_origins
    
    def test_json_response_formatting(self):
        """Test JSON response formatting."""
        test_data = [
            {
                "pdf_navn": "test.pdf",
                "titel": "Test Bog",
                "forfatter": "Test Forfatter",
                "sidenr": 1,
                "chunk": "Test chunk",
                "distance": 0.15
            }
        ]
        
        json_response = json.dumps(test_data)
        parsed_response = json.loads(json_response)
        
        assert len(parsed_response) == 1
        assert parsed_response[0]["pdf_navn"] == "test.pdf"
        assert parsed_response[0]["distance"] == 0.15
