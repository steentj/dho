# Lokal Udvikling Guide

## Oversigt

Denne guide hjælper udviklere med at sætte et komplet udviklingsenvironment op til DHO Semantisk Søgemaskine systemet.

## 🛠 **Udviklings Setup**

### Forudsætninger
- Python 3.12+
- Docker og Docker Compose
- Git
- Foretrukken IDE (VS Code anbefalet)

### Initial Setup
```bash
# Clone repository
git clone [repository-url] SlægtBib
cd SlægtBib/src

# Opret development environment
cp .env.template .env

# Konfigurér for lokal udvikling
nano .env
```

### Development Environment Konfiguration
```bash
# .env for lokal udvikling
POSTGRES_HOST=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=dev123
POSTGRES_DB=dhodb_dev

# Brug dummy provider for hurtig udvikling
PROVIDER=dummy

# Eller Ollama for realistisk testing
PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=nomic-embed-text

# Development specifics
LOG_LEVEL=DEBUG
CHUNK_SIZE=300  # Mindre chunks for hurtigere testing
```

## 🐍 **Python Development**

### Virtual Environment Setup
```bash
# Opret virtual environment
python -m venv venv

# Aktivér (macOS/Linux)
source venv/bin/activate

# Aktivér (Windows)
venv\Scripts\activate

# Installer dependencies
pip install -r create_embeddings/requirements.txt
pip install -r database/requirements.txt  # hvis eksisterer
```

### Development Dependencies
```bash
# Installer test og development tools
pip install pytest pytest-asyncio pytest-cov
pip install black flake8 mypy
pip install jupyter  # til notebook udvikling
```

### Code Style Setup
```bash
# Formattér kode
black create_embeddings/ database/ soegemaskine/

# Lint kode
flake8 create_embeddings/ database/

# Type checking
mypy create_embeddings/ database/
```

## 🧪 **Testing**

### Test Environment Setup
```bash
# Sæt test database op
POSTGRES_HOST=localhost POSTGRES_DB=test_dhodb python -c "
import asyncpg
import asyncio
async def setup():
    conn = await asyncpg.connect('postgresql://postgres:dev123@localhost/postgres')
    await conn.execute('DROP DATABASE IF EXISTS test_dhodb')
    await conn.execute('CREATE DATABASE test_dhodb')
    await conn.close()
asyncio.run(setup())
"
```

### Kør Tests
```bash
# Alle tests
pytest

# Specifikke test moduler
pytest create_embeddings/tests/
pytest database/tests/

# Med coverage
pytest --cov=create_embeddings --cov-report=html

# Async tests
pytest -v create_embeddings/tests/test_book_processing_injection.py

# Integration tests
pytest create_embeddings/tests/integration/
```

### Test Konfiguration
Tests bruger automatisk test environment med:
- Dummy embedding provider
- Separate test database
- Mock eksterne services

## 🐳 **Docker Development**

### Lokal Docker Services
```bash
# Start kun database for udvikling
cd soegemaskine
docker-compose up -d postgres

# Start database og Ollama
docker-compose --profile embeddings up -d postgres ollama

# Stop services
docker-compose down
```

### Development Container
```bash
# Byg development image
docker build -t dho-dev -f create_embeddings/Dockerfile .

# Kør interaktiv container
docker run -it --rm \
  -v $(pwd):/app \
  -e POSTGRES_HOST=host.docker.internal \
  --network soegemaskine_default \
  dho-dev bash
```

## 🔍 **Debugging**

### Python Debugging
```python
# Tilføj breakpoints i kode
import pdb; pdb.set_trace()

# Eller med ipdb (bedre interface)
import ipdb; ipdb.set_trace()

# VS Code debugging - tilføj til launch.json:
{
    "name": "Debug Book Processor",
    "type": "python",
    "request": "launch",
    "program": "create_embeddings/book_processor_wrapper.py",
    "args": ["--validate-config"],
    "console": "integratedTerminal",
    "env": {"LOG_LEVEL": "DEBUG"}
}
```

### Database Debugging
```bash
# Connect til database
docker exec -it soegemaskine-postgres-1 psql -U postgres -d dhodb

# Tjek tabeller
\dt

# Query chunks
SELECT id, page_number, substring(chunk_text, 1, 100) FROM chunks LIMIT 5;

# Query embeddings
SELECT embedding_id, provider, substring(chunk_text, 1, 50) FROM openai_embeddings LIMIT 3;
```

### Container Debugging
```bash
# Inspicér running container
docker exec -it soegemaskine-book-processor-1 bash

# Tjek logs
docker logs soegemaskine-book-processor-1 -f

# Container stats
docker stats
```

## 📊 **Performance Profiling**

### Python Profiling
```bash
# Basic profiling
python -m cProfile -o profile.stats create_embeddings/opret_bøger.py

# Analyse profiling results
python -c "
import pstats
p = pstats.Stats('profile.stats')
p.sort_stats('cumulative').print_stats(10)
"

# Memory profiling
pip install memory-profiler
python -m memory_profiler create_embeddings/book_processor_wrapper.py
```

