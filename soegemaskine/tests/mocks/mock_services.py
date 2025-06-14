"""
Mock services for comprehensive testing of the semantic search.

Provides fully functional mock implementations of external services used in testing.
"""

import asyncio
import random
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime


class MockOpenAIService:
    """Mock OpenAI API service for testing."""
    
    def __init__(self, api_key: str = "test_api_key"):
        self.api_key = api_key
        self.call_count = 0
        self.total_tokens = 0
        self.embeddings_cache = {}
    
    async def create_embedding(self, text: str, model: str = "text-embedding-ada-002") -> Dict[str, Any]:
        """Create a mock embedding for text."""
        self.call_count += 1
        tokens = len(text.split())
        self.total_tokens += tokens
        
        # Use cached embedding if available
        if text in self.embeddings_cache:
            embedding = self.embeddings_cache[text]
        else:
            # Generate deterministic embedding based on text hash
            embedding = self._generate_embedding(text)
            self.embeddings_cache[text] = embedding
        
        return {
            "object": "list",
            "data": [{
                "object": "embedding",
                "index": 0,
                "embedding": embedding
            }],
            "model": model,
            "usage": {
                "prompt_tokens": tokens,
                "total_tokens": tokens
            }
        }
    
    def _generate_embedding(self, text: str, dimension: int = 1536) -> List[float]:
        """Generate a deterministic embedding based on text content."""
        # Use text hash as seed for reproducible results
        text_hash = hash(text)
        random.seed(text_hash)
        
        embedding = []
        for i in range(dimension):
            # Generate values that cluster similar content together
            if "historie" in text.lower():
                base_val = 0.1 + (i / dimension) * 0.2
            elif "kultur" in text.lower():
                base_val = 0.3 + (i / dimension) * 0.2
            elif "samfund" in text.lower():
                base_val = 0.5 + (i / dimension) * 0.2
            else:
                base_val = 0.0
            
            noise = random.uniform(-0.1, 0.1)
            embedding.append(base_val + noise)
        
        # Reset random seed
        random.seed()
        return embedding
    
    def get_stats(self) -> Dict[str, Any]:
        """Get API usage statistics."""
        return {
            "call_count": self.call_count,
            "total_tokens": self.total_tokens,
            "cached_embeddings": len(self.embeddings_cache)
        }


