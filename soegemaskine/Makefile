# Makefile for Semantic Search soegemaskine Development and Testing

.PHONY: help install test test-unit test-integration test-coverage clean lint format docker-test

# Default target
help:
	@echo "Available targets:"
	@echo "  install          Install development dependencies"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-coverage    Run tests with coverage report"
	@echo "  lint             Run linting (mypy, black check)"
	@echo "  format           Format code with black"
	@echo "  clean            Clean up generated files"
	@echo "  docker-test      Run tests in Docker environment"
	@echo "  validate-env     Validate current .env (root)"
	@echo "  health-check     Curl /healthz and /readyz endpoints"

# Install development dependencies
install:
	@echo "Installing development dependencies..."
	pip install -r requirements-dev.txt
	pip install -r searchapi/requirements.txt

# Run all tests
test:
	@echo "Running all tests..."
	python -m pytest tests/ -v

# Run unit tests only
test-unit:
	@echo "Running unit tests..."
	python -m pytest tests/unit/ -v -m unit

# Run integration tests only  
test-integration:
	@echo "Running integration tests..."
	python -m pytest tests/integration/ -v -m integration

# Run tests with coverage
test-coverage:
	@echo "Running tests with coverage..."
	python -m pytest tests/ --cov=searchapi --cov=../create_embeddings --cov-report=html --cov-report=term-missing

# Run quick tests (exclude slow tests)
test-quick:
	@echo "Running quick tests..."
	python -m pytest tests/ -v -m "not slow"

# Lint code
lint:
	@echo "Running linting..."
	python -m mypy searchapi/ || true
	python -m mypy ../create_embeddings/ || true
	python -m black --check searchapi/ tests/ || true

# Format code
format:
	@echo "Formatting code..."
	python -m black searchapi/ tests/
	python -m black ../create_embeddings/

# Clean up generated files
clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf htmlcov/ .coverage .pytest_cache/ 2>/dev/null || true

# Run tests in Docker environment (optional)
docker-test:
	@echo "Running tests in Docker..."
	docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit

# Validate environment configuration (root .env)
validate-env:
	@echo "Validating root .env ..."
	python ../scripts/validate_env.py --json || true

# Health checks (requires stack running)
health-check:
	@echo "GET /healthz" && curl -s http://localhost:8080/healthz | python -m json.tool || true
	@echo "GET /readyz" && curl -s -o /dev/stderr -w "\nHTTP:%{http_code}\n" http://localhost:8080/readyz || true

# Setup test database (if needed)
setup-test-db:
	@echo "Setting up test database..."
	# This would set up a test PostgreSQL database if needed
	@echo "Test database setup complete"

# Run specific test file
test-file:
	@read -p "Enter test file path: " filepath; \
	python -m pytest $$filepath -v

# Run tests matching pattern
test-pattern:
	@read -p "Enter test pattern: " pattern; \
	python -m pytest tests/ -k "$$pattern" -v

# Check test dependencies
check-deps:
	@echo "Checking test dependencies..."
	python -c "import pytest, pytest_asyncio, pytest_mock, pytest_cov, httpx, faker; print('All test dependencies available')"

# ---------------------------------------------------------------------------
# Stage 4 Modular Docker Compose Targets
# ---------------------------------------------------------------------------

COMPOSE_BASE=-f docker-compose.base.yml
COMPOSE_EMBED=-f docker-compose.embeddings.yml
COMPOSE_EDGE=-f docker-compose.edge.yml

.PHONY: up-minimal up-local up-prod down-stacks compose-config ps-stacks logs-stacks

up-minimal:
	@echo "Starting minimal stack (postgres + searchapi)" 
	docker compose $(COMPOSE_BASE) up -d

up-minimal-clean:
	@echo "Starting minimal stack (clean) and removing orphans" 
	docker compose $(COMPOSE_BASE) up -d --remove-orphans

up-local:
	@echo "Starting local stack (base + embeddings services)"
	docker compose $(COMPOSE_BASE) $(COMPOSE_EMBED) up -d

up-prod:
	@echo "Starting production stack (base + embeddings + edge)"
	docker compose $(COMPOSE_BASE) $(COMPOSE_EMBED) $(COMPOSE_EDGE) up -d

down-stacks:
	@echo "Stopping all modular stacks"
	docker compose $(COMPOSE_BASE) $(COMPOSE_EMBED) $(COMPOSE_EDGE) down

compose-config:
	@echo "Merged configuration (local)" 
	docker compose $(COMPOSE_BASE) $(COMPOSE_EMBED) config

ps-stacks:
	docker compose $(COMPOSE_BASE) ps

logs-stacks:
	docker compose $(COMPOSE_BASE) logs -f

# ---------------------------------------------------------------------------
# Stage 5 Shadow Search Targets
# ---------------------------------------------------------------------------

SHADOW_COMPOSE=-f docker-compose.base.yml -f docker-compose.shadow.yml

.PHONY: shadow-up shadow-up-ollama shadow-up-openai shadow-down shadow-query shadow-compare

shadow-up:
	@echo "Starting shadow search (inherits provider from .env)"
	docker compose $(SHADOW_COMPOSE) up -d postgres searchapi-shadow

shadow-up-ollama:
	@echo "Starting shadow search with provider=ollama"
	docker compose $(SHADOW_COMPOSE) up -d postgres
	docker compose $(SHADOW_COMPOSE) rm -f searchapi-shadow >/dev/null 2>&1 || true
	docker compose $(SHADOW_COMPOSE) run -d --name dhosearch-shadow -e PROVIDER=ollama -e OLLAMA_MODEL=nomic-embed-text searchapi-shadow

shadow-up-openai:
	@echo "Starting shadow search with provider=openai"
	docker compose $(SHADOW_COMPOSE) up -d postgres
	docker compose $(SHADOW_COMPOSE) rm -f searchapi-shadow >/dev/null 2>&1 || true
	docker compose $(SHADOW_COMPOSE) run -d --name dhosearch-shadow -e PROVIDER=openai searchapi-shadow

shadow-down:
	@echo "Stopping shadow search"
	docker compose $(SHADOW_COMPOSE) down --remove-orphans

shadow-query:
	@read -p "Enter query: " q; curl -s -X POST http://localhost:18000/search -H 'Content-Type: application/json' -d '{"query": "'"$$q"'"}' | python3 -m json.tool

shadow-compare:
	python ../scripts/compare_search_results.py --queries shadow_queries.txt --main http://localhost:8080 --shadow http://localhost:18000 --top 5 --output shadow_comparison.json
	@echo "Comparison written to soegemaskine/shadow_comparison.json"
