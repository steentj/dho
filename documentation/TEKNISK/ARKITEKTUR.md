# System Arkitektur

## Oversigt

DHO Semantisk Søgemaskine er bygget med en modulær, pluggable arkitektur der understøtter flere database providers, embedding models, og tekst processing strategier.

## 🏗 **Højniveau Arkitektur**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Search API    │    │  Processing     │
│   (Web UI)      │    │   (Flask)       │    │  Pipeline       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Core Components                             │
├─────────────────┬─────────────────┬─────────────────────────────┤
│  Database       │  Embedding      │  Chunking                   │
│  Abstraction    │  Providers      │  Strategies                 │
│                 │                 │                             │
│  ┌───────────┐  │  ┌───────────┐  │  ┌─────────────────────┐    │
│  │PostgreSQL │  │  │  OpenAI   │  │  │ Sentence Splitter   │    │
│  │ Service   │  │  │ Provider  │  │  │                     │    │
│  └───────────┘  │  └───────────┘  │  └─────────────────────┘    │
│                 │                 │                             │
│  ┌───────────┐  │  ┌───────────┐  │  ┌─────────────────────┐    │
│  │  Future   │  │  │  Ollama   │  │  │   Word Overlap      │    │
│  │ Database  │  │  │ Provider  │  │  │                     │    │
│  └───────────┘  │  └───────────┘  │  └─────────────────────┘    │
│                 │                 │                             │
│                 │  ┌───────────┐  │                             │
│                 │  │  Dummy    │  │                             │
│                 │  │ Provider  │  │                             │
│                 │  └───────────┘  │                             │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

## 📦 **Core Moduler**

### Database Layer (`database/`)

#### Abstraktion
```python
# interfaces.py - Definerer kontrakter
class BookService(ABC):
    @abstractmethod
    async def get_or_create_book(self, pdf_url: str, title: str, author: str, pages: int) -> int:
        pass

class DatabaseService(ABC):
    @abstractmethod
    async def find_book_by_url(self, url: str) -> Optional[int]:
        pass
```

#### Implementation
```python
# postgresql.py - Konkret implementation
class PostgreSQLService(DatabaseService):
    async def find_book_by_url(self, url: str) -> Optional[int]:
        # PostgreSQL-specifik implementation
        
# factory.py - Factory pattern
class DatabaseFactory:
    @staticmethod
    def create_service(db_type: str) -> DatabaseService:
        if db_type == "postgresql":
            return PostgreSQLService()
```

**Design Principper:**
- **Dependency Injection**: Services injected via factory
- **Interface Segregation**: Separate interfaces for different concerns
- **Single Responsibility**: Each service har specifikt ansvar

### Embedding Providers (`create_embeddings/providers/`)

#### Pluggable Architecture
```python
# embedding_providers.py - Base abstraktion
class EmbeddingProvider(ABC):
    @abstractmethod
    async def get_embedding(self, text: str) -> List[float]:
        pass
    
    @abstractmethod
    def get_table_name(self) -> str:
        pass

# Konkrete implementationer
class OpenAIEmbeddingProvider(EmbeddingProvider):
    async def get_embedding(self, text: str) -> List[float]:
        # OpenAI API integration
        
class OllamaEmbeddingProvider(EmbeddingProvider):
    async def get_embedding(self, text: str) -> List[float]:
        # Ollama lokal integration
```

#### Provider Selection
```python
# factory.py - Environment-based selection
class EmbeddingProviderFactory:
    @staticmethod
    def create_provider(provider: str, api_key: str) -> EmbeddingProvider:
        if provider == "openai":
            return OpenAIEmbeddingProvider(api_key)
        elif provider == "ollama":
            return OllamaEmbeddingProvider()
        elif provider == "dummy":
            return DummyEmbeddingProvider()
```

**Design Features:**
- **Provider Isolation**: Hver provider er selvstændig
- **Table Separation**: Embeddings gemmes i provider-specifikke tabeller
- **Async Support**: Alle providers understøtter async operations

### Chunking System (`create_embeddings/chunking.py`)

#### Strategy Pattern
```python
# ChunkingStrategy base class
class ChunkingStrategy(ABC):
    @abstractmethod
    def chunk_text(self, text: str, max_tokens: int, title: str = "") -> List[str]:
        pass

# Konkrete strategier
class SentenceSplitterChunkingStrategy(ChunkingStrategy):
    def chunk_text(self, text: str, max_tokens: int, title: str = "") -> List[str]:
        # Sentence-aware chunking med titel prefiks
        
class WordOverlapChunkingStrategy(ChunkingStrategy):
    def chunk_text(self, text: str, max_tokens: int, title: str = "") -> List[str]:
        # Fixed-size chunks med overlap
```

