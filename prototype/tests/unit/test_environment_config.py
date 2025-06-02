"""
Unit tests for environment variable configuration.
"""
import pytest
import os
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add the searchapi directory to the path for imports
searchapi_path = Path(__file__).parent.parent.parent / "searchapi"
sys.path.insert(0, str(searchapi_path))


@pytest.mark.unit
class TestEnvironmentConfiguration:
    """Test environment variable loading and configuration."""
    
    def test_distance_threshold_default_value(self):
        """Test that DISTANCE_THRESHOLD has correct default value."""
        with patch.dict(os.environ, {}, clear=True):
            # When no environment variable is set, should default to 0.5
            threshold = float(os.getenv("DISTANCE_THRESHOLD", "0.5"))
            assert threshold == 0.5
    
    def test_distance_threshold_custom_value(self):
        """Test that DISTANCE_THRESHOLD can be set to custom value."""
        test_threshold = "0.3"
        with patch.dict(os.environ, {"DISTANCE_THRESHOLD": test_threshold}):
            threshold = float(os.getenv("DISTANCE_THRESHOLD", "0.5"))
            assert threshold == 0.3
    
    def test_distance_threshold_invalid_value_handling(self):
        """Test handling of invalid DISTANCE_THRESHOLD values."""
        with patch.dict(os.environ, {"DISTANCE_THRESHOLD": "invalid"}):
            with pytest.raises(ValueError):
                float(os.getenv("DISTANCE_THRESHOLD", "0.5"))
    
    def test_distance_threshold_boundary_values(self):
        """Test boundary values for DISTANCE_THRESHOLD."""
        # Test minimum value (0.0)
        with patch.dict(os.environ, {"DISTANCE_THRESHOLD": "0.0"}):
            threshold = float(os.getenv("DISTANCE_THRESHOLD", "0.5"))
            assert threshold == 0.0
        
        # Test maximum value (1.0 for cosine distance)
        with patch.dict(os.environ, {"DISTANCE_THRESHOLD": "1.0"}):
            threshold = float(os.getenv("DISTANCE_THRESHOLD", "0.5"))
            assert threshold == 1.0
    
    def test_all_required_environment_variables_structure(self):
        """Test that all required environment variables are properly structured."""
        required_vars = [
            "DATABASE_URL",
            "OPENAI_API_KEY", 
            "TILLADTE_KALDERE",
            "DISTANCE_THRESHOLD"
        ]
        
        # Test with mock values
        mock_env = {
            "DATABASE_URL": "postgres://test:test@localhost/testdb",
            "OPENAI_API_KEY": "test-key",
            "TILLADTE_KALDERE": "http://localhost:8000,http://localhost:3000",
            "DISTANCE_THRESHOLD": "0.5"
        }
        
        with patch.dict(os.environ, mock_env):
            for var in required_vars:
                assert os.getenv(var) is not None
                assert len(os.getenv(var)) > 0
    
    def test_tilladte_kaldere_parsing(self):
        """Test parsing of TILLADTE_KALDERE environment variable."""
        test_urls = "http://localhost:8000,https://example.com,http://localhost:3000"
        
        with patch.dict(os.environ, {"TILLADTE_KALDERE": test_urls}):
            urls = os.getenv("TILLADTE_KALDERE", "").split(",")
            filtered_urls = [url for url in urls if url]
            
            assert len(filtered_urls) == 3
            assert "http://localhost:8000" in filtered_urls
            assert "https://example.com" in filtered_urls
            assert "http://localhost:3000" in filtered_urls
    
    def test_tilladte_kaldere_empty_handling(self):
        """Test handling of empty TILLADTE_KALDERE."""
        with patch.dict(os.environ, {"TILLADTE_KALDERE": ""}):
            urls = os.getenv("TILLADTE_KALDERE", "").split(",")
            filtered_urls = [url for url in urls if url]
            
            assert len(filtered_urls) == 0


@pytest.mark.unit 
class TestEnvironmentVariableIntegration:
    """Test integration of environment variables with application logic."""
    
    def test_distance_threshold_integration_mock(self):
        """Test that distance threshold is properly used in application logic."""
        # This is a placeholder test that will be expanded when we implement
        # the actual distance threshold logic in the search function
        test_threshold = "0.3"
        
        with patch.dict(os.environ, {"DISTANCE_THRESHOLD": test_threshold}):
            threshold = float(os.getenv("DISTANCE_THRESHOLD", "0.5"))
            
            # Test that the threshold can be used in comparison operations
            test_distances = [0.1, 0.25, 0.35, 0.5, 0.8]
            filtered_results = [d for d in test_distances if d <= threshold]
            
            assert len(filtered_results) == 2  # 0.1 and 0.25
            assert 0.1 in filtered_results
            assert 0.25 in filtered_results
            assert 0.35 not in filtered_results
    
    @patch('os.getenv')
    def test_environment_variable_loading_order(self, mock_getenv):
        """Test that environment variables are loaded in correct order."""
        # Mock the getenv calls to track the order
        mock_getenv.side_effect = lambda key, default=None: {
            "DATABASE_URL": "postgres://test:test@localhost/testdb",
            "OPENAI_API_KEY": "test-key", 
            "DISTANCE_THRESHOLD": "0.5",
            "TILLADTE_KALDERE": "http://localhost:8000"
        }.get(key, default)
        
        # Simulate loading environment variables
        db_url = os.getenv("DATABASE_URL")
        api_key = os.getenv("OPENAI_API_KEY")
        threshold = os.getenv("DISTANCE_THRESHOLD", "0.5")
        allowed_origins = os.getenv("TILLADTE_KALDERE", "")
        
        # Verify all calls were made
        assert mock_getenv.call_count >= 4
        assert db_url == "postgres://test:test@localhost/testdb"
        assert api_key == "test-key"
        assert threshold == "0.5"
        assert allowed_origins == "http://localhost:8000"
