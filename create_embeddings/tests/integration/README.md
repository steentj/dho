# Integration Tests Setup

## Overview
The integration tests in `create_embeddings/tests/integration/` test the complete embedding system including database operations and provider integrations.

## Prerequisites

### PostgreSQL Database
The tests require a PostgreSQL database. Environment variables are automatically set for local testing:

- `POSTGRES_USER=postgres`
- `POSTGRES_PASSWORD=postgres`
- `POSTGRES_HOST=localhost`
- `POSTGRES_PORT=5432`
- `POSTGRES_DB=test_db`

### Running PostgreSQL
Ensure PostgreSQL is running on localhost:5432. Check with:
```bash
pg_isready -h localhost -p 5432
```

## Running Tests

### Command Line
```bash
# Run all integration tests
POSTGRES_USER=postgres POSTGRES_PASSWORD=postgres POSTGRES_HOST=localhost POSTGRES_PORT=5432 pytest create_embeddings/tests/integration/ -v

# Run specific test
POSTGRES_USER=postgres POSTGRES_PASSWORD=postgres POSTGRES_HOST=localhost POSTGRES_PORT=5432 pytest create_embeddings/tests/integration/test_embedding_integration.py::test_ollama_embedding_generation -v
```

### VS Code
The tests should now work in VS Code's test panel. Environment variables are automatically configured through:

1. `.env.test` file in project root
2. VS Code settings in `.vscode/settings.json`
3. Automatic fallback values in `conftest.py`

### Environment Configuration
Environment variables are loaded in order of preference:

1. Existing environment variables (highest priority)
2. `.env.test` file 
3. Default values in conftest.py (lowest priority)

## Test Structure

### Available Tests
- `test_ollama_embedding_generation`: Tests embedding generation and database storage
- `test_similarity_search`: Tests similarity search functionality
- `test_cross_provider_compatibility`: Tests multiple embedding providers
- `test_batch_processing_performance`: Performance tests with different batch sizes

### Test Markers
- `@pytest.mark.integration`: Integration tests requiring external services
- `@pytest.mark.benchmark`: Performance/benchmark tests
- `@pytest.mark.database`: Tests requiring database access

## Troubleshooting

### Database Connection Issues
If tests fail with connection errors:

1. Verify PostgreSQL is running: `pg_isready -h localhost -p 5432`
2. Check credentials match your PostgreSQL setup
3. Tests will automatically skip if database is unavailable

### VS Code Test Panel Issues
If tests don't appear or fail in VS Code:

1. Reload VS Code window
2. Check Python interpreter is correct (.venv)
3. Verify `.env.test` file exists
4. Check VS Code settings in `.vscode/settings.json`

### Environment Variables
Current test environment can be checked:
```python
import os
print("POSTGRES_HOST:", os.getenv("POSTGRES_HOST"))
```
