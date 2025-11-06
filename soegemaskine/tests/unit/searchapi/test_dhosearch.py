"""
Unit tests for dhosearch.py
"""
import os
import sys
from pathlib import Path
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.middleware.cors import CORSMiddleware

# Add src directory to the path for imports
src_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(src_path))

# Import the module under test
from soegemaskine.searchapi import dhosearch
from soegemaskine.searchapi.dhosearch import (
    SearchResult, 
    SearchResponse, 
    Input, 
    lifespan,
    group_results_by_book, 
    create_response_format, 
    find_nærmeste,
    extract_text_from_chunk
)

@pytest.mark.unit
class TestSearchModels:
    """Test the Pydantic models for search API."""
    
    def test_search_result_model(self):
        """Test SearchResult model initialization with valid data."""
        data = {
            "pdf_navn": "test.pdf",
            "titel": "Test Bog",
            "forfatter": "Test Forfatter",
            "chunks": ["[Side 42] Dette er en test chunk.", "[Side 43] Dette er endnu en chunk."],
            "min_distance": 0.15,
            "chunk_count": 2
        }
        
        result = SearchResult(**data)
        
        assert result.pdf_navn == "test.pdf"
        assert result.titel == "Test Bog"
        assert result.forfatter == "Test Forfatter"
        assert result.chunks == ["[Side 42] Dette er en test chunk.", "[Side 43] Dette er endnu en chunk."]
        assert result.min_distance == 0.15
        assert result.chunk_count == 2
    
    def test_search_response_model(self):
        """Test SearchResponse model initialization with valid data."""
        results = [
            SearchResult(
                pdf_navn="test1.pdf",
                titel="Test Bog 1",
                forfatter="Forfatter 1",
                chunks=["[Side 42] Dette er en test chunk 1."],
                min_distance=0.15,
                chunk_count=1
            ),
            SearchResult(
                pdf_navn="test2.pdf",
                titel="Test Bog 2",
                forfatter="Forfatter 2",
                chunks=["[Side 10] Dette er en test chunk 2.", "[Side 11] Endnu en chunk."],
                min_distance=0.25,
                chunk_count=2
            )
        ]
        
        response = SearchResponse(results=results)
        
        assert len(response.results) == 2
        assert response.results[0].pdf_navn == "test1.pdf"
        assert response.results[1].pdf_navn == "test2.pdf"
    
    def test_input_model(self):
        """Test Input model initialization with valid data."""
        data = {"query": "test søgning"}
        
        input_obj = Input(**data)
        
        assert input_obj.query == "test søgning"

@pytest.mark.unit
class TestLifespan:
    """Test the lifespan context manager."""
    
    @pytest.mark.asyncio
    @patch('soegemaskine.searchapi.dhosearch.PostgreSQLService')
    @patch('soegemaskine.searchapi.dhosearch.EmbeddingProviderFactory')
    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://user:pass@localhost/testdb",
        "PROVIDER": "openai",
        "OPENAI_API_KEY": "sk-test",
        "OPENAI_MODEL": "text-embedding-3-small"
    }, clear=True)
    async def test_lifespan_openai_init(self, mock_factory, mock_postgresql):
        """Test lifespan initialization with OpenAI provider."""
        # Setup mocks
        mock_db = AsyncMock()
        mock_postgresql.return_value = mock_db
        
        mock_provider = MagicMock()
        mock_factory.create_from_config.return_value = mock_provider
        
        # Create a FastAPI app with the lifespan context
        app = FastAPI()
        
        # Initialize global variables to None
        dhosearch.db_service = None
        dhosearch.embedding_provider = None
        
        # Call the lifespan context manager
        async with lifespan(app):
            # Check that services were initialized
            assert dhosearch.db_service is not None
            assert dhosearch.embedding_provider is not None
            
            # Check that connect was called
            mock_db.connect.assert_called_once()
            
            # Check provider was created with correct parameters
            mock_factory.create_from_config.assert_called_once()
        
        # Check that disconnect was called after context exit
        mock_db.disconnect.assert_called_once()
        
        # Check that global variables were reset to None
        assert dhosearch.db_service is None
        assert dhosearch.embedding_provider is None
    
    @pytest.mark.asyncio
    @patch('soegemaskine.searchapi.dhosearch.PostgreSQLService')
    @patch('soegemaskine.searchapi.dhosearch.EmbeddingProviderFactory')
    @patch.dict(os.environ, {
        "DATABASE_URL": "postgresql://user:pass@localhost/testdb",
        "PROVIDER": "ollama",
        "OLLAMA_MODEL": "nomic-embed-text"
    }, clear=True)
    async def test_lifespan_ollama_init(self, mock_factory, mock_postgresql):
        """Test lifespan initialization with Ollama provider."""
        # Setup mocks
        mock_db = AsyncMock()
        mock_postgresql.return_value = mock_db
        
        mock_provider = MagicMock()
        mock_factory.create_from_config.return_value = mock_provider
        
        # Create a FastAPI app with the lifespan context
        app = FastAPI()
        
        # Initialize global variables to None
        dhosearch.db_service = None
        dhosearch.embedding_provider = None
        
        # Call the lifespan context manager
        async with lifespan(app):
            # Check that services were initialized
            assert dhosearch.db_service is not None
            assert dhosearch.embedding_provider is not None
            
            # Check that connect was called
            mock_db.connect.assert_called_once()
            
            # Check provider was created with correct parameters
            mock_factory.create_from_config.assert_called_once()
        
        # Check that disconnect was called after context exit
        mock_db.disconnect.assert_called_once()

