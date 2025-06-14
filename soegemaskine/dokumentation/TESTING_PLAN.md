# Testing Plan for Issue #3: Create Unit and Integration Tests

## Overview
This plan details the implementation of comprehensive testing for the semantic search soegemaskine, including both unit tests (with mocks) and integration tests for the embedding creation and search API components.

## Current Architecture Analysis

### Components to Test:
1. **Embedding Creation (`create_embeddings/opret_bøger.py`)**
   - PDF processing and text extraction
   - Text chunking logic
   - Embedding generation (with OpenAI API)
   - Database storage operations
   - EmbeddingProvider abstraction (already exists)

2. **Search API (`soegemaskine/searchapi/dhosearch.py`)**
   - FastAPI endpoints
   - Search request parsing
   - Embedding generation for search queries
   - Database search operations
   - Response formatting

3. **Flask Frontend (`webpage_flask/`)**
   - Search form processing
   - API communication
   - Result display logic

## Implementation Plan

### Phase 1: Setup Testing Infrastructure

#### 1.1 Create Test Dependencies File
- **File**: `soegemaskine/requirements-dev.txt`
- **Content**: Testing frameworks and dependencies
  ```
  pytest
  pytest-asyncio
  pytest-mock
  httpx  # For FastAPI testing
  unittest-mock
  faker  # For generating test data
  sqlite3  # For test database
  ```

#### 1.2 Create Test Directory Structure
```
soegemaskine/
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest configuration and fixtures
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_embedding_providers.py
│   │   ├── test_text_processing.py
│   │   ├── test_chunking.py
│   │   └── test_search_logic.py
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_embedding_pipeline.py
│   │   ├── test_search_api.py
│   │   └── test_database_operations.py
│   └── fixtures/
│       ├── mock_book.pdf
│       ├── sample_text.txt
│       └── test_data.json
```

### Phase 2: Unit Tests

#### 2.1 Embedding Provider Tests (`test_embedding_providers.py`)
- Test `DummyEmbeddingProvider` returns correct format
- Test `OpenAIEmbeddingProvider` with mocked API calls
- Test `EmbeddingProviderFactory` creation logic
- Test error handling for invalid providers

#### 2.2 Text Processing Tests (`test_text_processing.py`)
- Test PDF text extraction with mock PDFs
- Test text cleaning functions
- Test edge cases (empty text, special characters)
- Test `extract_text_from_chunk` function

#### 2.3 Chunking Logic Tests (`test_chunking.py`)
- Test `chunk_text` function with various inputs
- Test chunk size limits
- Test sentence boundary detection
- Test handling of short texts
- Test chunking with different token limits

#### 2.4 Search Logic Tests (`test_search_logic.py`)
- Test embedding generation for search queries
- Test distance function calculations
- Test result formatting
- Test database query construction (with mocked DB)

### Phase 3: Integration Tests

#### 3.1 Embedding Pipeline Tests (`test_embedding_pipeline.py`)
- **Mock Book Setup**: Create a small test PDF
- **Mock OpenAI API**: Use `DummyEmbeddingProvider`
- **SQLite Test DB**: Use in-memory SQLite for database operations
- **Test Flow**:
  1. Load mock book
  2. Extract and chunk text
  3. Generate embeddings (mocked)
  4. Store in test database
  5. Verify data integrity

#### 3.2 Search API Tests (`test_search_api.py`)
- **FastAPI Test Client**: Use `httpx.AsyncClient`
- **Mock Dependencies**: Mock OpenAI and database
- **Test Scenarios**:
  1. Basic search request/response
  2. Different chunk sizes and distance functions
  3. Error handling (invalid requests, API failures)
  4. CORS headers
  5. Response format validation

#### 3.3 Database Operations Tests (`test_database_operations.py`)
- **Test Database Setup**: Use SQLite with same schema
- **Test Operations**:
  1. Book insertion
  2. Chunk storage
  3. Vector similarity search
  4. Database connection handling
  5. Transaction rollback on errors

### Phase 4: Test Data and Fixtures

#### 4.1 Mock Data Creation
- **Mock PDF**: Small PDF with known text content
- **Test Embeddings**: Predictable dummy vectors
- **Sample Queries**: Various search scenarios
- **Expected Results**: Known good responses for validation

#### 4.2 Database Fixtures
- **Schema Setup**: SQLite version of PostgreSQL schema
- **Sample Data**: Pre-populated test data
- **Cleanup**: Automatic test data cleanup

### Phase 5: Refactoring for Testability

#### 5.1 Dependency Injection
- Extract database connections as injectable dependencies
- Make OpenAI client configurable/injectable
- Separate pure functions from side effects

#### 5.2 Configuration Management
- Environment-based configuration for tests
- Separate test configuration files
- Mock-friendly configuration patterns

## Implementation Timeline

### Week 1: Infrastructure Setup
- [ ] Create requirements-dev.txt
- [ ] Set up test directory structure
- [ ] Create basic conftest.py with fixtures
- [ ] Set up pytest configuration

### Week 2: Unit Tests
- [ ] Implement embedding provider tests
- [ ] Implement text processing tests
- [ ] Implement chunking logic tests
- [ ] Implement search logic tests

### Week 3: Integration Tests
- [ ] Create mock data and fixtures
- [ ] Implement embedding pipeline tests
- [ ] Implement search API tests
- [ ] Implement database operation tests

### Week 4: Documentation and CI/CD
- [ ] Document how to run tests locally
- [ ] Create test documentation
- [ ] Set up CI/CD pipeline (optional)
- [ ] Performance benchmarks for tests

## Running Tests Locally

### Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Set up test environment variables
export TEST_ENV=true
export DATABASE_URL=sqlite:///test.db
export OPENAI_API_KEY=dummy_key_for_tests
```

### Running Tests
```bash
# Run all tests
pytest

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run with coverage
pytest --cov=searchapi --cov=create_embeddings

# Run specific test file
pytest tests/unit/test_embedding_providers.py -v
```

## Success Criteria

### Unit Tests
- [ ] 90%+ code coverage for testable functions
- [ ] All embedding providers work correctly
- [ ] Text processing handles edge cases
- [ ] Chunking logic produces consistent results
- [ ] Search logic generates correct queries

### Integration Tests
- [ ] End-to-end embedding pipeline works with mock data
- [ ] Search API returns correct responses
- [ ] Database operations maintain data integrity
- [ ] Error handling works across all components
- [ ] Performance within acceptable limits

### Documentation
- [ ] Clear instructions for running tests
- [ ] Documentation of test scenarios
- [ ] Examples of adding new tests
- [ ] Troubleshooting guide for common issues

## Benefits of This Testing Strategy

1. **Confidence**: Comprehensive test coverage ensures reliable deployments
2. **Development Speed**: Faster debugging and feature development
3. **Refactoring Safety**: Can safely modify code with test coverage
4. **Documentation**: Tests serve as living documentation
5. **Quality Assurance**: Catches bugs early in development cycle
