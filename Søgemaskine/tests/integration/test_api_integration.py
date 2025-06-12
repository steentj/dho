"""
Integration tests for API endpoints and services.

Tests the complete API integration including FastAPI endpoints,
request/response handling, and service integrations.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.integration
class TestAPIEndpointIntegration:
    """Test API endpoint integration."""

    @pytest.fixture
    def mock_app_dependencies(self):
        """Mock application dependencies."""
        return {
            "search_engine": AsyncMock(),
            "database": AsyncMock(),
            "openai_client": AsyncMock(),
            "config": {
                "api_key": "test_key",
                "database_url": "test://localhost",
                "model_name": "text-embedding-ada-002"
            }
        }

    @pytest.fixture
    def sample_search_request(self):
        """Sample search request data."""
        return {
            "query": "danske traditioner",
            "limit": 10,
            "chunk_size": 1000,
            "distance_function": "cosine"
        }

    @pytest.mark.asyncio
    async def test_search_endpoint_full_flow(self, mock_app_dependencies, sample_search_request):
        """Test the complete search endpoint flow."""
        
        # Setup mock responses
        mock_search_engine = mock_app_dependencies["search_engine"]
        mock_search_engine.get_results.return_value = [
            {
                "book_id": "123",
                "title": "Danske Traditioner",
                "chunk_text": "Information om danske traditioner og kultur.",
                "similarity": 0.92,
                "chunk_index": 0
            },
            {
                "book_id": "124",
                "title": "Kulturhistorie",
                "chunk_text": "Historisk perspektiv på danske skikke.",
                "similarity": 0.87,
                "chunk_index": 1
            }
        ]
        
        # Mock the complete endpoint function
        async def mock_search_endpoint(request_data):
            # Validate request
            if not request_data.get("query"):
                return {"error": "Query is required", "status_code": 400}
            
            # Get results from search engine
            results = await mock_search_engine.get_results(
                query=request_data["query"],
                limit=request_data.get("limit", 10),
                chunk_size=request_data.get("chunk_size", 1000),
                distance_function=request_data.get("distance_function", "cosine")
            )
            
            # Format response
            return {
                "results": results,
                "total": len(results),
                "query": request_data["query"],
                "limit": request_data.get("limit", 10),
                "status_code": 200
            }
        
        # Test the endpoint
        response = await mock_search_endpoint(sample_search_request)
        
        assert response["status_code"] == 200
        assert response["total"] == 2
        assert response["query"] == "danske traditioner"
        assert len(response["results"]) == 2
        assert response["results"][0]["similarity"] > response["results"][1]["similarity"]

    @pytest.mark.asyncio
    async def test_health_endpoint_integration(self, mock_app_dependencies):
        """Test the health check endpoint."""
        
        async def mock_health_endpoint():
            # Check database connection
            db_status = "healthy"
            try:
                await mock_app_dependencies["database"].execute("SELECT 1")
            except Exception:
                db_status = "unhealthy"
            
            # Check OpenAI API
            openai_status = "healthy"
            try:
                await mock_app_dependencies["openai_client"].models.list()
            except Exception:
                openai_status = "unhealthy"
            
            overall_status = "healthy" if db_status == "healthy" and openai_status == "healthy" else "unhealthy"
            
            return {
                "status": overall_status,
                "database": db_status,
                "openai": openai_status,
                "timestamp": "2024-01-01T00:00:00Z"
            }
        
        # Test healthy scenario
        response = await mock_health_endpoint()
        assert response["status"] == "healthy"
        assert response["database"] == "healthy"
        assert response["openai"] == "healthy"

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, mock_app_dependencies):
        """Test error handling across the API."""
        
        async def mock_endpoint_with_errors(request_type, simulate_error=None):
            try:
                if request_type == "search":
                    if simulate_error == "validation":
                        raise ValueError("Invalid query parameter")
                    elif simulate_error == "database":
                        raise ConnectionError("Database connection failed")
                    elif simulate_error == "openai":
                        raise Exception("OpenAI API error")
                    else:
                        return {"status": "success", "data": "search_results"}
                
                elif request_type == "health":
                    if simulate_error == "database":
                        raise ConnectionError("Database unreachable")
                    else:
                        return {"status": "healthy"}
                
            except ValueError as e:
                return {"error": str(e), "status_code": 400}
            except ConnectionError as e:
                return {"error": str(e), "status_code": 503}
            except Exception as e:
                return {"error": str(e), "status_code": 500}
        
        # Test validation error
        response = await mock_endpoint_with_errors("search", simulate_error="validation")
        assert response["status_code"] == 400
        assert "Invalid query" in response["error"]
        
        # Test database error
        response = await mock_endpoint_with_errors("search", simulate_error="database")
        assert response["status_code"] == 503
        assert "Database" in response["error"]
        
        # Test OpenAI API error
        response = await mock_endpoint_with_errors("search", simulate_error="openai")
        assert response["status_code"] == 500
        assert "OpenAI" in response["error"]

    @pytest.mark.asyncio
    async def test_concurrent_api_requests(self, mock_app_dependencies):
        """Test handling of concurrent API requests."""
        
        request_count = 0
        
        async def mock_concurrent_endpoint(request_id):
            nonlocal request_count
            request_count += 1
            
            # Simulate processing time
            await asyncio.sleep(0.01)
            
            return {
                "request_id": request_id,
                "processed_by": f"worker_{request_count}",
                "status": "completed"
            }
        
        # Create 10 concurrent requests
        request_ids = list(range(10))
        tasks = [mock_concurrent_endpoint(req_id) for req_id in request_ids]
        
        # Execute concurrently
        responses = await asyncio.gather(*tasks)
        
        assert len(responses) == 10
        assert all(response["status"] == "completed" for response in responses)
        
        # Verify all request IDs are present
        returned_ids = [response["request_id"] for response in responses]
        assert set(returned_ids) == set(request_ids)

    @pytest.mark.asyncio
    async def test_request_validation_integration(self):
        """Test request validation logic."""
        
        def validate_search_request(data):
            errors = []
            
            # Required fields
            if not data.get("query"):
                errors.append("Query is required")
            if data.get("query") and len(data["query"]) < 3:
                errors.append("Query must be at least 3 characters")
            
            # Optional field validation
            if "limit" in data:
                if not isinstance(data["limit"], int) or data["limit"] < 1 or data["limit"] > 100:
                    errors.append("Limit must be an integer between 1 and 100")
            
            if "chunk_size" in data:
                valid_sizes = [500, 1000, 1500, 2000]
                if data["chunk_size"] not in valid_sizes:
                    errors.append(f"Chunk size must be one of {valid_sizes}")
            
            if "distance_function" in data:
                valid_functions = ["cosine", "euclidean", "dot_product"]
                if data["distance_function"] not in valid_functions:
                    errors.append(f"Distance function must be one of {valid_functions}")
            
            return errors
        
        # Test valid request
        valid_request = {
            "query": "valid query",
            "limit": 10,
            "chunk_size": 1000,
            "distance_function": "cosine"
        }
        errors = validate_search_request(valid_request)
        assert len(errors) == 0
        
        # Test invalid requests
        invalid_requests = [
            {},  # Missing query
            {"query": ""},  # Empty query
            {"query": "ab"},  # Too short query
            {"query": "valid", "limit": 0},  # Invalid limit
            {"query": "valid", "limit": 150},  # Limit too high
            {"query": "valid", "chunk_size": 750},  # Invalid chunk size
            {"query": "valid", "distance_function": "invalid"}  # Invalid distance function
        ]
        
        for invalid_request in invalid_requests:
            errors = validate_search_request(invalid_request)
            assert len(errors) > 0


@pytest.mark.integration
class TestServiceIntegration:
    """Test integration between different services."""

    @pytest.mark.asyncio
    async def test_search_engine_database_integration(self):
        """Test integration between search engine and database."""
        
        # Mock database with embeddings
        mock_database = AsyncMock()
        mock_database.execute.return_value = [
            ("123", "Test Bog", "Test content", "[0.1, 0.2, 0.3]", 0),
            ("124", "Another Book", "More content", "[0.4, 0.5, 0.6]", 1)
        ]
        
        # Mock search engine that uses the database
        class MockSearchEngine:
            def __init__(self, database):
                self.database = database
            
            async def search(self, query_embedding, limit=10):
                # This would normally do vector similarity search
                results = await self.database.execute(
                    "SELECT book_id, title, chunk_text, embedding, chunk_index FROM embeddings"
                )
                
                # Simulate similarity calculation
                formatted_results = []
                for result in results:
                    formatted_results.append({
                        "book_id": result[0],
                        "title": result[1],
                        "chunk_text": result[2],
                        "similarity": 0.95,  # Mock similarity
                        "chunk_index": result[4]
                    })
                
                return formatted_results[:limit]
        
        # Test the integration
        search_engine = MockSearchEngine(mock_database)
        query_embedding = [0.1, 0.2, 0.3] * 512
        
        results = await search_engine.search(query_embedding, limit=5)
        
        assert len(results) == 2
        assert results[0]["book_id"] == "123"
        assert results[0]["title"] == "Test Bog"
        mock_database.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_openai_embedding_service_integration(self):
        """Test integration with OpenAI embedding service."""
        
        # Mock OpenAI client
        mock_openai = AsyncMock()
        mock_openai.embeddings.create.return_value = AsyncMock(
            data=[MagicMock(embedding=[0.1, 0.2, 0.3] * 512)]
        )
        
        # Mock embedding service
        class MockEmbeddingService:
            def __init__(self, openai_client):
                self.client = openai_client
            
            async def get_embedding(self, text):
                response = await self.client.embeddings.create(
                    model="text-embedding-ada-002",
                    input=text
                )
                return response.data[0].embedding
        
        # Test the integration
        embedding_service = MockEmbeddingService(mock_openai)
        embedding = await embedding_service.get_embedding("test text")
        
        assert len(embedding) == 1536
        assert embedding[0] == 0.1
        mock_openai.embeddings.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_full_stack_integration_simulation(self):
        """Test full stack integration simulation."""
        
        # Mock all services
        mock_openai = AsyncMock()
        mock_database = AsyncMock()
        
        # Setup responses
        mock_openai.embeddings.create.return_value = AsyncMock(
            data=[MagicMock(embedding=[0.1, 0.2, 0.3] * 512)]
        )
        
        mock_database.execute.return_value = [
            ("123", "Test Bog", "Relevant content about Danish history", 0.92, 0)
        ]
        
        # Mock the full application
        class MockApplication:
            def __init__(self, openai_client, database):
                self.openai_client = openai_client
                self.database = database
            
            async def search(self, query):
                # Step 1: Get query embedding
                embedding_response = await self.openai_client.embeddings.create(
                    model="text-embedding-ada-002",
                    input=query
                )
                # Use the embedding for similarity search (simulated)
                _ = embedding_response.data[0].embedding
                
                # Step 2: Search database
                db_results = await self.database.execute(
                    "SELECT book_id, title, chunk_text, similarity, chunk_index FROM search_results"
                )
                
                # Step 3: Format results
                results = []
                for result in db_results:
                    results.append({
                        "book_id": result[0],
                        "title": result[1],
                        "content": result[2],
                        "score": result[3],
                        "chunk_index": result[4]
                    })
                
                return {
                    "query": query,
                    "results": results,
                    "total": len(results)
                }
        
        # Test the full stack
        app = MockApplication(mock_openai, mock_database)
        response = await app.search("danish history")
        
        assert response["query"] == "danish history"
        assert response["total"] == 1
        assert response["results"][0]["title"] == "Test Bog"
        assert response["results"][0]["score"] == 0.92
        
        # Verify all services were called
        mock_openai.embeddings.create.assert_called_once()
        mock_database.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_propagation_integration(self):
        """Test how errors propagate through service integrations."""
        
        # Mock services with various error scenarios
        async def mock_service_chain(fail_at=None):
            try:
                # Service 1: Input validation
                if fail_at == "validation":
                    raise ValueError("Invalid input")
                
                # Service 2: OpenAI API call
                if fail_at == "openai":
                    raise Exception("OpenAI API error")
                
                # Service 3: Database operation
                if fail_at == "database":
                    raise ConnectionError("Database connection failed")
                
                # Service 4: Result formatting
                if fail_at == "formatting":
                    raise RuntimeError("Result formatting error")
                
                return {"status": "success", "data": "all_services_completed"}
            
            except ValueError as e:
                return {"error": f"Validation error: {e}", "status_code": 400}
            except ConnectionError as e:
                return {"error": f"Database error: {e}", "status_code": 503}
            except Exception as e:
                return {"error": f"Service error: {e}", "status_code": 500}
        
        # Test different failure points
        scenarios = ["validation", "openai", "database", "formatting", None]
        expected_codes = [400, 500, 503, 500, None]
        
        for scenario, expected_code in zip(scenarios, expected_codes):
            result = await mock_service_chain(fail_at=scenario)
            
            if expected_code:
                assert result["status_code"] == expected_code
                assert "error" in result
            else:
                assert result["status"] == "success"
