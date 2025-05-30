# Testing Guide for Semantic Search Prototype

This document describes how to run and develop tests for the semantic search prototype.

## Overview

The test suite is organized into:
- **Unit tests** (`tests/unit/`): Test individual functions and classes in isolation
- **Integration tests** (`tests/integration/`): Test component interactions and workflows
- **Fixtures** (`tests/fixtures/`): Shared test data and mock services

## Prerequisites

1. Install development dependencies:
```bash
make install
# or manually:
pip install -r requirements-dev.txt
```

2. Ensure you have the required environment variables (see `.env.example`)

## Running Tests

### Quick Start
```bash
# Run all tests
make test

# Run only unit tests
make test-unit

# Run only integration tests
make test-integration

# Run tests with coverage
make test-coverage
```

### Advanced Usage
```bash
# Run specific test file
python -m pytest tests/unit/test_text_processing.py -v

# Run tests matching a pattern
python -m pytest tests/ -k "test_chunking" -v

# Run tests with specific markers
python -m pytest tests/ -m "not slow" -v

# Run tests with detailed output
python -m pytest tests/ -v -s
```

## Test Structure

### Unit Tests
Located in `tests/unit/`, these test individual components:

- `test_text_processing.py` - Text chunking and processing functions
- `test_embedding_providers.py` - Embedding provider classes  
- `test_search_api.py` - FastAPI endpoints and request handling
- `test_search_engine.py` - Search engine class methods
- `test_database.py` - Database operation functions

### Integration Tests
Located in `tests/integration/`, these test complete workflows:

- `test_embedding_pipeline.py` - Full embedding creation workflow
- `test_search_pipeline.py` - Complete search request handling
- `test_api_integration.py` - API endpoint integration with database

### Test Fixtures
Located in `tests/fixtures/`:

- `test_data.json` - Sample books, embeddings, and search results
- `mocks.py` - Mock services for external dependencies
- `conftest.py` - Shared pytest fixtures and utilities

## Writing Tests

### Unit Test Example
```python
import pytest
from unittest.mock import patch
from create_embeddings.opret_bøger import chunk_text

@pytest.mark.unit
def test_chunk_text_basic():
    """Test basic text chunking functionality."""
    text = "Dette er en test. Dette er en anden sætning."
    chunks = list(chunk_text(text, max_tokens=5))
    
    assert len(chunks) > 0
    assert all(len(chunk.split()) <= 5 for chunk in chunks)

@pytest.mark.unit  
@patch('openai.OpenAI')
def test_embedding_generation(mock_openai, mock_openai_client):
    """Test embedding generation with mocked OpenAI."""
    # Test implementation here
    pass
```

### Integration Test Example
```python
import pytest
from httpx import AsyncClient

@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_endpoint_integration(mock_env_vars, mock_database_connection):
    """Test complete search endpoint with database."""
    # Test implementation here
    pass
```

## Test Configuration

### pytest.ini
Key settings:
- Test discovery patterns
- Coverage configuration  
- Async test support
- Custom markers

### Environment Variables
Tests use mocked environment variables by default. Override in `conftest.py` or specific tests as needed.

### Markers
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests  
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.database` - Tests requiring database
- `@pytest.mark.api` - API endpoint tests

## Mocking Strategy

### External Dependencies
- **OpenAI API**: Mocked to return consistent embeddings
- **Database**: In-memory SQLite or mocked PostgreSQL connections
- **HTTP requests**: Mocked aiohttp sessions
- **PDF processing**: Mocked PyMuPDF documents

### Mock Fixtures
Key fixtures available in `conftest.py`:
- `mock_openai_client` - Mocked OpenAI client
- `mock_database_connection` - Mocked database connection
- `sample_pdf_content` - Test PDF content
- `mock_env_vars` - Test environment variables

## Coverage

Target coverage: 80% minimum

View coverage report:
```bash
make test-coverage
# Open htmlcov/index.html in browser for detailed report
```

## Debugging Tests

### Verbose Output
```bash
python -m pytest tests/ -v -s --tb=long
```

### Debug Specific Test
```bash
python -m pytest tests/unit/test_specific.py::test_function -v -s
```

### Print Debugging
Use `print()` statements with `-s` flag, or use `pytest.set_trace()` for breakpoints.

## Continuous Integration

Tests run automatically on:
- Pull requests
- Main branch commits
- Manual triggers

Local CI simulation:
```bash
make clean
make lint
make test-coverage
```

## Performance Considerations

### Fast Tests
- Use mocks for all external dependencies
- Keep test data small
- Avoid real network requests
- Use in-memory databases

### Slow Tests
Mark with `@pytest.mark.slow` and exclude from quick runs:
```bash
python -m pytest tests/ -m "not slow"
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure PYTHONPATH includes project root
2. **Async test failures**: Check pytest-asyncio configuration
3. **Mock not working**: Verify patch targets and mock setup
4. **Database errors**: Ensure test database is properly mocked

### Getting Help

1. Check test output with `-v` flag
2. Review `conftest.py` for available fixtures
3. Look at existing tests for patterns
4. Check pytest documentation for advanced features

## Adding New Tests

1. Determine if test should be unit or integration
2. Place in appropriate directory
3. Use descriptive test names
4. Add appropriate markers
5. Mock external dependencies
6. Include docstrings explaining test purpose
7. Update this documentation if needed

## Test Data Management

- Keep test data minimal but realistic
- Use factories (Faker) for varied test data
- Store common test data in `fixtures/test_data.json`
- Clean up any created resources in teardown
