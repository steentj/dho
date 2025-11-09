"""
Mock services for testing the semantic search.
"""
from unittest.mock import AsyncMock, MagicMock
from typing import List, Dict, Any


class MockOpenAIEmbeddingProvider:
    """Mock OpenAI embedding provider that returns consistent test embeddings."""
    
    def __init__(self, api_key: str = "test_key"):
        self.api_key = api_key
        self.call_count = 0
    
    async def get_embedding(self, chunk: str) -> List[float]:
        """Return a mock embedding based on the input text."""
        self.call_count += 1
        
        # Create deterministic embeddings based on text content
        if "Anna Krogh" in chunk or "gymnastik" in chunk:
            return [0.1 + i * 0.01 for i in range(1536)]
        elif "Niels Rolsted" in chunk or "skov" in chunk:
            return [0.2 + i * 0.01 for i in range(1536)]
        elif "højskole" in chunk:
            return [0.3 + i * 0.01 for i in range(1536)]
        else:
            return [0.1] * 1536  # Default embedding


class MockDatabase:
    """Mock database for testing."""
    
    def __init__(self):
        self.embeddings = []
        self.books = []
        self.call_count = 0
    
    async def connect(self):
        """Mock database connection."""
        return self
    
    async def close(self):
        """Mock database close."""
        pass
    
    async def fetchval(self, query: str, *params) -> Any:
        """Mock fetchval operation."""
        self.call_count += 1
        if "INSERT" in query:
            return len(self.embeddings) + 1  # Return new ID
        return None
    
    async def fetch(self, query: str, *params) -> List[tuple]:
        """Mock fetch operation for search results."""
        self.call_count += 1
        
        # Return mock search results
        return [
            ("test_book.pdf", "Test Bog", "Test Forfatter", 1, 
             "Dette er en test chunk.", 0.15),
            ("test_book.pdf", "Test Bog", "Test Forfatter", 2,
             "Dette er en anden test chunk.", 0.25)
        ]
    
    async def execute(self, query: str, *params):
        """Mock execute operation."""
        self.call_count += 1
        if "INSERT" in query:
            # Simulate storing embedding
            self.embeddings.append(params)


class MockPDFDocument:
    """Mock PDF document for testing."""
    
    def __init__(self, pages: Dict[int, str]):
        self.pages = pages
    
    def __len__(self):
        return len(self.pages)
    
    def __getitem__(self, index):
        mock_page = MagicMock()
        mock_page.get_text.return_value = self.pages.get(index + 1, "")
        return mock_page


class MockHTTPSession:
    """Mock aiohttp session for testing."""
    
    def __init__(self, response_data: bytes = b"fake_pdf_content"):
        self.response_data = response_data
        self.request_count = 0
    
    async def get(self, url: str, **kwargs):
        """Mock HTTP GET request."""
        self.request_count += 1
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read.return_value = self.response_data
        
        # Return context manager
        context_manager = AsyncMock()
        context_manager.__aenter__.return_value = mock_response
        context_manager.__aexit__.return_value = None
        
        return context_manager


def create_mock_fastapi_app():
    """Create a mock FastAPI app for testing."""
    try:
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        
        app = FastAPI()
        
        @app.get("/")
        async def root():
            return {"Hej": "Dette er Dansk Historie Online: Semantisk søgning API"}
        
        @app.post("/search2")
        async def search2(request: dict):
            return [
                {
                    "pdf_navn": "test_book.pdf",
                    "titel": "Test Bog",
                    "forfatter": "Test Forfatter", 
                    "sidenr": 1,
                    "chunk": "Test chunk content",
                    "distance": 0.15
                }
            ]
        
        return TestClient(app)
    except ImportError:
        # FastAPI not available, return mock
        return MagicMock()


# Pre-defined mock responses
MOCK_OPENAI_RESPONSE = {
    "data": [
        {
            "embedding": [0.1] * 1536
        }
    ]
}

MOCK_SEARCH_RESULTS = [
    {
        "pdf_navn": "test_book.pdf",
        "titel": "Test Bog om Dansk Historie",
        "forfatter": "Test Forfatter",
        "sidenr": 1,
        "chunk": "Dette er test indhold om Anna Krogh og gymnastik.",
        "distance": 0.15
    }
]
