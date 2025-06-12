"""
Tests for test utilities and mock services.

Validates that our testing infrastructure works correctly.
Note: These are simple validation tests using standard assertions.
"""

import asyncio
import pytest

from tests.utils.test_utils import (
    TestDataGenerator, MockResponseGenerator, TestAssertions, 
    TestHelpers, PerformanceTestHelpers
)
from tests.mocks.mock_services import (
    MockOpenAIService, MockDatabaseService, MockHTTPService,
    MockSearchEngine, MockServiceFactory
)


def test_data_generator_sample_book():
    """Test creating sample book data."""
    book = TestDataGenerator.create_sample_book("test_123")
    
    assert book["book_id"] == "test_123"
    assert "title" in book
    assert "author" in book
    assert "content" in book
    assert "metadata" in book
    assert isinstance(book["metadata"], dict)
    print("✓ TestDataGenerator.create_sample_book() works correctly")


def test_data_generator_sample_chunks():
    """Test creating sample text chunks."""
    chunks = TestDataGenerator.create_sample_chunks("book_123", 3)
    
    assert len(chunks) == 3
    for i, chunk in enumerate(chunks):
        assert chunk["book_id"] == "book_123"
        assert chunk["chunk_index"] == i
        assert "chunk_text" in chunk
        assert "embedding" in chunk
        assert len(chunk["embedding"]) == 1536
    print("✓ TestDataGenerator.create_sample_chunks() works correctly")


def test_data_generator_search_results():
    """Test creating sample search results."""
    results = TestDataGenerator.create_sample_search_results(5)
    
    assert len(results) == 5
    for i, result in enumerate(results):
        assert result["similarity"] == round(0.95 - (i * 0.05), 2)
        TestAssertions.assert_valid_search_result(result)
    
    TestAssertions.assert_search_results_ordered(results)
    print("✓ TestDataGenerator.create_sample_search_results() works correctly")


def test_data_generator_embeddings():
    """Test creating sample embeddings."""
    embedding = TestDataGenerator.create_sample_embeddings(1536)
    
    TestAssertions.assert_valid_embedding(embedding, 1536)
    print("✓ TestDataGenerator.create_sample_embeddings() works correctly")


def test_mock_response_generator_openai():
    """Test OpenAI embedding response generation."""
    response = MockResponseGenerator.openai_embedding_response("test text")
    
    assert response["object"] == "list"
    assert len(response["data"]) == 1
    assert response["data"][0]["object"] == "embedding"
    assert len(response["data"][0]["embedding"]) == 1536
    assert "usage" in response
    print("✓ MockResponseGenerator.openai_embedding_response() works correctly")


def test_mock_response_generator_database():
    """Test database search response generation."""
    results = MockResponseGenerator.database_search_response("test query", 3)
    
    assert len(results) <= 3
    for result in results:
        assert len(result) == 5  # book_id, title, chunk_text, similarity, chunk_index
        assert isinstance(result[3], float)  # similarity
        assert 0 <= result[3] <= 1  # similarity range
    print("✓ MockResponseGenerator.database_search_response() works correctly")


def test_mock_response_generator_api():
    """Test API search response generation."""
    sample_results = TestDataGenerator.create_sample_search_results(3)
    response = MockResponseGenerator.api_search_response("test query", sample_results)
    
    TestAssertions.assert_api_response_format(response)
    assert response["query"] == "test query"
    assert len(response["results"]) == 3
    print("✓ MockResponseGenerator.api_search_response() works correctly")


def test_test_assertions_valid_embedding():
    """Test valid embedding assertion."""
    embedding = [0.1, -0.5, 0.8] * 512  # 1536 dimensions
    TestAssertions.assert_valid_embedding(embedding)
    
    # Test invalid cases
    try:
        TestAssertions.assert_valid_embedding([0.1, 0.2])  # Wrong dimension
        assert False, "Should have raised AssertionError"
    except AssertionError:
        pass  # Expected
    
    print("✓ TestAssertions.assert_valid_embedding() works correctly")


def test_test_assertions_search_results():
    """Test search result validation."""
    result = TestDataGenerator.create_sample_search_results(1)[0]
    TestAssertions.assert_valid_search_result(result)
    
    # Test invalid case
    try:
        TestAssertions.assert_valid_search_result({"incomplete": "data"})
        assert False, "Should have raised AssertionError"
    except AssertionError:
        pass  # Expected
    
    print("✓ TestAssertions.assert_valid_search_result() works correctly")


def test_test_helpers_mock_creation():
    """Test mock helper creation."""
    mock_conn = TestHelpers.create_mock_database_connection()
    assert mock_conn is not None
    assert hasattr(mock_conn, 'cursor')
    
    mock_client = TestHelpers.create_mock_openai_client()
    assert mock_client is not None
    assert hasattr(mock_client, 'embeddings')
    
    print("✓ TestHelpers mock creation works correctly")


def test_test_helpers_config():
    """Test test environment configuration creation."""
    config = TestHelpers.create_test_environment_config()
    
    assert "database" in config
    assert "openai" in config
    assert "search" in config
    assert "api" in config
    
    assert config["database"]["url"].startswith("postgresql://")
    assert config["openai"]["model"] == "text-embedding-ada-002"
    print("✓ TestHelpers.create_test_environment_config() works correctly")