#### Factory Selection
```python
class ChunkingStrategyFactory:
    @staticmethod
    def create_strategy(strategy: str) -> ChunkingStrategy:
        if strategy == "sentence_splitter":
            return SentenceSplitterChunkingStrategy()
        elif strategy == "word_overlap":
            return WordOverlapChunkingStrategy()
```

## 🔄 **Data Flow**

### Book Processing Pipeline

```
1. Input Processing
   ├─ URL Validation
   ├─ PDF Download
   └─ Metadata Extraction

2. Text Extraction
   ├─ Page-by-page Processing
   ├─ Text Cleaning
   └─ Structure Preservation

3. Chunking Phase
   ├─ Strategy Selection (env: CHUNKING_STRATEGY)
   ├─ Text Segmentation
   └─ Title Integration

4. Embedding Generation
   ├─ Provider Selection (env: PROVIDER)
   ├─ API/Local Model Call
   └─ Vector Generation

5. Database Storage
   ├─ Book Metadata Storage
   ├─ Chunk Text Storage
   └─ Provider-specific Embedding Storage
```

### Search Query Flow

```
1. Query Input
   ├─ User Query Reception
   ├─ Query Preprocessing
   └─ Embedding Generation

2. Vector Search
   ├─ Similarity Calculation
   ├─ Distance Filtering
   └─ Result Ranking

3. Result Processing
   ├─ Metadata Enrichment
   ├─ Context Extraction
   └─ Response Formatting

4. Response Delivery
   ├─ JSON Serialization
   ├─ CORS Handling
   └─ Client Response
```

## 🗄 **Database Schema**

### Core Tables
```sql
-- Books metadata
CREATE TABLE books (
    id SERIAL PRIMARY KEY,
    pdf_url TEXT UNIQUE NOT NULL,
    title TEXT,
    author TEXT,
    pages INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Text chunks (provider-agnostic)
CREATE TABLE chunks (
    id SERIAL PRIMARY KEY,
    book_id INTEGER REFERENCES books(id),
    page_number INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Provider-specific embedding tables
CREATE TABLE openai_embeddings (
    embedding_id SERIAL PRIMARY KEY,
    chunk_id INTEGER REFERENCES chunks(id),
    embedding VECTOR(1536),  -- OpenAI embedding dimension
    provider TEXT DEFAULT 'openai',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ollama_embeddings (
    embedding_id SERIAL PRIMARY KEY,
    chunk_id INTEGER REFERENCES chunks(id),
    embedding VECTOR(768),   -- Ollama embedding dimension
    provider TEXT DEFAULT 'ollama',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Index Strategy
```sql
-- Performance indexes
CREATE INDEX idx_books_url ON books(pdf_url);
CREATE INDEX idx_chunks_book_id ON chunks(book_id);
CREATE INDEX idx_openai_embeddings_chunk_id ON openai_embeddings(chunk_id);
CREATE INDEX idx_ollama_embeddings_chunk_id ON ollama_embeddings(chunk_id);

-- Vector similarity indexes (hvis understøttet)
CREATE INDEX idx_openai_embeddings_vector ON openai_embeddings 
USING ivfflat (embedding vector_cosine_ops);
```

## 🔌 **Dependency Injection Pattern**

### Service Registration
```python
# I book_processor_wrapper.py
async def process_books_from_file(self, input_file: str):
    # Dependency injection af alle komponenter
    embedding_provider = EmbeddingProviderFactory.create_provider(
        os.getenv("PROVIDER"), 
        os.getenv("OPENAI_API_KEY")
    )
    
    chunking_strategy = ChunkingStrategyFactory.create_strategy(
        os.getenv("CHUNKING_STRATEGY", "sentence_splitter")
    )
    
    # Services injected til processing pipeline
    await process_book(
        book_url, chunk_size, pool, session, 
        embedding_provider, chunking_strategy
    )
```

### Benefits
- **Testability**: Mock objects kan injected under tests
- **Flexibility**: Runtime component switching
- **Separation of Concerns**: Business logic adskilt fra infrastructure
- **Configuration-driven**: Environment variables styrer component selection

## 🏭 **Factory Pattern Implementation**

### Multi-layer Factory Design
```python
# Layer 1: Component Factories
EmbeddingProviderFactory.create_provider()
ChunkingStrategyFactory.create_strategy()
DatabaseFactory.create_service()