### Database Performance
```sql
-- Slow query analysis
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- Index usage
SELECT schemaname, tablename, attname, n_distinct, correlation 
FROM pg_stats 
WHERE tablename IN ('chunks', 'openai_embeddings');
```

## 🧩 **Udviklings Workflow**

### Feature Development
```bash
# 1. Opret feature branch
git checkout -b feature/ny-chunking-strategy

# 2. Udvikl og test
pytest create_embeddings/tests/test_chunking.py -v

# 3. Formattér kode
black create_embeddings/chunking.py
flake8 create_embeddings/chunking.py

# 4. Commit changes
git add .
git commit -m "Add: Ny chunking strategy implementering"

# 5. Test integration
./scripts/process_books.sh --validate
```

### Code Review Checklist
- [ ] Alle tests passerer
- [ ] Code er formateret med black
- [ ] Ingen flake8 warnings
- [ ] Type hints tilføjet (mypy)
- [ ] Docstrings opdateret
- [ ] Configuration validation opdateret hvis nødvendigt
- [ ] Integration tests kører

## 🔧 **Common Development Tasks**

### Tilføj Ny Embedding Provider
```python
# 1. Udvid EmbeddingProvider base class
class NewProvider(EmbeddingProvider):
    async def get_embedding(self, text: str) -> List[float]:
        # Implementation
        pass
    
    def get_table_name(self) -> str:
        return "new_provider_embeddings"

# 2. Registrér i factory
# I EmbeddingProviderFactory.create_provider()
elif provider == "new_provider":
    return NewProvider(api_key)

# 3. Opdatér validation
# I validate_config()
elif provider == "new_provider":
    required_vars.extend(["NEW_PROVIDER_API_KEY"])

# 4. Tilføj tests
class TestNewProvider:
    def test_get_embedding(self):
        # Test implementation
```

### Tilføj Ny Chunking Strategy
```python
# 1. Udvid ChunkingStrategy
class NewChunkingStrategy(ChunkingStrategy):
    def chunk_text(self, text: str, max_tokens: int, title: str = "") -> List[str]:
        # Implementation
        pass

# 2. Registrér i factory
# I ChunkingStrategyFactory.create_strategy()
elif strategy == "new_strategy":
    return NewChunkingStrategy()

# 3. Opdatér validation
# I validate_config()
valid_strategies = ["sentence_splitter", "word_overlap", "new_strategy"]

# 4. Dokumentér i CHUNKING_STRATEGIER.md
```

## 📝 **Documentation Development**

### Opdatér Dokumentation
```bash
# Test dokumentation links
find documentation/ -name "*.md" -exec grep -l "broken-link" {} \;

# Validate markdown
markdownlint documentation/**/*.md

# Preview dokumentation
# Installer markdown viewer eller brug VS Code preview
```

## 🐛 **Fejlfinding**

### Almindelige Udviklings Problemer

#### Import Errors
```python
# Problem: ModuleNotFoundError
# Løsning: Tilføj src til Python path
import sys
sys.path.append('/path/to/SlægtBib/src')

# Eller brug relative imports
from .providers import EmbeddingProviderFactory
```

#### Database Connection Issues
```bash
# Problem: Database connection refused
# Løsning: Sørg for at PostgreSQL kører
docker-compose up -d postgres

# Tjek database er tilgængelig
pg_isready -h localhost -p 5432
```

#### Docker Build Failures
```bash
# Problem: Docker build fails
# Løsning: Clean docker cache
docker system prune -f

# Rebuild from scratch
docker build --no-cache -t dho-dev .
```

#### Async Test Issues
```python
# Problem: RuntimeError: There is no current event loop
# Løsning: Brug pytest-asyncio
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

### Memory Debugging
```bash
# Find memory leaks
valgrind --tool=memcheck python create_embeddings/book_processor_wrapper.py

# Monitor container memory
docker exec soegemaskine-book-processor-1 cat /proc/meminfo
```

### Network Debugging
```bash
# Test internal Docker networking
docker exec soegemaskine-book-processor-1 nc -zv postgres 5432
docker exec soegemaskine-book-processor-1 nc -zv ollama 11434

# Test external connectivity
docker exec soegemaskine-book-processor-1 curl -I https://api.openai.com
```

## 🚀 **Production Deployment**

### Pre-deployment Checklist
- [ ] Alle tests passerer
- [ ] Performance benchmarks mødt
- [ ] Security audit gennemført
- [ ] Configuration valideret
- [ ] Database migration planlagt
- [ ] Rollback plan klar
- [ ] Monitoring setup verificeret

### Environment Parity
Sørg for at development environment matcher production:
- Samme Docker images
- Samme environment variabler struktur
- Samme chunking og embedding konfiguration
- Lignende data volumens

---

**Næste skridt:**
- Se [Konfigurationsguide](../KONFIGURATION.md) for advanced settings
- Gennemgå [System Arkitektur](../TEKNISK/ARKITEKTUR.md) for dybere forståelse
- Bidrag til [testing strategy](../ARKIV/) documentation