@pytest.mark.asyncio
async def test_performance_helpers():
    """Test performance measurement helpers."""
    @PerformanceTestHelpers.measure_execution_time
    async def test_async_func():
        await asyncio.sleep(0.1)
        return {"result": "success"}
    
    result = await test_async_func()
    
    assert "execution_time_ms" in result
    assert result["execution_time_ms"] >= 100  # At least 100ms
    assert result["result"] == "success"
    
    print("✓ PerformanceTestHelpers.measure_execution_time() works correctly")


@pytest.mark.asyncio
async def test_mock_openai_service():
    """Test the mock OpenAI service."""
    service = MockOpenAIService()
    
    response = await service.create_embedding("test text")
    
    assert response["object"] == "list"
    assert len(response["data"]) == 1
    assert len(response["data"][0]["embedding"]) == 1536
    assert service.call_count == 1
    
    # Test caching
    response2 = await service.create_embedding("test text")
    assert response["data"][0]["embedding"] == response2["data"][0]["embedding"]
    assert service.call_count == 2
    assert len(service.embeddings_cache) == 1
    
    print("✓ MockOpenAIService works correctly")


@pytest.mark.asyncio
async def test_mock_database_service():
    """Test the mock database service."""
    service = MockDatabaseService()
    
    # Test connection
    assert not service.connected
    await service.connect()
    assert service.connected
    
    # Test book insertion
    book_data = TestDataGenerator.create_sample_book("test_book")
    book_id = await service.insert_book(book_data)
    assert book_id == "test_book"
    assert book_id in service.books
    
    # Test chunk insertion
    chunk_data = {
        "book_id": "test_book",
        "chunk_text": "Test chunk content",
        "embedding": [0.1, 0.2, 0.3] * 512
    }
    chunk_id = await service.insert_chunk(chunk_data)
    assert chunk_id in service.chunks
    
    # Test search
    query_embedding = [0.1, 0.2, 0.3] * 512
    results = await service.vector_search(query_embedding, limit=10)
    assert len(results) > 0
    
    await service.disconnect()
    assert not service.connected
    
    print("✓ MockDatabaseService works correctly")


@pytest.mark.asyncio
async def test_mock_http_service():
    """Test the mock HTTP service."""
    service = MockHTTPService()
    
    # Test GET request
    response = await service.get("https://example.com/api")
    assert response["status"] == 200
    assert len(service.requests) == 1
    assert service.requests[0]["method"] == "GET"
    
    # Test POST request
    data = {"query": "test"}
    response = await service.post("https://example.com/search", data=data)
    assert response["status"] == 200
    assert len(service.requests) == 2
    assert service.requests[1]["method"] == "POST"
    
    # Test predefined responses
    custom_response = {"status": 201, "data": {"id": 123}}
    service.set_response("https://api.test.com/create", custom_response)
    response = await service.get("https://api.test.com/create")
    assert response == custom_response
    
    print("✓ MockHTTPService works correctly")


@pytest.mark.asyncio
async def test_mock_search_engine():
    """Test the comprehensive mock search engine."""
    engine = MockSearchEngine()
    
    # Initialize
    await engine.initialize()
    assert engine.database_service.connected
    assert engine.database_service.books_count > 0
    
    # Test search
    response = await engine.search("dansk historie", limit=5)
    TestAssertions.assert_api_response_format(response)
    assert response["query"] == "dansk historie"
    assert len(response["results"]) > 0
    
    # Test analytics
    analytics = engine.get_analytics()
    assert analytics["total_searches"] == 1
    assert len(engine.get_search_history()) == 1
    
    # Test adding document
    initial_books = engine.database_service.books_count
    new_doc = TestDataGenerator.create_sample_book("new_book")
    book_id = await engine.add_document(new_doc)
    assert book_id == "new_book"
    assert engine.database_service.books_count == initial_books + 1
    
    await engine.cleanup()
    assert not engine.database_service.connected
    
    print("✓ MockSearchEngine works correctly")


def test_mock_service_factory():
    """Test the mock service factory."""
    # Test OpenAI service with failures
    service = MockServiceFactory.create_openai_service(failure_rate=0.5)
    assert isinstance(service, MockOpenAIService)
    assert service.api_key == "test_key"
    
    # Test database service with latency
    service = MockServiceFactory.create_database_service(latency_ms=100)
    assert isinstance(service, MockDatabaseService)
    
    # Test search engine with config
    config = {
        "openai_failure_rate": 0.1,
        "database_latency_ms": 50
    }
    engine = MockServiceFactory.create_search_engine(config)
    assert isinstance(engine, MockSearchEngine)
    
    print("✓ MockServiceFactory works correctly")


async def run_all_tests():
    """Run all validation tests."""
    print("Running test utilities validation tests...\n")
    
    # Sync tests
    test_data_generator_sample_book()
    test_data_generator_sample_chunks()
    test_data_generator_search_results()
    test_data_generator_embeddings()
    test_mock_response_generator_openai()
    test_mock_response_generator_database()
    test_mock_response_generator_api()
    test_test_assertions_valid_embedding()
    test_test_assertions_search_results()
    test_test_helpers_mock_creation()
    test_test_helpers_config()
    test_mock_service_factory()
    
    # Async tests
    await test_performance_helpers()
    await test_mock_openai_service()
    await test_mock_database_service()
    await test_mock_http_service()
    await test_mock_search_engine()
    
    print("\n✅ All test utilities validation tests passed!")
    print("Phase 4 test utilities are working correctly.")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