class MockDatabaseService:
    """Mock database service for testing."""
    
    def __init__(self):
        self.books = {}
        self.chunks = {}
        self.call_count = 0
        self.connected = False
    
    @property
    def books_count(self) -> int:
        """Return the number of books in the mock database."""
        return len(self.books)
    
    async def connect(self):
        """Mock database connection."""
        self.connected = True
        await asyncio.sleep(0.01)  # Simulate connection delay
    
    async def disconnect(self):
        """Mock database disconnection."""
        self.connected = False
    
    async def insert_book(self, book_data: Dict[str, Any]) -> str:
        """Insert a book into the mock database."""
        self.call_count += 1
        book_id = book_data.get("book_id", str(uuid.uuid4()))
        self.books[book_id] = {
            **book_data,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        return book_id
    
    async def insert_chunk(self, chunk_data: Dict[str, Any]) -> str:
        """Insert a text chunk into the mock database."""
        self.call_count += 1
        chunk_id = str(uuid.uuid4())
        self.chunks[chunk_id] = {
            **chunk_data,
            "chunk_id": chunk_id,
            "created_at": datetime.now().isoformat()
        }
        return chunk_id
    
    async def vector_search(self, query_embedding: List[float], limit: int = 10, 
                           distance_function: str = "cosine") -> List[tuple]:
        """Perform mock vector similarity search."""
        self.call_count += 1
        results = []
        
        for chunk_id, chunk in self.chunks.items():
            if "embedding" in chunk:
                # Calculate mock similarity based on distance function
                similarity = self._calculate_similarity(
                    query_embedding, chunk["embedding"], distance_function
                )
                
                results.append((
                    chunk.get("book_id", "unknown"),
                    self.books.get(chunk.get("book_id", ""), {}).get("title", "Unknown Title"),
                    chunk.get("chunk_text", ""),
                    similarity,
                    chunk.get("chunk_index", 0)
                ))
        
        # Sort by similarity and limit results
        results.sort(key=lambda x: x[3], reverse=True)
        return results[:limit]
    
    def _calculate_similarity(self, embedding1: List[float], embedding2: List[float], 
                            distance_function: str) -> float:
        """Calculate similarity between embeddings."""
        if distance_function == "cosine":
            # Simplified cosine similarity
            dot_product = sum(a * b for a, b in zip(embedding1[:10], embedding2[:10]))
            return max(0.0, min(1.0, dot_product / 10 + 0.5))
        elif distance_function == "euclidean":
            # Simplified euclidean distance converted to similarity
            distance = sum((a - b) ** 2 for a, b in zip(embedding1[:10], embedding2[:10])) ** 0.5
            return max(0.0, min(1.0, 1.0 / (1.0 + distance)))
        else:  # dot_product
            dot_product = sum(a * b for a, b in zip(embedding1[:10], embedding2[:10]))
            return max(0.0, min(1.0, (dot_product + 10) / 20))
    
    async def get_book(self, book_id: str) -> Optional[Dict[str, Any]]:
        """Get a book by ID."""
        self.call_count += 1
        return self.books.get(book_id)
    
    async def get_chunks_by_book(self, book_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a book."""
        self.call_count += 1
        return [chunk for chunk in self.chunks.values() 
                if chunk.get("book_id") == book_id]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database usage statistics."""
        return {
            "call_count": self.call_count,
            "books_count": len(self.books),
            "chunks_count": len(self.chunks),
            "connected": self.connected
        }


class MockHTTPService:
    """Mock HTTP client for testing external API calls."""
    
    def __init__(self):
        self.requests = []
        self.responses = {}
        self.default_response = {"status": 200, "data": {}}
    
    async def get(self, url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Mock HTTP GET request."""
        request = {
            "method": "GET",
            "url": url,
            "headers": headers or {},
            "timestamp": datetime.now().isoformat()
        }
        self.requests.append(request)
        
        # Return predefined response if available
        if url in self.responses:
            response = self.responses[url]
            # Simulate network delay
            await asyncio.sleep(random.uniform(0.01, 0.05))
            return response
        
        return self.default_response
    
    async def post(self, url: str, data: Any = None, 
                   headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Mock HTTP POST request."""
        request = {
            "method": "POST",
            "url": url,
            "data": data,
            "headers": headers or {},
            "timestamp": datetime.now().isoformat()
        }
        self.requests.append(request)
        
        # Return predefined response if available
        if url in self.responses:
            response = self.responses[url]
            await asyncio.sleep(random.uniform(0.01, 0.05))
            return response
        
        return self.default_response
    
    def set_response(self, url: str, response: Dict[str, Any]):
        """Set a predefined response for a URL."""
        self.responses[url] = response
    
    def get_request_history(self) -> List[Dict[str, Any]]:
        """Get history of all requests made."""
        return self.requests.copy()
    
    def clear_history(self):
        """Clear request history."""
        self.requests.clear()


class MockSearchEngine:
    """Mock search engine for comprehensive testing."""
    
    def __init__(self):
        self.openai_service = MockOpenAIService()
        self.database_service = MockDatabaseService()
        self.http_service = MockHTTPService()
        self.search_history = []
        self.analytics = {
            "total_searches": 0,
            "average_response_time": 0.0,
            "popular_queries": {}
        }
    
    async def initialize(self):
        """Initialize mock search engine."""
        await self.database_service.connect()
        
        # Load some test data
        await self._load_test_data()
    
    async def search(self, query: str, limit: int = 10, 
                    distance_function: str = "cosine") -> Dict[str, Any]:
        """Perform mock search."""
        start_time = datetime.now()
        
        # Generate query embedding
        embedding_response = await self.openai_service.create_embedding(query)
        query_embedding = embedding_response["data"][0]["embedding"]
        
        # Search database
        search_results = await self.database_service.vector_search(
            query_embedding, limit, distance_function
        )
        
        # Format results
        formatted_results = []
        for book_id, title, chunk_text, similarity, chunk_index in search_results:
            formatted_results.append({
                "book_id": book_id,
                "title": title,
                "chunk_text": chunk_text,
                "similarity": round(similarity, 3),
                "chunk_index": chunk_index,
                "relevance_score": round(similarity * 0.95, 3)
            })
        
        # Record search
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        search_record = {
            "query": query,
            "results_count": len(formatted_results),
            "response_time_ms": response_time,
            "timestamp": start_time.isoformat()
        }
        self.search_history.append(search_record)
        
        # Update analytics
        self._update_analytics(query, response_time)
        
        return {
            "query": query,
            "results": formatted_results,
            "total": len(formatted_results),
            "limit": limit,
            "offset": 0,
            "processing_time_ms": round(response_time, 2),
            "timestamp": start_time.isoformat()
        }
    
    async def add_document(self, document: Dict[str, Any]) -> str:
        """Add a document to the search engine."""
        # Insert book
        book_id = await self.database_service.insert_book(document)
        
        # Create chunks and embeddings
        content = document.get("content", "")
        chunks = self._create_chunks(content, book_id)
        
        for chunk in chunks:
            # Generate embedding
            embedding_response = await self.openai_service.create_embedding(chunk["chunk_text"])
            chunk["embedding"] = embedding_response["data"][0]["embedding"]
            
            # Store chunk
            await self.database_service.insert_chunk(chunk)
        
        return book_id
    
    def _create_chunks(self, content: str, book_id: str, chunk_size: int = 1000) -> List[Dict[str, Any]]:
        """Split content into chunks."""
        words = content.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size // 5):  # Approximate word count
            chunk_words = words[i:i + chunk_size // 5]
            chunk_text = " ".join(chunk_words)
            
            chunks.append({
                "book_id": book_id,
                "chunk_index": len(chunks),
                "chunk_text": chunk_text,
                "chunk_size": len(chunk_text)
            })
        
        return chunks
    
    async def _load_test_data(self):
        """Load test data into the mock search engine."""
        test_books = [
            {
                "book_id": "test_book_1",
                "title": "Danmarks Historie",
                "author": "Test Forfatter",
                "content": "Dette er en bog om dansk historie og traditioner. "
                          "Den beskriver hvordan det danske samfund har udviklet sig gennem tiden. "
                          "Bogen indeholder information om vikinger, middelalder og moderne tid."
            },
            {
                "book_id": "test_book_2", 
                "title": "Danske Traditioner",
                "author": "Kultur Ekspert",
                "content": "En omfattende guide til danske kulturelle traditioner og skikke. "
                          "Bogen dækker højtider, mad, musik og sociale normer i Danmark. "
                          "Perfekt til at forstå dansk kultur og samfund."
            },
            {
                "book_id": "test_book_3",
                "title": "Moderne Danmark",
                "author": "Samfunds Forsker", 
                "content": "En analyse af det moderne danske samfund og dets værdier. "
                          "Bogen ser på demokrati, velfærd og social sammenhængskraft. "
                          "Relevant for forståelse af nutidens Danmark."
            }
        ]
        
        for book in test_books:
            await self.add_document(book)
    
    def _update_analytics(self, query: str, response_time: float):
        """Update search analytics."""
        self.analytics["total_searches"] += 1
        
        # Update average response time
        current_avg = self.analytics["average_response_time"]
        total_searches = self.analytics["total_searches"]
        self.analytics["average_response_time"] = (
            (current_avg * (total_searches - 1) + response_time) / total_searches
        )
        
        # Track popular queries
        if query in self.analytics["popular_queries"]:
            self.analytics["popular_queries"][query] += 1
        else:
            self.analytics["popular_queries"][query] = 1
    
    def get_analytics(self) -> Dict[str, Any]:
        """Get search analytics."""
        return {
            **self.analytics,
            "search_history_count": len(self.search_history),
            "openai_stats": self.openai_service.get_stats(),
            "database_stats": self.database_service.get_stats()
        }
    
    def get_search_history(self) -> List[Dict[str, Any]]:
        """Get search history."""
        return self.search_history.copy()
    
    async def cleanup(self):
        """Clean up resources."""
        await self.database_service.disconnect()


class MockServiceFactory:
    """Factory for creating mock services with various configurations."""
    
    @staticmethod
    def create_openai_service(api_key: str = "test_key", 
                            failure_rate: float = 0.0) -> MockOpenAIService:
        """Create a mock OpenAI service with optional failure simulation."""
        service = MockOpenAIService(api_key)
        
        if failure_rate > 0:
            original_create = service.create_embedding
            
            async def failing_create_embedding(text: str, model: str = "text-embedding-ada-002"):
                if random.random() < failure_rate:
                    raise Exception("Mock API failure")
                return await original_create(text, model)
            
            service.create_embedding = failing_create_embedding
        
        return service
    
    @staticmethod
    def create_database_service(latency_ms: int = 0) -> MockDatabaseService:
        """Create a mock database service with optional latency simulation."""
        service = MockDatabaseService()
        
        if latency_ms > 0:
            # Add latency to all async methods
            for method_name in ['connect', 'insert_book', 'insert_chunk', 'vector_search']:
                original_method = getattr(service, method_name)
                
                async def add_latency(*args, **kwargs):
                    await asyncio.sleep(latency_ms / 1000)
                    return await original_method(*args, **kwargs)
                
                setattr(service, method_name, add_latency)
        
        return service
    
    @staticmethod
    def create_search_engine(config: Optional[Dict[str, Any]] = None) -> MockSearchEngine:
        """Create a mock search engine with optional configuration."""
        engine = MockSearchEngine()
        
        if config:
            # Apply configuration
            if "openai_failure_rate" in config:
                engine.openai_service = MockServiceFactory.create_openai_service(
                    failure_rate=config["openai_failure_rate"]
                )
            
            if "database_latency_ms" in config:
                engine.database_service = MockServiceFactory.create_database_service(
                    latency_ms=config["database_latency_ms"]
                )
        
        return engine
