"""
Utility functions for testing the semantic search prototype.

Provides common test data, helper functions, and utilities used across test files.
"""

import asyncio
import functools
import json
import os
import random
import time
from typing import Dict, List, Any
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock


class TestDataGenerator:
    """Generate test data for various test scenarios."""
    
    @staticmethod
    def create_sample_book(book_id: str = "test_book_123") -> Dict[str, Any]:
        """Create a sample book for testing."""
        return {
            "book_id": book_id,
            "title": f"Test Bog {book_id}",
            "author": "Test Forfatter",
            "publication_year": 2023,
            "content": "Dette er test indhold for en bog om dansk historie og kultur. "
                      "Bogen indeholder information om traditioner, samfund og værdier.",
            "metadata": {
                "pages": 150,
                "language": "da",
                "category": "historie"
            }
        }
    
    @staticmethod
    def create_sample_chunks(book_id: str = "test_book_123", count: int = 3) -> List[Dict[str, Any]]:
        """Create sample text chunks for testing."""
        chunks = []
        base_texts = [
            "Dette er den første chunk om dansk historie.",
            "Anden chunk handler om danske traditioner og kultur.",
            "Tredje chunk indeholder information om samfund og værdier.",
            "Fjerde chunk beskriver historiske begivenheder.",
            "Femte chunk fokuserer på moderne dansk kultur."
        ]
        
        for i in range(count):
            chunks.append({
                "book_id": book_id,
                "chunk_index": i,
                "chunk_text": base_texts[i % len(base_texts)],
                "chunk_size": len(base_texts[i % len(base_texts)]),
                "embedding": [random.uniform(-1, 1) for _ in range(1536)]  # Mock embedding
            })
        
        return chunks
    
    @staticmethod
    def create_sample_search_results(count: int = 5) -> List[Dict[str, Any]]:
        """Create sample search results for testing."""
        results = []
        titles = [
            "Danmarks Historie",
            "Danske Traditioner", 
            "Kulturhistorie",
            "Samfund og Værdier",
            "Moderne Danmark"
        ]
        
        for i in range(count):
            results.append({
                "book_id": f"book_{i+1}",
                "title": titles[i % len(titles)],
                "chunk_text": f"Dette er chunk {i+1} med relevant indhold om emnet.",
                "similarity": round(0.95 - (i * 0.05), 2),  # Decreasing similarity
                "chunk_index": i,
                "metadata": {
                    "relevance_score": round(0.9 - (i * 0.04), 2),
                    "content_type": "text"
                }
            })
        
        return results
    
    @staticmethod
    def create_sample_embeddings(dimension: int = 1536) -> List[float]:
        """Create sample embeddings for testing."""
        return [random.uniform(-1, 1) for _ in range(dimension)]
    
    @staticmethod
    def create_sample_queries() -> List[str]:
        """Create sample search queries for testing."""
        return [
            "dansk historie",
            "traditioner og kultur",
            "samfund og værdier",
            "historiske begivenheder",
            "moderne Danmark",
            "danske skikke",
            "kulturarv",
            "social udvikling"
        ]


