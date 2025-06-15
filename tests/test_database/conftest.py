"""
Test configuration for database tests.
"""
import pytest
import os
from unittest.mock import AsyncMock


@pytest.fixture
def mock_db_config():
    """Fixture providing test database configuration."""
    return {
        'host': 'localhost',
        'port': 5432,
        'database': 'test_db',
        'user': 'test_user',
        'password': 'test_pass'
    }


@pytest.fixture
def mock_asyncpg_pool():
    """Fixture providing mock asyncpg pool."""
    mock_pool = AsyncMock()
    mock_connection = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
    mock_pool.acquire.return_value.__aexit__.return_value = None
    return mock_pool, mock_connection


@pytest.fixture
def sample_embedding():
    """Fixture providing sample embedding data."""
    return {
        'id': 1,
        'book_id': 1,
        'chunk_text': 'This is a sample text chunk for testing purposes.',
        'embedding': [0.1, 0.2, 0.3, 0.4, 0.5],
        'metadata': {
            'page': 1,
            'chapter': 'Introduction',
            'section': 'Overview'
        }
    }


@pytest.fixture
def sample_embeddings_list():
    """Fixture providing list of sample embeddings."""
    return [
        {
            'id': 1,
            'book_id': 1,
            'chunk_text': 'First chunk',
            'embedding': [0.1, 0.2, 0.3],
            'metadata': {'page': 1}
        },
        {
            'id': 2,
            'book_id': 1,
            'chunk_text': 'Second chunk',
            'embedding': [0.4, 0.5, 0.6],
            'metadata': {'page': 1}
        },
        {
            'id': 3,
            'book_id': 2,
            'chunk_text': 'Third chunk',
            'embedding': [0.7, 0.8, 0.9],
            'metadata': {'page': 2}
        }
    ]


@pytest.fixture
def clean_env():
    """Fixture to clean environment variables for testing."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )


def pytest_collection_modifyitems(config, items):
    """Auto-mark tests based on their location."""
    for item in items:
        # Mark all async tests
        if 'async' in item.name or item.function.__name__.startswith('test_') and 'async' in str(item.function):
            item.add_marker(pytest.mark.asyncio)
        
        # Mark integration tests
        if 'integration' in item.fspath.basename or 'test_integration' in item.name:
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)