@pytest.mark.unit
class TestMiddleware:
    """Test the HTTP middleware."""
    
    @patch('soegemaskine.searchapi.dhosearch.PostgreSQLService')
    @patch('soegemaskine.searchapi.dhosearch.EmbeddingProviderFactory')
    def test_log_origin_middleware(self, mock_factory, mock_postgresql):
        """Test log origin middleware."""
        # Setup mock app
        mock_db = AsyncMock()
        mock_postgresql.return_value = mock_db
        mock_db.connect = AsyncMock()
        mock_db.disconnect = AsyncMock()
        
        mock_provider = MagicMock()
        mock_factory.create_provider.return_value = mock_provider
        
        # Initialize TestClient with our FastAPI app
        with patch('soegemaskine.searchapi.dhosearch.print') as mock_print:
            client = TestClient(dhosearch.app)
            
            # Send a request with an origin header
            response = client.get("/", headers={"origin": "http://example.com"})
            
            # Check that the origin was logged
            mock_print.assert_any_call("Origin: http://example.com")
            
            # Check response
            assert response.status_code == 200

@pytest.mark.unit
class TestCORSMiddleware:
    """Test the CORS middleware."""
    
    @patch('soegemaskine.searchapi.dhosearch.PostgreSQLService')
    @patch('soegemaskine.searchapi.dhosearch.EmbeddingProviderFactory')
    @patch.dict(os.environ, {
        "TILLADTE_KALDERE": "http://localhost:3000,http://example.com"
    }, clear=True)
    def test_cors_middleware_allowed_origin(self, mock_factory, mock_postgresql):
        """Test CORS middleware with allowed origin."""
        # Setup mock app
        mock_db = AsyncMock()
        mock_postgresql.return_value = mock_db
        mock_db.connect = AsyncMock()
        mock_db.disconnect = AsyncMock()
        
        mock_provider = MagicMock()
        mock_factory.create_provider.return_value = mock_provider
        
        # Create a fresh app instance to avoid middleware conflicts
        test_app = FastAPI()
        
        # Add CORS middleware to test app
        tilladte_oprindelse_urler = os.environ["TILLADTE_KALDERE"].split(",")
        test_app.add_middleware(
            CORSMiddleware,
            allow_origins=[url for url in tilladte_oprindelse_urler if url],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Initialize TestClient with our test app
        client = TestClient(test_app)
        
        # Send a request with an allowed origin
        # Using OPTIONS request to trigger preflight CORS handling
        response = client.options("/", headers={
            "origin": "http://localhost:3000",
            "access-control-request-method": "GET"
        })
        
        # Check CORS headers
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert response.status_code == 200
    
    @patch('soegemaskine.searchapi.dhosearch.PostgreSQLService')
    @patch('soegemaskine.searchapi.dhosearch.EmbeddingProviderFactory')
    @patch.dict(os.environ, {
        "TILLADTE_KALDERE": "http://localhost:3000,http://example.com"
    }, clear=True)
    def test_cors_middleware_disallowed_origin(self, mock_factory, mock_postgresql):
        """Test CORS middleware with disallowed origin."""
        # Setup mock app
        mock_db = AsyncMock()
        mock_postgresql.return_value = mock_db
        mock_db.connect = AsyncMock()
        mock_db.disconnect = AsyncMock()
        
        mock_provider = MagicMock()
        mock_factory.create_provider.return_value = mock_provider
        
        # Create a fresh app instance to avoid middleware conflicts
        test_app = FastAPI()
        
        # Add CORS middleware to test app
        tilladte_oprindelse_urler = os.environ["TILLADTE_KALDERE"].split(",")
        test_app.add_middleware(
            CORSMiddleware,
            allow_origins=[url for url in tilladte_oprindelse_urler if url],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Initialize TestClient with our test app
        client = TestClient(test_app)
        
        # Send a request with a disallowed origin
        # Using OPTIONS request to trigger preflight CORS handling
        response = client.options("/", headers={
            "origin": "http://bad-origin.com",
            "access-control-request-method": "GET"
        })
        
        # Check CORS headers - disallowed origin should not be in the response
        assert response.headers.get("access-control-allow-origin") != "http://bad-origin.com"
        # For OPTIONS (preflight) request with disallowed origin, FastAPI returns 400
        assert response.status_code == 400

@pytest.mark.unit
class TestEndpoints:
    """Test the API endpoints."""
    
    @patch('soegemaskine.searchapi.dhosearch.PostgreSQLService')
    @patch('soegemaskine.searchapi.dhosearch.EmbeddingProviderFactory')
    def test_root_endpoint(self, mock_factory, mock_postgresql):
        """Test the root endpoint."""
        # Setup mock app
        mock_db = AsyncMock()
        mock_postgresql.return_value = mock_db
        mock_db.connect = AsyncMock()
        mock_db.disconnect = AsyncMock()
        
        mock_provider = MagicMock()
        mock_factory.create_provider.return_value = mock_provider
        
        # Initialize TestClient with our FastAPI app
        client = TestClient(dhosearch.app)
        
        # Call the root endpoint
        response = client.get("/")
        
        # Check response
        assert response.status_code == 200
        assert "Hej" in response.json()
        assert "Semantisk søgning API" in response.json()["Hej"]
    
    @patch('soegemaskine.searchapi.dhosearch.PostgreSQLService')
    @patch('soegemaskine.searchapi.dhosearch.EmbeddingProviderFactory')
    @patch('soegemaskine.searchapi.dhosearch.find_nærmeste')
    @patch('soegemaskine.searchapi.dhosearch.group_results_by_book')
    @patch('soegemaskine.searchapi.dhosearch.create_response_format')
    def test_search_endpoint(self, mock_create_response, mock_group_results, 
                            mock_find_nearest, mock_factory, mock_postgresql):
        """Test the search endpoint."""
        # Setup mock app
        mock_db = AsyncMock()
        mock_postgresql.return_value = mock_db
        mock_db.connect = AsyncMock()
        mock_db.disconnect = AsyncMock()
        
        # We need to initialize the global variables directly
        # since the FastAPI lifespan context is not run during testing
        mock_provider = MagicMock()
        mock_provider.get_embedding = AsyncMock(return_value=[0.1] * 1536)
        mock_factory.create_provider.return_value = mock_provider
        
        # Directly assign to global variables
        dhosearch.db_service = mock_db
        dhosearch.embedding_provider = mock_provider
        
        # Setup mock search results
        mock_db_results = [
            ("test.pdf", "Test Bog", "Test Forfatter", 42, "Dette er en test chunk.", 0.15)
        ]
        mock_find_nearest.return_value = mock_db_results
        
        # Setup mock grouped results
        mock_grouped = {
            "test.pdf": {
                "pdf_navn": "test.pdf",
                "titel": "Test Bog",
                "forfatter": "Test Forfatter",
                "chunks": [
                    {"chunk": "Dette er en test chunk.", "sidenr": 42, "distance": 0.15}
                ],
                "pages": [42],
                "distances": [0.15],
                "min_distance": 0.15
            }
        }
        mock_group_results.return_value = mock_grouped
        
        # Setup mock response format
        mock_response = [
            {
                "pdf_navn": "test.pdf",
                "titel": "Test Bog",
                "forfatter": "Test Forfatter",
                "chunks": ["[Side 42] Dette er en test chunk."],
                "min_distance": 0.15,
                "chunk_count": 1
            }
        ]
        mock_create_response.return_value = mock_response
        
        # Initialize TestClient with our FastAPI app
        client = TestClient(dhosearch.app)
        
        # Call the search endpoint
        response = client.post("/search", json={"query": "test søgning"})
        
        # Check response
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["pdf_navn"] == "test.pdf"
        assert response.json()[0]["titel"] == "Test Bog"
        
        # Verify mock calls
        mock_provider.get_embedding.assert_called_once_with("test søgning")
        mock_find_nearest.assert_called_once()
        mock_group_results.assert_called_once_with(mock_db_results)
        mock_create_response.assert_called_once_with(mock_grouped)

@pytest.mark.unit
class TestGroupResultsByBook:
    """Test the group_results_by_book function."""
    
    def test_group_results_single_book(self):
        """Test grouping results from a single book."""
        results = [
            ("test.pdf", "Test Bog", "Test Forfatter", 42, "Chunk 1", 0.15),
            ("test.pdf", "Test Bog", "Test Forfatter", 43, "Chunk 2", 0.25),
            ("test.pdf", "Test Bog", "Test Forfatter", 44, "Chunk 3", 0.10)
        ]
        
        grouped = group_results_by_book(results)
        
        assert len(grouped) == 1
        assert "test.pdf" in grouped
        assert grouped["test.pdf"]["titel"] == "Test Bog"
        assert grouped["test.pdf"]["forfatter"] == "Test Forfatter"
        assert len(grouped["test.pdf"]["chunks"]) == 3
        assert grouped["test.pdf"]["pages"] == [42, 43, 44]
        assert grouped["test.pdf"]["distances"] == [0.15, 0.25, 0.10]
        assert grouped["test.pdf"]["min_distance"] == 0.10  # Minimum distance
    
    def test_group_results_multiple_books(self):
        """Test grouping results from multiple books."""
        results = [
            ("test1.pdf", "Test Bog 1", "Forfatter 1", 10, "Chunk 1 from Book 1", 0.15),
            ("test2.pdf", "Test Bog 2", "Forfatter 2", 20, "Chunk 1 from Book 2", 0.25),
            ("test1.pdf", "Test Bog 1", "Forfatter 1", 11, "Chunk 2 from Book 1", 0.35)
        ]
        
        grouped = group_results_by_book(results)
        
        assert len(grouped) == 2
        assert "test1.pdf" in grouped
        assert "test2.pdf" in grouped
        
        # Check book 1
        assert grouped["test1.pdf"]["titel"] == "Test Bog 1"
        assert grouped["test1.pdf"]["forfatter"] == "Forfatter 1"
        assert len(grouped["test1.pdf"]["chunks"]) == 2
        assert grouped["test1.pdf"]["pages"] == [10, 11]
        assert grouped["test1.pdf"]["min_distance"] == 0.15
        
        # Check book 2
        assert grouped["test2.pdf"]["titel"] == "Test Bog 2"
        assert grouped["test2.pdf"]["forfatter"] == "Forfatter 2"
        assert len(grouped["test2.pdf"]["chunks"]) == 1
        assert grouped["test2.pdf"]["pages"] == [20]
        assert grouped["test2.pdf"]["min_distance"] == 0.25
    
    def test_group_results_empty_input(self):
        """Test grouping with empty input."""
        results = []
        
        grouped = group_results_by_book(results)
        
        assert len(grouped) == 0
        assert isinstance(grouped, dict)
    
    def test_group_results_none_forfatter(self):
        """Test grouping with None forfatter value."""
        results = [
            ("test.pdf", "Test Bog", None, 42, "Chunk 1", 0.15),
            ("test.pdf", "Test Bog", "None", 43, "Chunk 2", 0.25)
        ]
        
        grouped = group_results_by_book(results)
        
        assert len(grouped) == 1
        assert grouped["test.pdf"]["forfatter"] == ""  # None converted to empty string
    
    def test_group_results_update_min_distance(self):
        """Test that min_distance is updated correctly."""
        results = [
            ("test.pdf", "Test Bog", "Test Forfatter", 42, "Chunk 1", 0.30),
            ("test.pdf", "Test Bog", "Test Forfatter", 43, "Chunk 2", 0.10),
            ("test.pdf", "Test Bog", "Test Forfatter", 44, "Chunk 3", 0.20)
        ]
        
        grouped = group_results_by_book(results)
        
        assert grouped["test.pdf"]["min_distance"] == 0.10  # Should be the minimum

@pytest.mark.unit
class TestCreateResponseFormat:
    """Test the create_response_format function."""
    
    def test_create_response_format_basic(self):
        """Test basic response format creation."""
        grouped_results = {
            "test.pdf": {
                "pdf_navn": "test.pdf",
                "titel": "Test Bog",
                "forfatter": "Test Forfatter",
                "chunks": [
                    {"chunk": "##title##Chunk 1 text", "sidenr": 42, "distance": 0.15},
                    {"chunk": "##title##Chunk 2 text", "sidenr": 43, "distance": 0.25}
                ],
                "pages": [42, 43],
                "distances": [0.15, 0.25],
                "min_distance": 0.15
            }
        }
        
        response = create_response_format(grouped_results)
        
        assert len(response) == 1
        assert response[0]["pdf_navn"] == "test.pdf"
        assert response[0]["titel"] == "Test Bog"
        assert response[0]["forfatter"] == "Test Forfatter"
        assert "chunks" in response[0]
        assert len(response[0]["chunks"]) == 2
        assert "[Side 42]" in response[0]["chunks"][0]
        assert "[Side 43]" in response[0]["chunks"][1]
        assert "Chunk 1 text" in response[0]["chunks"][0]
        assert "Chunk 2 text" in response[0]["chunks"][1]
        assert response[0]["min_distance"] == 0.15
        assert response[0]["chunk_count"] == 2
    
    def test_create_response_format_multiple_books(self):
        """Test response format creation with multiple books."""
        grouped_results = {
            "test1.pdf": {
                "pdf_navn": "test1.pdf",
                "titel": "Test Bog 1",
                "forfatter": "Forfatter 1",
                "chunks": [
                    {"chunk": "##title##Chunk from Book 1", "sidenr": 10, "distance": 0.15}
                ],
                "pages": [10],
                "distances": [0.15],
                "min_distance": 0.15
            },
            "test2.pdf": {
                "pdf_navn": "test2.pdf",
                "titel": "Test Bog 2",
                "forfatter": "Forfatter 2",
                "chunks": [
                    {"chunk": "##title##Chunk from Book 2", "sidenr": 20, "distance": 0.10}
                ],
                "pages": [20],
                "distances": [0.10],
                "min_distance": 0.10
            }
        }
        
        response = create_response_format(grouped_results)
        
        assert len(response) == 2
        
        # Results should be sorted by min_distance (ascending)
        assert response[0]["pdf_navn"] == "test2.pdf"  # Lower distance comes first
        assert response[1]["pdf_navn"] == "test1.pdf"
        
        # Check book 2 (first in results)
        assert response[0]["titel"] == "Test Bog 2"
        assert response[0]["min_distance"] == 0.10
        assert "chunks" in response[0]
        assert "[Side 20]" in response[0]["chunks"][0]
        
        # Check book 1 (second in results)
        assert response[1]["titel"] == "Test Bog 1"
        assert response[1]["min_distance"] == 0.15
        assert "chunks" in response[1]
        assert "[Side 10]" in response[1]["chunks"][0]
    
    def test_create_response_format_empty_input(self):
        """Test response format creation with empty input."""
        grouped_results = {}
        
        response = create_response_format(grouped_results)
        
        assert len(response) == 0
        assert isinstance(response, list)
    
    def test_create_response_format_sort_by_distance(self):
        """Test that results are sorted by distance."""
        grouped_results = {
            "test1.pdf": {
                "pdf_navn": "test1.pdf",
                "titel": "Test Bog 1",
                "forfatter": "Forfatter 1",
                "chunks": [
                    {"chunk": "##title##Chunk from Book 1", "sidenr": 10, "distance": 0.30}
                ],
                "pages": [10],
                "distances": [0.30],
                "min_distance": 0.30
            },
            "test2.pdf": {
                "pdf_navn": "test2.pdf",
                "titel": "Test Bog 2",
                "forfatter": "Forfatter 2",
                "chunks": [
                    {"chunk": "##title##Chunk from Book 2", "sidenr": 20, "distance": 0.10}
                ],
                "pages": [20],
                "distances": [0.10],
                "min_distance": 0.10
            },
            "test3.pdf": {
                "pdf_navn": "test3.pdf",
                "titel": "Test Bog 3",
                "forfatter": "Forfatter 3",
                "chunks": [
                    {"chunk": "##title##Chunk from Book 3", "sidenr": 30, "distance": 0.20}
                ],
                "pages": [30],
                "distances": [0.20],
                "min_distance": 0.20
            }
        }
        
        response = create_response_format(grouped_results)
        
        # Check correct sorting by min_distance
        assert response[0]["pdf_navn"] == "test2.pdf"  # distance = 0.10
        assert response[1]["pdf_navn"] == "test3.pdf"  # distance = 0.20
        assert response[2]["pdf_navn"] == "test1.pdf"  # distance = 0.30

@pytest.mark.unit
class TestFindNærmeste:
    """Test the find_nærmeste function."""
    
    @pytest.mark.asyncio
    @patch('soegemaskine.searchapi.dhosearch.os.getenv')
    async def test_find_nærmeste_basic(self, mock_getenv):
        """Test basic find_nærmeste functionality."""
        # Setup mocks
        mock_getenv.return_value = "0.5"  # distance threshold
        mock_db_results = [
            ("test.pdf", "Test Bog", "Test Forfatter", 42, "Dette er en test chunk.", 0.15),
            ("test.pdf", "Test Bog", "Test Forfatter", 43, "Dette er en anden test chunk.", 0.25),
            ("test.pdf", "Test Bog", "Test Forfatter", 44, "Dette er en tredje test chunk.", 0.55)  # Exceeds threshold
        ]
        
        # Set up global variables
        dhosearch.db_service = AsyncMock()
        dhosearch.db_service.vector_search = AsyncMock(return_value=mock_db_results)
        
        dhosearch.embedding_provider = MagicMock()
        dhosearch.embedding_provider.get_provider_name = MagicMock(return_value="openai")
        
        # Call the function
        test_vector = [0.1] * 1536
        results = await find_nærmeste(test_vector)
        
        # Verify results - should filter out the result with distance > 0.5
        assert len(results) == 2
        assert results[0][0] == "test.pdf"
        assert results[0][3] == 42  # page number
        assert results[1][3] == 43  # page number
        
        # Verify the DB call
        dhosearch.db_service.vector_search.assert_called_once_with(
            embedding=test_vector,
            limit=1000,
            distance_function="cosine",
            chunk_size="normal",
            provider_name="openai"
        )
    
    @pytest.mark.asyncio
    @patch('soegemaskine.searchapi.dhosearch.os.getenv')
    async def test_find_nærmeste_distance_threshold(self, mock_getenv):
        """Test find_nærmeste with different distance threshold."""
        # Setup mocks with lower threshold
        mock_getenv.return_value = "0.2"  # stricter threshold
        mock_db_results = [
            ("test.pdf", "Test Bog", "Test Forfatter", 42, "Dette er en test chunk.", 0.15),
            ("test.pdf", "Test Bog", "Test Forfatter", 43, "Dette er en anden test chunk.", 0.25),  # Exceeds threshold
            ("test.pdf", "Test Bog", "Test Forfatter", 44, "Dette er en tredje test chunk.", 0.30)  # Exceeds threshold
        ]
        
        # Set up global variables
        dhosearch.db_service = AsyncMock()
        dhosearch.db_service.vector_search = AsyncMock(return_value=mock_db_results)
        
        dhosearch.embedding_provider = MagicMock()
        dhosearch.embedding_provider.get_provider_name = MagicMock(return_value="openai")
        
        # Call the function
        test_vector = [0.1] * 1536
        results = await find_nærmeste(test_vector)
        
        # Verify results - should only include the first result with distance < 0.2
        assert len(results) == 1
        assert results[0][0] == "test.pdf"
        assert results[0][3] == 42  # page number
    
    @pytest.mark.asyncio
    @patch('soegemaskine.searchapi.dhosearch.os.getenv')
    async def test_find_nærmeste_short_chunks_filtered(self, mock_getenv):
        """Test that short chunks are filtered out."""
        # Setup mocks
        mock_getenv.return_value = "0.5"  # distance threshold
        mock_db_results = [
            ("test.pdf", "Test Bog", "Test Forfatter", 42, "Dette er en test chunk.", 0.15),
            ("test.pdf", "Test Bog", "Test Forfatter", 43, "For kort", 0.25),  # Too short, < 20 chars
            ("test.pdf", "Test Bog", "Test Forfatter", 44, "     ", 0.30)  # Too short after strip
        ]
        
        # Set up global variables
        dhosearch.db_service = AsyncMock()
        dhosearch.db_service.vector_search = AsyncMock(return_value=mock_db_results)
        
        dhosearch.embedding_provider = MagicMock()
        dhosearch.embedding_provider.get_provider_name = MagicMock(return_value="openai")
        
        # Call the function
        test_vector = [0.1] * 1536
        results = await find_nærmeste(test_vector)
        
        # Verify results - short chunks should be filtered out
        assert len(results) == 1
        assert results[0][0] == "test.pdf"
        assert results[0][3] == 42  # page number
    
    @pytest.mark.asyncio
    @patch('soegemaskine.searchapi.dhosearch.os.getenv')
    async def test_find_nærmeste_database_error(self, mock_getenv):
        """Test find_nærmeste with database error."""
        # Setup mocks
        mock_getenv.return_value = "0.5"  # distance threshold
        
        # Set up global variables
        dhosearch.db_service = AsyncMock()
        dhosearch.db_service.vector_search = AsyncMock(side_effect=Exception("Database error"))
        
        dhosearch.embedding_provider = MagicMock()
        dhosearch.embedding_provider.get_provider_name = MagicMock(return_value="openai")
        
        # Call the function
        test_vector = [0.1] * 1536
        
        # Mock print to avoid cluttering test output
        with patch('soegemaskine.searchapi.dhosearch.print'):
            results = await find_nærmeste(test_vector)
        
        # Verify results - should return empty list on error
        assert len(results) == 0
    
    @pytest.mark.asyncio
    @patch('soegemaskine.searchapi.dhosearch.os.getenv')
    async def test_find_nærmeste_provider_name_none(self, mock_getenv):
        """Test find_nærmeste when provider_name is None."""
        # Setup mocks
        mock_getenv.return_value = "0.5"  # distance threshold
        mock_db_results = [
            ("test.pdf", "Test Bog", "Test Forfatter", 42, "Dette er en test chunk.", 0.15)
        ]
        
        # Set up global variables
        dhosearch.db_service = AsyncMock()
        dhosearch.db_service.vector_search = AsyncMock(return_value=mock_db_results)
        
        # Provider doesn't have get_provider_name method
        dhosearch.embedding_provider = MagicMock()
        if hasattr(dhosearch.embedding_provider, 'get_provider_name'):
            delattr(dhosearch.embedding_provider, 'get_provider_name')
        
        # Call the function
        test_vector = [0.1] * 1536
        results = await find_nærmeste(test_vector)
        
        # Verify results
        assert len(results) == 1
        
        # Verify the DB call - provider_name should be None
        dhosearch.db_service.vector_search.assert_called_once_with(
            embedding=test_vector,
            limit=1000,
            distance_function="cosine",
            chunk_size="normal",
            provider_name=None
        )

@pytest.mark.unit
class TestExtractTextFromChunk:
    """Test the extract_text_from_chunk function."""
    
    def test_extract_text_basic(self):
        """Test basic text extraction."""
        chunk = "Dette er en almindelig tekst uden titel markering."
        
        result = extract_text_from_chunk(chunk)
        
        assert result == chunk
    
    def test_extract_text_with_title(self):
        """Test text extraction with title markup."""
        chunk = "##BOGTITEL##Dette er teksten efter bogtitlen."
        
        result = extract_text_from_chunk(chunk)
        
        assert result == "Dette er teksten efter bogtitlen."
    
    def test_extract_text_complex_title(self):
        """Test text extraction with complex title."""
        chunk = "##NIELS BUCH LEVIN: BREVE FRA 1846-1854##Her begynder den egentlige tekst."
        
        result = extract_text_from_chunk(chunk)
        
        assert result == "Her begynder den egentlige tekst."
    
    def test_extract_text_empty_after_title(self):
        """Test text extraction when nothing follows the title."""
        chunk = "##BOGTITEL##"
        
        result = extract_text_from_chunk(chunk)
        
        assert result == ""
    
    def test_extract_text_only_title(self):
        """Test text extraction when there's only a title without ending ##."""
        chunk = "##BOGTITEL"  # Note: This only has one ## delimiter
        
        # With our improved implementation, this should return an empty string
        # since there's nothing after the title marker
        result = extract_text_from_chunk(chunk)
        assert result == ""
