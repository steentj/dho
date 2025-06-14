"""
Shared test fixtures and configuration for the semantic search tests.
"""
import pytest
import asyncio
import os
import tempfile
import sqlite3
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, List, Any
import json

# Test data constants
SAMPLE_PDF_CONTENT = {
    1: "Dette er side 1 af test dokumentet. Den handler om Anna Krogh og hendes arbejde med gymnastik.",
    2: "Side 2 indeholder information om Niels Rolsted og hans tid som skovfoged i Fledskov.",
    3: "Den sidste side beskriver højskoler og deres betydning for dansk uddannelse."
}

SAMPLE_EMBEDDING = [0.1] * 1536  # Standard OpenAI embedding dimension

SAMPLE_SEARCH_RESULTS = [
    {
        "pdf_navn": "test_book.pdf",
        "titel": "Test Bog",
        "forfatter": "Test Forfatter",
        "sidenr": 1,
        "chunk": "Dette er en test chunk fra test bogen.",
        "distance": 0.15
    }
]


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.data = [MagicMock()]
    mock_response.data[0].embedding = SAMPLE_EMBEDDING
    mock_client.embeddings.create.return_value = mock_response
    return mock_client


@pytest.fixture
async def mock_async_openai_client():
    """Mock async OpenAI client for testing."""
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.data = [AsyncMock()]
    mock_response.data[0].embedding = SAMPLE_EMBEDDING
    mock_client.embeddings.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_database_connection():
    """Mock database connection for testing."""
    mock_conn = AsyncMock()
    
    # Mock common database operations
    mock_conn.fetchval.return_value = 1  # For INSERT operations returning ID
    mock_conn.fetch.return_value = [
        ("test_book.pdf", "Test Bog", "Test Forfatter", 1, "Test chunk", 0.15)
    ]
    mock_conn.execute.return_value = None
    
    return mock_conn


@pytest.fixture
def sample_pdf_content():
    """Sample PDF content for testing."""
    return SAMPLE_PDF_CONTENT


@pytest.fixture
def sample_embedding():
    """Sample embedding vector for testing."""
    return SAMPLE_EMBEDDING


@pytest.fixture
def sample_search_results():
    """Sample search results for testing."""
    return SAMPLE_SEARCH_RESULTS


@pytest.fixture
def temp_test_file():
    """Create a temporary file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("http://example.com/book1.pdf\n")
        f.write("http://example.com/book2.pdf\n")
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    test_env = {
        "OPENAI_API_KEY": "test_key_123",
        "OPENAI_MODEL": "text-embedding-3-small",
        "DATABASE_URL": "postgresql://test:test@localhost:5432/test_db",
        "POSTGRES_DB": "test_db",
        "POSTGRES_USER": "test_user", 
        "POSTGRES_PASSWORD": "test_password",
        "TILLADTE_KALDERE": "http://localhost:3000,http://127.0.0.1:3000"
    }
    
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    
    return test_env


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp session for HTTP requests."""
    mock_session = AsyncMock()
    
    # Mock successful PDF response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.read.return_value = b"fake_pdf_content"
    
    mock_session.get.return_value.__aenter__.return_value = mock_response
    
    return mock_session


@pytest.fixture
def mock_fitz_document():
    """Mock PyMuPDF document for PDF processing."""
    mock_doc = MagicMock()
    mock_doc.__len__.return_value = 3  # 3 pages
    
    # Mock pages
    mock_pages = []
    for i, (page_num, content) in enumerate(SAMPLE_PDF_CONTENT.items()):
        mock_page = MagicMock()
        mock_page.get_text.return_value = content
        mock_pages.append(mock_page)
    
    mock_doc.__getitem__ = lambda self, index: mock_pages[index]
    
    return mock_doc


@pytest.fixture
def sample_chunks():
    """Sample text chunks for testing."""
    return [
        "Dette er den første chunk af tekst om Anna Krogh.",
        "Dette er den anden chunk om Niels Rolsted og skovarbejde.",
        "Den tredje chunk handler om højskoler i Danmark."
    ]


@pytest.fixture
async def test_database():
    """Create an in-memory SQLite database for testing."""
    # Note: This is a simplified version. In real implementation,
    # you might want to use a PostgreSQL test container or similar
    conn = sqlite3.connect(":memory:")
    
    # Create simplified table structure
    conn.execute("""
        CREATE TABLE embeddings (
            id INTEGER PRIMARY KEY,
            pdf_navn TEXT,
            titel TEXT,
            forfatter TEXT,
            sidenr INTEGER,
            chunk TEXT,
            embedding TEXT  -- JSON string of the embedding vector
        )
    """)
    
    # Insert sample data
    sample_data = [
        (1, "test_book.pdf", "Test Bog", "Test Forfatter", 1, 
         "Test chunk content", json.dumps(SAMPLE_EMBEDDING))
    ]
    
    conn.executemany("""
        INSERT INTO embeddings (id, pdf_navn, titel, forfatter, sidenr, chunk, embedding)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, sample_data)
    
    conn.commit()
    
    yield conn
    
    conn.close()


# Event loop fixture for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Utility functions for tests
def assert_embedding_shape(embedding: List[float], expected_dim: int = 1536):
    """Assert that an embedding has the correct shape."""
    assert isinstance(embedding, list), "Embedding should be a list"
    assert len(embedding) == expected_dim, f"Embedding should have {expected_dim} dimensions"
    assert all(isinstance(x, (int, float)) for x in embedding), "All embedding values should be numeric"


def assert_search_result_format(result: Dict[str, Any]):
    """Assert that a search result has the correct format."""
    required_fields = ["pdf_navn", "titel", "forfatter", "sidenr", "chunk", "distance"]
    for field in required_fields:
        assert field in result, f"Search result missing required field: {field}"
    
    assert isinstance(result["sidenr"], int), "Page number should be an integer"
    assert isinstance(result["distance"], (int, float)), "Distance should be numeric"
    assert isinstance(result["chunk"], str), "Chunk should be a string"
