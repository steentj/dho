Titel: Konfigurationseksempler
Oprettet: 2025-10-07 15:33
Sidst ændret: 2025-10-07 15:45

# Konfigurationseksempler

Dette directory indeholder komplette `.env` eksempler for forskellige scenarier og use cases.

## 📁 **Tilgængelige Eksempler**

### **Tilgængelige filer**
- **[.env.lokalt.eksempel](.env.lokalt.eksempel)** - Lokal udvikling med Ollama
- **[.env.produktion.eksempel](.env.produktion.eksempel)** - Produktion med OpenAI
- **[.env.test.eksempel](.env.test.eksempel)** - Testing med dummy provider

## 🚀 **Hurtig Start**

### Trin 1: Vælg Eksempel
Vælg det eksempel der passer bedst til dit use case:

```bash
# Lokal udvikling
cp documentation/EKSEMPLER/.env.lokalt.eksempel .env

# Produktion
cp documentation/EKSEMPLER/.env.produktion.eksempel .env

# Testing
cp documentation/EKSEMPLER/.env.test.eksempel .env
```

### Trin 2: Tilpas Konfiguration
Redigér `.env` filen og sæt dine specifikke værdier:

```bash
nano .env
```

### Trin 3: Validér Setup
```bash
./scripts/process_books.sh --validate
```

## 📋 **Eksempel Oversigt**

| Eksempel | Provider | Chunk Strategy | Use Case |
|----------|----------|----------------|----------|
| Lokalt | Ollama | word_overlap | Udvikling, ingen API omkostninger |
| Produktion | OpenAI | word_overlap | Produktion med høj kvalitet |
| Test | Dummy | sentence_splitter | Automatiserede tests |

## 🔧 **Tilpasning Guidelines**

### Database Konfiguration
Alle eksempler bruger PostgreSQL. Tilpas efter dit miljø:
- **Lokal**: `POSTGRES_HOST=localhost`
- **Docker**: `POSTGRES_HOST=postgres`
- **Remote**: `POSTGRES_HOST=your-db-server.com`

### API Nøgler
Husk at erstatte placeholder værdier:
- `your_openai_api_key` → Din rigtige OpenAI API nøgle
- `your_secure_password` → Stærkt database password

### Ports og URLs
Kontrollér at porte ikke konflikter med eksisterende services:
- PostgreSQL: Standard 5432
- Ollama: Standard 11434
- Søgemaskine API: Standard 8080

## 🔍 **Se Også**

- **[Konfigurationsguide](../REFERENCE/KONFIGURATION.md)** - Detaljeret forklaring af alle variabler
- **[Lokal opsætning](../GUIDES/LOCAL_SETUP.md)** - Setup instruktioner
- **[Chunking Strategier](../TEKNISK/CHUNKING_STRATEGIER.md)** - Guide til chunking valg