# Layer 2: Service Composition
class ProcessingServiceFactory:
    @staticmethod
    def create_complete_pipeline():
        db_service = DatabaseFactory.create_service()
        embedding_provider = EmbeddingProviderFactory.create_provider()
        chunking_strategy = ChunkingStrategyFactory.create_strategy()
        return ProcessingPipeline(db_service, embedding_provider, chunking_strategy)
```

## 🚀 **Async Architecture**

### Concurrency Model
```python
# Async processing with semaphore control
semaphore = asyncio.Semaphore(5)  # Max 5 concurrent books

async def process_books_batch(book_urls):
    tasks = [
        asyncio.create_task(
            semaphore_guard_processing(semaphore, url)
        )
        for url in book_urls
    ]
    await asyncio.gather(*tasks, return_exceptions=True)
```

### Resource Management
- **Connection Pooling**: Database connection pools
- **Rate Limiting**: API call throttling via semaphores
- **Memory Management**: Streaming processing for large files
- **Error Isolation**: Exception handling per concurrent task

## 🔐 **Configuration Management**

### Environment-driven Configuration
```python
# Centralized validation
def validate_config():
    # Provider-specific validation
    provider = os.getenv("PROVIDER", "ollama")
    if provider == "openai":
        required_vars.extend(["OPENAI_API_KEY"])
    elif provider == "ollama":
        required_vars.extend(["OLLAMA_BASE_URL", "OLLAMA_MODEL"])
    
    # Strategy validation
    chunking_strategy = os.getenv("CHUNKING_STRATEGY", "sentence_splitter")
    if chunking_strategy not in ["sentence_splitter", "word_overlap"]:
        raise ValueError("Invalid chunking strategy")
```

### Configuration Layers
1. **Environment Variables**: Runtime configuration
2. **Default Values**: Fallback defaults i kode
3. **Validation Layer**: Comprehensive validation before execution
4. **Documentation**: `.env.template` med alle options

## 📈 **Skalering og Performance**

### Horizontal Scaling Points
- **Processing Workers**: Multiple container instances
- **Database Read Replicas**: Separate read/write databases
- **Embedding Service Sharding**: Multiple Ollama instances
- **Search API Load Balancing**: Multiple Flask instances

### Performance Optimizations
- **Batch Processing**: Gruppe operations for efficiency
- **Connection Pooling**: Reduce connection overhead
- **Async I/O**: Non-blocking operations
- **Vector Indexing**: Optimized similarity search
- **Caching Layers**: Redis for frequent queries

## 🔄 **Extensibility Points**

### Tilføj Ny Database Provider
```python
# 1. Implementér DatabaseService interface
class NewDatabaseService(DatabaseService):
    async def find_book_by_url(self, url: str) -> Optional[int]:
        # New database implementation

# 2. Registrér i factory
if db_type == "newdb":
    return NewDatabaseService()

# 3. Opdatér configuration validation
```

### Tilføj Ny Embedding Provider
```python
# 1. Implementér EmbeddingProvider interface
class NewEmbeddingProvider(EmbeddingProvider):
    async def get_embedding(self, text: str) -> List[float]:
        # New embedding implementation
    
    def get_table_name(self) -> str:
        return "new_provider_embeddings"

# 2. Opret database tabel
# 3. Registrér i factory
# 4. Opdatér validation
```

## 🛡 **Error Handling og Resilience**

### Multi-layer Error Handling
```python
# Layer 1: Component-level errors
try:
    embedding = await provider.get_embedding(text)
except ProviderError as e:
    log.warning(f"Provider error: {e}")
    # Fallback eller retry logic

# Layer 2: Processing-level errors  
try:
    await process_book(url, ...)
except Exception as e:
    failed_books.append({"url": url, "error": str(e)})
    log.error(f"Book processing failed: {e}")

# Layer 3: System-level errors
try:
    await process_books_from_file(input_file)
except SystemError as e:
    log.critical(f"System failure: {e}")
    update_status("fejl")
```

### Resilience Patterns
- **Circuit Breaker**: API failure protection
- **Retry Logic**: Exponential backoff for transient failures
- **Graceful Degradation**: Fallback providers
- **Error Aggregation**: Collect and report failures
- **Health Checks**: System status monitoring

---

**Design Philosophy**: Modulær, testbar, og skalerbar arkitektur med clear separation of concerns og comprehensive error handling.
