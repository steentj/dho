# Installation Guide

## Oversigt

Denne guide fører dig gennem installation og opsætning af DHO Semantisk Søgemaskine systemet på både macOS og Linux.

## 📋 **Forudsætninger**

### System Krav

- **Operativsystem**: macOS 10.15+ eller Linux (Ubuntu 18.04+, CentOS 7+)
- **RAM**: Minimum 8GB (16GB anbefalet for Ollama)
- **Disk**: Minimum 10GB fri plads
- **Netværk**: Internet forbindelse til download af dependencies

### Software Dependencies

- **Docker**: Version 20.10+
- **Docker Compose**: Version 2.0+
- **Git**: Til kodebase access
- **Terminal**: Bash eller zsh shell

## 🚀 **Installation**

### Trin 1: Install Docker

#### macOS

```bash
# Download Docker Desktop fra https://www.docker.com/products/docker-desktop
# Eller via Homebrew:
brew install --cask docker
```

#### Linux (Ubuntu/Debian)

```bash
# Opdatér package liste
sudo apt update

# Installér Docker
sudo apt install docker.io docker-compose-plugin

# Tilføj bruger til docker group
sudo usermod -aG docker $USER

# Log ud og ind igen for at aktivere group membership
```

#### Linux (CentOS/RHEL)

```bash
# Installér Docker
sudo yum install -y docker docker-compose

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Tilføj bruger til docker group
sudo usermod -aG docker $USER
```

### Trin 2: Verificér Docker Installation

```bash
# Test Docker
docker --version
docker compose version

# Test at Docker kører
docker run hello-world
```

### Trin 3: Hent Kodebase

```bash
# Navigér til ønsket installation directory
cd /path/to/your/projects

# Clone repository
git clone [repository-url] SlægtBib
cd SlægtBib/src
```

### Trin 4: Konfigurér Environment

```bash
# Kopiér environment template
cp .env.template .env

# Redigér konfiguration
nano .env  # eller din foretrukne editor
```

#### Minimum Konfiguration

For hurtig test, sæt i `.env`:
```bash
# Database
POSTGRES_HOST=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=test123
POSTGRES_DB=dhodb

# Embeddings (vælg en)
PROVIDER=dummy  # Til hurtig test
# ELLER
PROVIDER=ollama  # Til lokale embeddings
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=nomic-embed-text
```

### Trin 5: Validér Installation

```bash
# Validér konfiguration
./scripts/process_books.sh --validate

# Forventet output:
# ✅ Alle påkrævede miljøvariabler er sat og gyldige
# Udbyder: dummy (eller ollama)
# Chunking Strategy: sentence_splitter
# Chunk Størrelse: 500
```

## 🔧 **Provider-Specifik Opsætning**

### Ollama (Lokale Embeddings)

#### Trin 1: Start Ollama Service

```bash
cd soegemaskine
docker-compose --profile embeddings up -d ollama
```

#### Trin 2: Installér Embedding Model

```bash
# Automatisk installation
../scripts/setup_ollama.sh

# Eller manuel installation
docker exec -it soegemaskine-ollama-1 ollama pull nomic-embed-text
```

#### Trin 3: Verificér Ollama

```bash
# Test Ollama API
curl http://localhost:11434/api/embeddings \
  -d '{"model": "nomic-embed-text", "prompt": "test"}' \
  -H "Content-Type: application/json"
```

### OpenAI (Cloud Embeddings)

#### Trin 1: Få API Nøgle

1. Gå til https://platform.openai.com/api-keys
2. Opret ny API nøgle
3. Kopiér nøglen (den vises kun én gang)

#### Trin 2: Konfigurér Environment

```bash
# Tilføj til .env fil
PROVIDER=openai
OPENAI_API_KEY=sk-proj-your-api-key-here
OPENAI_MODEL=text-embedding-3-small
```

#### Trin 3: Test API Forbindelse

```bash
# Validér konfiguration inkluderer API test
./scripts/process_books.sh --validate
```

## 🗄️ **Database Opsætning**

### Start Database Service

```bash
cd soegemaskine
docker-compose up -d postgres
```

### Verificér Database

```bash
# Test database forbindelse
docker exec -it dhodb psql -U steen -d WW2 -c "SELECT version();"
```

-U angiver database brugeren. Sæt den korrekte
-d database navn

### Database Migration (hvis nødvendigt)

Systemet opretter automatisk tabeller ved første kørsel. Ingen manuel migration nødvendig.

## 📝 **Test Installation**

### Minimum Funktionalitet Test

```bash
# Opret test bog liste
echo "https://example.com/test.pdf" > test_books.txt

# Test bog processering (dry run)
./scripts/process_books.sh --file test_books.txt --validate-only
```

### Komplet System Test

```bash
# Start alle services
cd soegemaskine
docker-compose --profile embeddings up -d

# Vent på services starter (30-60 sekunder)
sleep 60

# Test søgemaskine API
curl http://localhost:8080/health

# Forventet response: {"status": "healthy"}
```

## 🐛 **Almindelige Installationsproblemer**

### Docker Permission Fejl

```bash
# Problem: "permission denied while trying to connect to Docker"
# Løsning: Tilføj bruger til docker group
sudo usermod -aG docker $USER
# Log ud og ind igen
```

### Port Konflikter

```bash
# Problem: "Port 5432 already in use"
# Løsning: Stop eksisterende PostgreSQL
sudo systemctl stop postgresql
# Eller ændr port i docker-compose.yml
```

### Ollama Model Download Fejl

```bash
# Problem: "model download failed"
# Løsning: Tjek internet forbindelse og prøv igen
docker exec -it soegemaskine-ollama-1 ollama pull nomic-embed-text

# Eller prøv mindre model
docker exec -it soegemaskine-ollama-1 ollama pull all-minilm
```

### Insufficient Memory

```bash
# Problem: "container killed (OOMKilled)"
# Løsning: Øg Docker memory limit
# I Docker Desktop: Settings > Resources > Memory > 8GB+
```

## 📊 **Performance Optimering**

### Udvikling Environment

```bash
# Minimal resource usage
PROVIDER=dummy
CHUNK_SIZE=300
LOG_LEVEL=WARNING
```

### Produktion Environment

```bash
# Optimal for performance
PROVIDER=ollama  # eller openai
CHUNK_SIZE=500
LOG_LEVEL=INFO

# Docker Compose optimering
docker-compose --profile embeddings up -d --scale postgres=1
```

## 🔄 **Opdatering og Vedligeholdelse**

### Opdatér System

```bash
# Hent seneste kode
git pull origin main

# Genstart services
cd soegemaskine
docker-compose down
docker-compose --profile embeddings up -d
```

### Database Backup

```bash
# Backup database
docker exec soegemaskine-postgres-1 pg_dump -U postgres dhodb > backup.sql

# Restore backup
cat backup.sql | docker exec -i soegemaskine-postgres-1 psql -U postgres -d dhodb
```

## 📞 **Næste Skridt**

Efter vellykket installation:

1. **Læs [Bog Processering Guide](BOG_PROCESSERING.md)** - Lær at tilføje bøger til systemet
2. **Gennemgå [Konfigurationsguide](../KONFIGURATION.md)** - Optimer systemet til dine behov
3. **Uddyb i [Lokal Udvikling](LOKAL_UDVIKLING.md)** - Sæt udvikling environment op

---

**Problemer?** Se [fejlfinding section](LOKAL_UDVIKLING.md#fejlfinding) eller kontakt support team.
