# Bog Processering Guide

## Oversigt

Denne guide viser hvordan du tilføjer bøger til DHO Semantisk Søgemaskine systemet. Du kører alt fra din **værtsmaskine terminal** - du behøver aldrig at gå ind i Docker container terminaler.

## 🚀 **Hurtig Start**

### Forudsætninger
1. Docker og Docker Compose installeret
2. System konfigureret (se [Installation Guide](INSTALLATION.md))
3. Database og embedding service kørende

### Grundlæggende Workflow
```bash
# 1. Validér konfiguration
./scripts/process_books.sh --validate

# 2. Processér bøger
./scripts/process_books.sh --file mine_boeger.txt

# 3. Overvåg fremgang
./scripts/process_books.sh --monitor

# 4. Genprøv fejlede bøger
./scripts/process_books.sh --retry
```

## 📝 **Forberedelse**

### Opret Bogliste
Opret en tekstfil på din værtsmaskine med én URL per linje:

```bash
# Opret fil
nano mine_boeger.txt

# Eksempel indhold:
https://example.com/bog1.pdf
https://example.com/bog2.pdf
https://example.com/bog3.pdf
```

### Understøttede Formater
- **PDF filer**: Primært understøttet format
- **URL krav**: Direkte links til PDF filer
- **Filstørrelse**: Anbefalet under 50MB per fil

## 🔧 **Processering Kommandoer**

### Validér Konfiguration
```bash
./scripts/process_books.sh --validate
```

**Hvad sker der:**
- Starter midlertidig Docker container
- Validerer `.env` fil konfiguration
- Tester database forbindelse
- Verificerer embedding provider
- Fjerner container efter test

**Forventet output:**
```
✅ Alle påkrævede miljøvariabler er sat og gyldige
Udbyder: ollama
Chunking Strategy: sentence_splitter
Chunk Størrelse: 500
Database forbindelse: OK
Embedding provider: OK
```

### Processér Bøger
```bash
./scripts/process_books.sh --file mine_boeger.txt
```

**Processerings flow:**
1. Starter processing container
2. Læser bog URLs fra fil
3. Downloader og analyserer hver bog
4. Opdeler tekst i chunks via valgt strategi
5. Genererer embeddings via valgt provider
6. Gemmer til database
7. Genererer status rapport

### Overvåg Fremgang
```bash
# Real-time monitoring
./scripts/process_books.sh --monitor

# Eller tjek status fil
cat output/processing_status.json
```

**Status fil eksempel:**
```json
{
  "status": "kører",
  "total_boeger": 10,
  "behandlet": 7,
  "fejlet": 1,
  "sidst_opdateret": "2025-06-30T14:30:00",
  "embedding_model": "nomic-embed-text",
  "udbyder": "ollama"
}
```

### Genprøv Fejlede Bøger
```bash
./scripts/process_books.sh --retry
```

**Hvad sker der:**
- Læser fejlede bøger fra `failed/failed_books.json`
- Opretter ny bog liste med kun fejlede URLs
- Genprocesserer med samme konfiguration
- Opdaterer status og fejl statistikker

## 📊 **Processing Strategier**

### Chunking Strategier

#### Sentence Splitter (Standard)
```bash
# I .env fil
CHUNKING_STRATEGY=sentence_splitter
CHUNK_SIZE=500
```

**Karakteristika:**
- Opdeler efter sætninger
- Respekterer max tokens (CHUNK_SIZE)
- Tilføjer bog titel til hver chunk
- Bedst til: Generel tekst søgning

#### Word Overlap
```bash
# I .env fil
CHUNKING_STRATEGY=word_overlap
CHUNK_SIZE=400  # Ignoreres, bruger fast 400-ord chunks
```

**Karakteristika:**
- Fast 400-ord chunks med 50-ord overlap
- Ignorerer CHUNK_SIZE parameter
- Ingen titel prefiks
- Bedst til: Lange dokumenter med kontekst behov

### Embedding Providers

#### Ollama (Lokale Embeddings)
```bash
# Fordele
+ Ingen API omkostninger
+ Data forbliver lokalt
+ God performance
+ Offline kapabilitet

# Ulemper
- Kræver mere RAM (8GB+)
- Længere opstartstid
- Mindre embedding space
```

#### OpenAI (Cloud Embeddings)
```bash
# Fordele
+ Høj embedding kvalitet
+ Stor embedding space
+ Hurtig opstart
+ Ingen local resource krav

# Ulemper
- API omkostninger
- Kræver internet forbindelse
- Data sendes til OpenAI
```

