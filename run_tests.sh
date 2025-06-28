#!/bin/bash
# run_tests.sh

# Set working directory
cd "$(dirname "$0")"

# Run diagnostic script
echo "Running diagnostic script..."
python diagnose_imports.py

# Run all tests including integration tests
echo "Running all tests..."
python -m pytest create_embeddings/tests/integration create_embeddings/tests/test_providers.py soegemaskine/tests/unit/test_embedding_providers.py -v

# Run coverage check
echo "Running coverage check..."
python -m pytest soegemaskine/tests/unit/test_embedding_providers.py::TestOllamaEmbeddingProvider -v --cov=create_embeddings.providers.embedding_providers --cov-report term-missing

echo "Done!"
