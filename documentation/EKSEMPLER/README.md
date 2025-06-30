# Konfigurationseksempler

Dette directory indeholder komplette `.env` eksempler for forskellige scenarier og use cases.

## 📁 **Tilgængelige Eksempler**

### **Grundlæggende Setup**
- **[.env.lokalt.eksempel](.env.lokalt.eksempel)** - Lokal udvikling med Ollama
- **[.env.produktion.eksempel](.env.produktion.eksempel)** - Produktion med OpenAI
- **[.env.test.eksempel](.env.test.eksempel)** - Testing med dummy provider

### **Avancerede Konfigurationer**
- **[.env.performance.eksempel](.env.performance.eksempel)** - Performance-optimeret setup
- **[.env.sikkerhed.eksempel](.env.sikkerhed.eksempel)** - Sikkerhedsfokuseret konfiguration
- **[.env.debugging.eksempel](.env.debugging.eksempel)** - Debug og udviklings setup

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
| Lokalt | Ollama | sentence_splitter | Udvikling, ingen API omkostninger |
| Produktion | OpenAI | word_overlap | Production med høj kvalitet |
| Test | Dummy | sentence_splitter | Automatiserede tests |
| Performance | Ollama | word_overlap | Høj gennemstrømning |
| Sikkerhed | OpenAI | sentence_splitter | Sikker produktion |
| Debugging | Dummy | sentence_splitter | Fejlsøgning og udvikling |

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

- **[Konfigurationsguide](../KONFIGURATION.md)** - Detaljeret forklaring af alle variabler
- **[Installation Guide](../BRUGERGUIDER/INSTALLATION.md)** - Setup instruktioner
- **[Chunking Strategier](../TEKNISK/CHUNKING_STRATEGIER.md)** - Guide til chunking valg