## 📁 **Filstruktur og Output**

### Input Filer
```
src/
├── mine_boeger.txt          # Din bog liste
├── .env                     # Konfiguration
└── scripts/
    └── process_books.sh     # Hovedscript
```

### Output Struktur
```
output/
├── processing_status.json   # Real-time status
├── processed_books.log     # Detaljeret log
└── completion_report.txt   # Afslutningsrapport

failed/
├── failed_books.json       # Fejlede bøger til retry
└── error_details.log      # Fejl detaljer
```

## 🐛 **Fejlfinding**

### Almindelige Problemer

#### "File not found" Fejl
```bash
# Problem: Bog liste ikke fundet
# Løsning: Tjek fil sti og eksistens
ls -la mine_boeger.txt
./scripts/process_books.sh --file $(pwd)/mine_boeger.txt
```

#### Database Forbindelse Fejl
```bash
# Problem: Kan ikke forbinde til database
# Løsning: Start database service
cd soegemaskine
docker-compose up -d postgres

# Verificér database
docker ps | grep postgres
```

#### Embedding Provider Fejl
```bash
# Problem: Ollama ikke tilgængelig
# Løsning: Start Ollama og installer model
cd soegemaskine
docker-compose --profile embeddings up -d ollama
../scripts/setup_ollama.sh

# Problem: OpenAI API fejl
# Løsning: Verificér API nøgle i .env
grep OPENAI_API_KEY .env
```

#### Memory/Performance Problemer
```bash
# Problem: Container killed (OOM)
# Løsning: Øg Docker memory limit eller reducer batch størrelse

# Midlertidig løsning: Reducér CHUNK_SIZE
CHUNK_SIZE=300

# Permanent løsning: Øg Docker memory til 8GB+
```

### Debug Mode
```bash
# Kør med detaljeret logging
LOG_LEVEL=DEBUG ./scripts/process_books.sh --file mine_boeger.txt

# Tjek container logs
docker logs soegemaskine-book-processor-1
```

## 📈 **Performance Optimering**

### Batch Størrelse
```bash
# For store filer (>10MB hver)
CHUNK_SIZE=300

# For mange små filer
CHUNK_SIZE=600

# Memory-constrained systems
CHUNK_SIZE=200
```

### Concurrent Processing
Systemet bruger automatisk 5 samtidige downloads. For at justere:

```bash
# Redigér book_processor_wrapper.py
semaphore = asyncio.Semaphore(3)  # Reducér til 3 for langsommere systemer
```

### Provider Optimering

#### Ollama Performance
```bash
# Forvarm model
docker exec soegemaskine-ollama-1 ollama run nomic-embed-text "test"

# Tjek model status
curl http://localhost:11434/api/tags
```

#### OpenAI Rate Limits
OpenAI har automatisk rate limiting. Ved fejl, vent og prøv igen.

## 📋 **Best Practices**

### Før Processering
1. **Validér altid konfiguration** først
2. **Test med små bog lister** (1-3 bøger)
3. **Verificér database space** for store collections
4. **Backup eksisterende data** hvis relevant

### Under Processering
1. **Overvåg fremgang** regelmæssigt
2. **Tjek log filer** for warnings
3. **Monitorér system ressourcer** (RAM, CPU)
4. **Vær tålmodig** - store bøger tager tid

### Efter Processering
1. **Gennemgå fejlede bøger** og find årsager
2. **Verificér data kvalitet** via søgninger
3. **Backup processed data** for sikkerhed
4. **Dokumentér processering noter** for teamet

## 🔄 **Batch Processing Workflow**

### Store Samlinger (100+ bøger)
```bash
# 1. Split bog liste i mindre batches
split -l 20 alle_boeger.txt batch_

# 2. Processér batch for batch
for batch in batch_*; do
  echo "Processing $batch..."
  ./scripts/process_books.sh --file $batch
  echo "Waiting 5 minutes before next batch..."
  sleep 300
done

# 3. Saml resultater
cat output/processing_status_*.json > samlet_status.json
```

### Kontinuerlig Overvågning
```bash
# Background monitoring
while true; do
  ./scripts/process_books.sh --monitor
  sleep 60
done
```

---

**Næste skridt:** Se [Konfigurationsguide](../KONFIGURATION.md) for avancerede indstillinger eller [Lokal Udvikling](LOKAL_UDVIKLING.md) for debugging teknikker.