class MockResponseGenerator:
    """Generate mock API responses for testing."""
    
    @staticmethod
    def openai_embedding_response(text: str, dimension: int = 1536) -> Dict[str, Any]:
        """Generate mock OpenAI embedding API response."""
        return {
            "object": "list",
            "data": [
                {
                    "object": "embedding",
                    "index": 0,
                    "embedding": [random.uniform(-1, 1) for _ in range(dimension)]
                }
            ],
            "model": "text-embedding-ada-002",
            "usage": {
                "prompt_tokens": len(text.split()),
                "total_tokens": len(text.split())
            }
        }
    
    @staticmethod
    def database_search_response(query: str, limit: int = 10) -> List[tuple]:
        """Generate mock database search response."""
        results = []
        for i in range(min(limit, 5)):  # Max 5 mock results
            results.append((
                f"book_{i+1}",                                    # book_id
                f"Test Bog {i+1}",                              # title
                f"Dette er chunk {i+1} relateret til '{query}'", # chunk_text
                round(0.95 - (i * 0.05), 2),                   # similarity
                i                                               # chunk_index
            ))
        return results
    
    @staticmethod
    def api_search_response(query: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate mock API search response."""
        return {
            "query": query,
            "results": results,
            "total": len(results),
            "limit": 10,
            "offset": 0,
            "processing_time_ms": random.randint(50, 200),
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def api_error_response(error_message: str, status_code: int = 400) -> Dict[str, Any]:
        """Generate mock API error response."""
        return {
            "error": {
                "message": error_message,
                "type": "validation_error" if status_code == 400 else "server_error",
                "code": status_code
            },
            "timestamp": datetime.now().isoformat()
        }


class TestAssertions:
    """Common assertion helpers for tests."""
    
    @staticmethod
    def assert_valid_embedding(embedding: List[float], expected_dimension: int = 1536):
        """Assert that an embedding is valid."""
        assert isinstance(embedding, list), "Embedding should be a list"
        assert len(embedding) == expected_dimension, f"Embedding should have {expected_dimension} dimensions"
        assert all(isinstance(x, (int, float)) for x in embedding), "All embedding values should be numeric"
        assert all(-2 <= x <= 2 for x in embedding), "Embedding values should be in reasonable range"
    
    @staticmethod
    def assert_valid_search_result(result: Dict[str, Any]):
        """Assert that a search result has required fields."""
        required_fields = ["book_id", "title", "chunk_text", "similarity", "chunk_index"]
        for field in required_fields:
            assert field in result, f"Search result missing required field: {field}"
        
        assert isinstance(result["similarity"], (int, float)), "Similarity should be numeric"
        assert 0 <= result["similarity"] <= 1, "Similarity should be between 0 and 1"
        assert isinstance(result["chunk_index"], int), "Chunk index should be integer"
        assert result["chunk_index"] >= 0, "Chunk index should be non-negative"
    
    @staticmethod
    def assert_search_results_ordered(results: List[Dict[str, Any]]):
        """Assert that search results are ordered by similarity (descending)."""
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i]["similarity"] >= results[i + 1]["similarity"], \
                    "Search results should be ordered by similarity (descending)"
    
    @staticmethod
    def assert_api_response_format(response: Dict[str, Any]):
        """Assert that API response has proper format."""
        assert isinstance(response, dict), "API response should be a dictionary"
        
        if "error" not in response:
            # Success response
            required_fields = ["query", "results", "total"]
            for field in required_fields:
                assert field in response, f"API response missing required field: {field}"
            
            assert isinstance(response["results"], list), "Results should be a list"
            assert isinstance(response["total"], int), "Total should be an integer"
            assert response["total"] >= 0, "Total should be non-negative"
        else:
            # Error response
            assert "error" in response, "Error response should have error field"
            assert isinstance(response["error"], dict), "Error should be a dictionary"


class TestHelpers:
    """Helper functions for common test operations."""
    
    @staticmethod
    def create_mock_database_connection():
        """Create a mock database connection for testing."""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
        
        # Default empty results
        mock_cursor.fetchall.return_value = []
        mock_cursor.fetchone.return_value = None
        mock_cursor.rowcount = 0
        
        return mock_conn
    
    @staticmethod
    def create_mock_openai_client():
        """Create a mock OpenAI client for testing."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3] * 512)]
        
        mock_client.embeddings.create.return_value = mock_response
        return mock_client
    
    @staticmethod
    def simulate_api_delay(min_ms: int = 10, max_ms: int = 100):
        """Simulate API response delay for testing."""
        import asyncio
        import random
        
        async def delay():
            delay_ms = random.randint(min_ms, max_ms)
            await asyncio.sleep(delay_ms / 1000)
        
        return delay()
    
    @staticmethod
    def create_test_environment_config() -> Dict[str, Any]:
        """Create test environment configuration."""
        return {
            "database": {
                "url": "postgresql://test:test@localhost:5432/test_db",
                "pool_size": 5,
                "timeout": 30
            },
            "openai": {
                "api_key": "test_api_key",
                "model": "text-embedding-ada-002",
                "max_tokens": 8000,
                "timeout": 30
            },
            "search": {
                "default_limit": 10,
                "max_limit": 100,
                "default_chunk_size": 1000,
                "supported_chunk_sizes": [500, 1000, 1500, 2000],
                "default_distance_function": "cosine",
                "supported_distance_functions": ["cosine", "euclidean", "dot_product"]
            },
            "api": {
                "host": "localhost",
                "port": 8000,
                "debug": True,
                "cors_origins": ["http://localhost:3000"]
            }
        }
    
    @staticmethod
    def save_test_results(test_name: str, results: Dict[str, Any], output_dir: str = "test_output"):
        """Save test results to file for analysis."""
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{test_name}_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        
        test_data = {
            "test_name": test_name,
            "timestamp": datetime.now().isoformat(),
            "results": results
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, indent=2, ensure_ascii=False)
        
        return filepath


class PerformanceTestHelpers:
    """Helpers for performance testing."""
    
    @staticmethod
    def measure_execution_time(func):
        """Decorator to measure function execution time."""
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)
            end_time = time.time()
            execution_time = (end_time - start_time) * 1000  # Convert to ms
            
            if hasattr(result, '__dict__'):
                result.execution_time_ms = execution_time
            elif isinstance(result, dict):
                result['execution_time_ms'] = execution_time
            
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            execution_time = (end_time - start_time) * 1000  # Convert to ms
            
            if hasattr(result, '__dict__'):
                result.execution_time_ms = execution_time
            elif isinstance(result, dict):
                result['execution_time_ms'] = execution_time
            
            return result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    @staticmethod
    def create_load_test_data(num_queries: int = 100) -> List[str]:
        """Create data for load testing."""
        import random
        
        base_queries = TestDataGenerator.create_sample_queries()
        queries = []
        
        for i in range(num_queries):
            base_query = random.choice(base_queries)
            # Add variation to queries
            variations = [
                base_query,
                f"{base_query} information",
                f"om {base_query}",
                f"{base_query} historie",
                f"moderne {base_query}"
            ]
            queries.append(random.choice(variations))
        
        return queries
