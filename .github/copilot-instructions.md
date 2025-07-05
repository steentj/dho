# DHO Semantic Search System - AI Coding Agent Guide

## Architecture Overview

A semantic search system for Danish historical PDFs using dependency injection patterns throughout:

- **`create_embeddings/`**: PDF processing pipeline with pluggable embedding providers and chunking strategies
- **`database/`**: Pluggable database layer with PostgreSQL implementation  
- **`soegemaskine/`**: FastAPI search service with vector similarity
- **Dependency Injection**: Core pattern enabling swappable implementations across all layers

## Critical Test Isolation Patterns

**ALWAYS use `clear=True` in `patch.dict()` for environment isolation:**

```python
# CORRECT - Isolated from real .env
with patch.dict(os.environ, {'KEY': 'value'}, clear=True):
    test_function()

# WRONG - Inherits real environment variables  
with patch.dict(os.environ, {'KEY': 'value'}):
    test_function()
```

**Mock `load_dotenv()` to prevent reading real `.env` files:**

```python
with patch("dotenv.load_dotenv"):
    with patch.dict(os.environ, test_vars, clear=True):
        # Test code here
```

These patterns prevent tests from reading production secrets and ensure repeatability.

## Configuration & Environment

- **`.env.template`**: Complete configuration reference with Danish comments
- **Three providers**: `openai`, `ollama` (local), `dummy` (testing)
- **Two chunking strategies**: `sentence_splitter` (default), `word_overlap` 
- **Validation**: `validate_config()` in `book_processor_wrapper.py` with cross-validation warnings

## Core Dependency Injection Interfaces

### Database Layer (`database/interfaces.py`)
```python
# Pluggable database implementations
BookRepository, SearchRepository, DatabaseFactory
# Current: PostgreSQL implementation in database/postgresql_service.py
```

### Embedding Providers (`create_embeddings/providers/`)
```python
# Factory pattern for embedding providers
EmbeddingProviderFactory.create_provider("openai|ollama|dummy", api_key)
# Each provider implements get_embedding(), has_embeddings_for_book(), get_table_name()
```

### Chunking Strategies (`create_embeddings/chunking.py`)
```python
# Strategy pattern for text chunking
ChunkingStrategyFactory.create_strategy("sentence_splitter|word_overlap")
# sentence_splitter: adds ##title## prefix and respects sentence boundaries
# word_overlap: 400-word chunks with 50-word overlap, no title prefix
```

## Development Workflow

### Phase-Based Development
1. **Plan First**: Create development phases with clear goals
2. **Tiny Steps**: Develop each phase in small, testable increments  
3. **Test-Driven**: Create/update tests for each step
4. **Manual Confirmation**: Always ask for confirmation before proceeding
5. **Documentation**: 
    1. Create/update markdown plans with to-do's for each phase
    2. All user docs in `/documentation/` must be Danish, technical, and concise
    3. Documentation is stored as markdown files in `/documentation/` directory
    4. Documents must have Creation date/time and Last Modified date/time at the top of the file

### Test Quality Standards
- **No Overlaps**: Avoid testing same functionality in multiple places
- **Complete Coverage**: Ensure all critical paths are tested
- **No Linting Errors**: All code must pass linting before proceeding
- **Test Structure**: Well-organized test suites with clear separation

### Critical Test Completion Rules
- **MANDATORY FULL SUITE VALIDATION**: Always run all tests in the codebase and verify they are ALL passing before declaring any feature finished or problem solved
- **PATIENCE WITH TEST EXECUTION**: When running all or a large number of tests, wait at least 15-20 seconds for complete execution - never assume tests are done prematurely
- **NO PARTIAL COMPLETION CLAIMS**: Do not declare success based on partial test runs or individual test file results
- **FULL VALIDATION COMMAND**: Always use `python -m pytest` (no file restrictions) as final validation step

### Testing Infrastructure

**Key Testing Commands:**
```bash
# Full test suite with coverage
python -m pytest --cov=create_embeddings --cov=searchapi --cov-fail-under=80

# Run specific test markers
python -m pytest -m unit    # Unit tests only
python -m pytest -m integration  # Integration tests only

# Test isolation verification (run multiple times)
for i in {1..5}; do python -m pytest path/to/specific_test.py; done
```

**Test Structure:**
- `pytest.ini`: Centralized config with markers (unit, integration, database, api)
- Coverage requirement: 80% minimum
- Async tests: `@pytest.mark.asyncio` with `asyncio_mode = auto`

## Docker Development Strategy

### Environment Parity
- **Development**: Docker containers for testing on macOS
- **Production**: Identical Docker setup on remote Linux server
- **Automation**: Easy, automated setup for both environments
- **Configuration**: Same Docker Compose files for dev/prod with environment overrides

### Container Architecture
```bash
# Development setup
docker-compose up --build

# Production deployment
docker-compose -f docker-compose.prod.yml up -d
```

## Development Workflows

**Environment Setup:**
```bash
# Always use virtual environment
python -m venv .venv && source .venv/bin/activate

# Configuration validation
python -c "from create_embeddings.book_processor_wrapper import validate_config; validate_config()"
```

**Book Processing Pipeline:**
```python
# Key injection points in book_processor_wrapper.py:
process_books_from_file() -> 
  EmbeddingProviderFactory.create_provider() ->
  ChunkingStrategyFactory.create_strategy() ->
  process_book() with injected dependencies
```

**Search API Pattern:**
```python
# Global service initialization in dhosearch.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_service, embedding_provider
    # Dependency injection setup
```

## Project-Specific Conventions

- **One Class Per File**: Enforced development rule
- **SOLID + GoF Patterns**: Architecture follows dependency injection throughout
- **Test-Driven Development**: Write failing test → implement → refactor → repeat
- **Provider Abstractions**: All external services (DB, embeddings, chunking) are swappable via interfaces

## Error Handling Patterns

- **Book Processing**: Continue on individual failures, log everything, save progress
- **API**: Standard HTTP status codes, client handles user messages  
- **Database**: ACID compliance, transaction safety via context managers
- **Logging**: File-based with 30-day rotation, structured for monitoring

## Performance Characteristics

- **Expected Load**: <500 requests/day (not optimized for high throughput)
- **Database**: PostgreSQL with pgvector for vector similarity
- **Embedding Storage**: Provider-specific table naming (chunks_openai, chunks_ollama, etc.)
- **Chunking Impact**: sentence_splitter preserves context, word_overlap ensures consistent size
