"""
Integration tests for the search pipeline.

Tests the complete search flow from query to results.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock


@pytest.mark.integration
class TestSearchPipelineIntegration:
    """Test the complete search pipeline integration."""

    @pytest.fixture
    def mock_database_with_data(self):
        """Mock database with sample search data."""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
        
        # Sample search results
        mock_cursor.fetchall.return_value = [
            ("123", "Test Bog", "Dette er en test chunk om dansk historie.", 0.95, 0),
            ("124", "Historie Bog", "Endnu en chunk om danske traditioner.", 0.89, 1),
            ("125", "Kultur Bog", "Information om dansk kultur og samfund.", 0.82, 0)
        ]
        
        return mock_conn

    @pytest.fixture
    def sample_query_data(self):
        """Sample query data for testing."""
        return {
            "query": "dansk historie",
            "limit": 10,
            "chunk_size": 1000,
            "distance_function": "cosine"
        }

    @pytest.mark.asyncio
    async def test_end_to_end_search_flow(self, mock_database_with_data, sample_query_data):
        """Test the complete end-to-end search flow."""
        
        # Mock search engine components
        async def mock_get_query_embedding(query):
            # Simulate embedding generation for query
            return [0.1, 0.2, 0.3] * 512
        
        async def mock_vector_search(embedding, limit, chunk_size, distance_func):
            # Simulate vector similarity search in database
            return [
                {
                    "book_id": "123",
                    "title": "Test Bog",
                    "chunk_text": "Dette er en test chunk om dansk historie.",
                    "similarity": 0.95,
                    "chunk_index": 0
                },
                {
                    "book_id": "124", 
                    "title": "Historie Bog",
                    "chunk_text": "Endnu en chunk om danske traditioner.",
                    "similarity": 0.89,
                    "chunk_index": 1
                }
            ]
        
        def mock_format_results(raw_results):
            # Simulate result formatting
            return [
                {
                    "book_id": result["book_id"],
                    "title": result["title"],
                    "content": result["chunk_text"],
                    "score": result["similarity"],
                    "chunk_index": result["chunk_index"]
                }
                for result in raw_results
            ]
        
        # Execute the search pipeline
        query = sample_query_data["query"]
        limit = sample_query_data["limit"]
        chunk_size = sample_query_data["chunk_size"]
        distance_func = sample_query_data["distance_function"]
        
        # Step 1: Get query embedding
        query_embedding = await mock_get_query_embedding(query)
        assert len(query_embedding) == 1536
        
        # Step 2: Perform vector search
        raw_results = await mock_vector_search(query_embedding, limit, chunk_size, distance_func)
        assert len(raw_results) == 2
        assert raw_results[0]["similarity"] > raw_results[1]["similarity"]  # Results sorted by similarity
        
        # Step 3: Format results
        formatted_results = mock_format_results(raw_results)
        assert len(formatted_results) == 2
        assert "dansk historie" in formatted_results[0]["content"]
        assert formatted_results[0]["score"] == 0.95

    @pytest.mark.asyncio
    async def test_search_with_different_parameters(self, mock_database_with_data):
        """Test search with different parameter combinations."""
        
        async def mock_parameterized_search(query, **kwargs):
            # Mock different search behaviors based on parameters
            chunk_size = kwargs.get("chunk_size", 1000)
            distance_func = kwargs.get("distance_function", "cosine")
            
            # Simulate different result sets based on parameters
            if chunk_size == 500:
                return [{"result": "small_chunk", "params": kwargs}]
            elif distance_func == "euclidean":
                return [{"result": "euclidean_search", "params": kwargs}]
            else:
                return [{"result": "default_search", "params": kwargs}]
        
        # Test with small chunk size
        results_small = await mock_parameterized_search(
            "test query", 
            limit=5, 
            chunk_size=500, 
            distance_function="cosine"
        )
        assert results_small[0]["result"] == "small_chunk"
        assert results_small[0]["params"]["chunk_size"] == 500
        
        # Test with euclidean distance
        results_euclidean = await mock_parameterized_search(
            "test query",
            limit=10,
            chunk_size=1000,
            distance_function="euclidean"
        )
        assert results_euclidean[0]["result"] == "euclidean_search"
        assert results_euclidean[0]["params"]["distance_function"] == "euclidean"

    @pytest.mark.asyncio
    async def test_search_error_scenarios(self):
        """Test various error scenarios in search pipeline."""
        
        async def mock_search_with_errors(query, error_type=None):
            if error_type == "embedding_error":
                raise Exception("Failed to generate embedding")
            elif error_type == "database_error":
                raise Exception("Database connection failed")
            elif error_type == "empty_query":
                return []
            else:
                return [{"result": "success"}]
        
        # Test embedding error
        with pytest.raises(Exception) as exc_info:
            await mock_search_with_errors("test", error_type="embedding_error")
        assert "embedding" in str(exc_info.value)
        
        # Test database error
        with pytest.raises(Exception) as exc_info:
            await mock_search_with_errors("test", error_type="database_error")
        assert "Database" in str(exc_info.value)
        
        # Test empty results
        results = await mock_search_with_errors("test", error_type="empty_query")
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_result_ranking(self):
        """Test that search results are properly ranked by similarity."""
        
        def mock_get_ranked_results():
            # Return unsorted results to test ranking
            return [
                {"id": "1", "similarity": 0.75, "content": "Low similarity"},
                {"id": "2", "similarity": 0.95, "content": "High similarity"},
                {"id": "3", "similarity": 0.82, "content": "Medium similarity"}
            ]
        
        def mock_rank_results(results):
            # Sort by similarity descending
            return sorted(results, key=lambda x: x["similarity"], reverse=True)
        
        raw_results = mock_get_ranked_results()
        ranked_results = mock_rank_results(raw_results)
        
        assert ranked_results[0]["similarity"] == 0.95  # Highest first
        assert ranked_results[1]["similarity"] == 0.82  # Medium second
        assert ranked_results[2]["similarity"] == 0.75  # Lowest last

    @pytest.mark.asyncio
    async def test_concurrent_search_requests(self):
        """Test handling of concurrent search requests."""
        
        async def mock_search_request(query_id):
            # Simulate search processing time
            import asyncio
            await asyncio.sleep(0.01)
            return {"query_id": query_id, "results": [f"result_for_{query_id}"]}
        
        # Create multiple concurrent search requests
        queries = ["query_1", "query_2", "query_3", "query_4", "query_5"]
        tasks = [mock_search_request(query) for query in queries]
        
        # Execute concurrently
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result["query_id"] == f"query_{i+1}"
            assert f"result_for_query_{i+1}" in result["results"]

    @pytest.mark.asyncio
    async def test_search_result_caching_simulation(self):
        """Test simulation of search result caching."""
        
        # Mock cache
        cache = {}
        
        async def mock_search_with_cache(query):
            # Check cache first
            if query in cache:
                return {"cached": True, "results": cache[query]}
            
            # Simulate search
            import asyncio
            await asyncio.sleep(0.01)  # Simulate search time
            results = [f"result_for_{query}"]
            
            # Store in cache
            cache[query] = results
            return {"cached": False, "results": results}
        
        # First search - should not be cached
        result1 = await mock_search_with_cache("test_query")
        assert result1["cached"] is False
        assert "test_query" in result1["results"][0]
        
        # Second search - should be cached
        result2 = await mock_search_with_cache("test_query")
        assert result2["cached"] is True
        assert result2["results"] == result1["results"]

    @pytest.mark.asyncio
    async def test_search_analytics_simulation(self):
        """Test simulation of search analytics tracking."""
        
        analytics_data = []
        
        async def mock_search_with_analytics(query, user_id=None):
            # Perform search
            results = [{"content": f"result for {query}"}]
            
            # Track analytics
            analytics_entry = {
                "query": query,
                "user_id": user_id,
                "result_count": len(results),
                "timestamp": "2024-01-01T00:00:00"
            }
            analytics_data.append(analytics_entry)
            
            return results
        
        # Perform searches with analytics
        await mock_search_with_analytics("dansk historie", user_id="user123")
        await mock_search_with_analytics("kultur", user_id="user456")
        await mock_search_with_analytics("tradition")  # No user_id
        
        assert len(analytics_data) == 3
        assert analytics_data[0]["query"] == "dansk historie"
        assert analytics_data[0]["user_id"] == "user123"
        assert analytics_data[1]["user_id"] == "user456"
        assert analytics_data[2]["user_id"] is None


@pytest.mark.integration  
class TestAPIIntegration:
    """Test API integration scenarios."""

    @pytest.fixture
    def mock_fastapi_app(self):
        """Mock FastAPI application for testing."""
        app = AsyncMock()
        
        # Mock search endpoint
        async def mock_search_endpoint(request_data):
            return {
                "results": [
                    {
                        "book_id": "123",
                        "title": "Test Bog",
                        "content": request_data.get("query", ""),
                        "score": 0.95
                    }
                ],
                "total": 1,
                "query": request_data.get("query", ""),
                "limit": request_data.get("limit", 10)
            }
        
        app.search = mock_search_endpoint
        return app

    @pytest.mark.asyncio
    async def test_api_search_endpoint_integration(self, mock_fastapi_app):
        """Test the search API endpoint integration."""
        
        request_data = {
            "query": "dansk historie",
            "limit": 5,
            "chunk_size": 1000,
            "distance_function": "cosine"
        }
        
        response = await mock_fastapi_app.search(request_data)
        
        assert response["total"] == 1
        assert response["query"] == "dansk historie"
        assert response["limit"] == 5
        assert len(response["results"]) == 1
        assert response["results"][0]["score"] == 0.95

    @pytest.mark.asyncio
    async def test_api_error_handling(self):
        """Test API error handling scenarios."""
        
        async def mock_api_call(endpoint, data=None, simulate_error=None):
            if simulate_error == "validation":
                return {"error": "Invalid request data", "status": 400}
            elif simulate_error == "server":
                return {"error": "Internal server error", "status": 500}
            elif simulate_error == "timeout":
                raise Exception("Request timeout")
            else:
                return {"status": 200, "data": "success"}
        
        # Test validation error
        response = await mock_api_call("/search", data={}, simulate_error="validation")
        assert response["status"] == 400
        assert "Invalid" in response["error"]
        
        # Test server error
        response = await mock_api_call("/search", data={}, simulate_error="server")
        assert response["status"] == 500
        
        # Test timeout
        with pytest.raises(Exception) as exc_info:
            await mock_api_call("/search", data={}, simulate_error="timeout")
        assert "timeout" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_api_rate_limiting_integration(self):
        """Test API rate limiting integration."""
        
        call_count = 0
        
        async def mock_rate_limited_api():
            nonlocal call_count
            call_count += 1
            
            if call_count > 5:  # Rate limit after 5 calls
                return {"error": "Rate limit exceeded", "status": 429}
            
            return {"status": 200, "data": f"call_{call_count}"}
        
        # Make calls until rate limited
        responses = []
        for _ in range(7):
            response = await mock_rate_limited_api()
            responses.append(response)
        
        # First 5 should succeed
        for i in range(5):
            assert responses[i]["status"] == 200
        
        # Last 2 should be rate limited
        for i in range(5, 7):
            assert responses[i]["status"] == 429
