"""
Test configuration and fixtures for database tests.
"""
import pytest
import os
from unittest.mock import patch


@pytest.fixture
def test_env_vars():
    """Provide test environment variables."""
    return {
        "POSTGRES_DB": "test_db",
        "POSTGRES_USER": "test_user", 
        "POSTGRES_PASSWORD": "test_pass",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "DATABASE_TYPE": "postgresql"
    }


@pytest.fixture
def mock_env(test_env_vars):
    """Mock environment variables for testing."""
    with patch.dict(os.environ, test_env_vars, clear=True):
        yield


@pytest.fixture
def sample_book_data():
    """Sample book data for testing."""
    return {
        "pdf_url": "https://example.com/test.pdf",
        "title": "Test Book",
        "author": "Test Author", 
        "pages": 100
    }


@pytest.fixture
def sample_chunks_data():
    """Sample chunks data for testing."""
    return [
        (1, "First chunk of text", [0.1, 0.2, 0.3, 0.4, 0.5]),
        (2, "Second chunk of text", [0.6, 0.7, 0.8, 0.9, 1.0]),
        (3, "Third chunk of text", [0.2, 0.4, 0.6, 0.8, 1.0])
    ]


@pytest.fixture
def sample_embedding():
    """Sample embedding vector for testing."""
    return [0.1] * 1536  # OpenAI embedding dimension


@pytest.fixture
def sample_search_results():
    """Sample search results for testing."""
    return [
        ("book1.pdf", "Book 1", "Author 1", 1, "chunk text 1", 0.15),
        ("book2.pdf", "Book 2", "Author 2", 3, "chunk text 2", 0.25),
        ("book3.pdf", "Book 3", "Author 3", 2, "chunk text 3", 0.35)
    ]
