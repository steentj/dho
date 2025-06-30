# Konfigurationsguide

## Oversigt

Dette dokument beskriver alle konfigurationsmuligheder for DHO Semantisk Søgemaskine systemet. Alle konfigurationer håndteres via miljøvariabler defineret i `.env` filen.

## 🔧 **Grundlæggende Opsætning**

### Kopiér Template
```bash
cp .env.template .env
```

### Redigér Konfiguration
Åbn `.env` filen i din foretrukne editor og konfigurér variablerne efter dine behov.

## 📋 **Konfigurationsvariabler**

### 🗄️ **Database Konfiguration**

#### Påkrævede Variabler
```bash
POSTGRES_HOST=postgres                    # Docker service navn eller localhost
POSTGRES_USER=postgres                    # Database brugernavn
POSTGRES_PASSWORD=your_secure_password    # Sikkert database password
POSTGRES_PORT=5432                        # Database port (standard: 5432)
POSTGRES_DB=dhodb                         # Database navn
```

**Vigtige noter:**
- Brug `postgres` som host i Docker miljø
- Brug `localhost` for lokal udvikling
- Password bør være stærkt og unikt

### 🤖 **Embedding Provider Konfiguration**

#### Provider Valg
```bash
PROVIDER=ollama                           # Valg: openai, ollama, dummy
```

#### OpenAI Konfiguration (påkrævet hvis PROVIDER=openai)
```bash
OPENAI_API_KEY=your_openai_api_key        # Din OpenAI API nøgle
OPENAI_MODEL=text-embedding-3-small       # Valgfri: OpenAI model
```

**Tilgængelige OpenAI modeller:**
- `text-embedding-3-small` (anbefalet - billig og hurtig)
- `text-embedding-3-large` (højere kvalitet, dyrere)
- `text-embedding-ada-002` (ældre model)

#### Ollama Konfiguration (påkrævet hvis PROVIDER=ollama)
```bash
OLLAMA_BASE_URL=http://ollama:11434       # Ollama server URL
OLLAMA_MODEL=nomic-embed-text             # Ollama embedding model
```

**Tilgængelige Ollama modeller:**
- `nomic-embed-text` (anbefalet - god balance)
- `all-minilm` (mindre, hurtigere)

#### Dummy Provider (til testing)
Ingen yderligere konfiguration påkrævet. Genererer tilfældige embeddings til test formål.

### ✂️ **Tekst Processering Konfiguration**

#### Chunk Størrelse
```bash
CHUNK_SIZE=500                            # Maksimum antal tokens per chunk
```

**Anbefalede værdier:**
- `300-500`: Standard for de fleste dokumenter
- `200-300`: For korte dokumenter eller hurtig processering
- `500-1000`: For lange dokumenter der kræver mere kontekst

#### Chunking Strategi
```bash
CHUNKING_STRATEGY=sentence_splitter       # Valg: sentence_splitter, word_overlap
```

**Chunking Strategier:**

##### `sentence_splitter` (Standard)
- **Funktion**: Opdeler tekst efter sætninger
- **Fordele**: Respekterer naturlige sproggrænser, tilføjer titel til chunks
- **Bedst til**: Generel tekst processering, søgekvalitet prioriteret
- **Max tokens**: Respekterer `CHUNK_SIZE` parameter

##### `word_overlap`
- **Funktion**: Fast 400-ord chunks med 50-ord overlap
- **Fordele**: Konsistent chunk størrelse, bevarer kontekst mellem chunks
- **Bedst til**: Lange dokumenter, når overlap er vigtigt
- **Max tokens**: Ignorerer `CHUNK_SIZE`, bruger fast størrelse

### 📁 **Processering Konfiguration**

```bash
URL_FILE=test_input.txt                   # Input fil til batch bog processering
LOG_DIR=./logs                            # Directory til log filer
```

### 🔍 **Søgemaskine API Konfiguration**

#### CORS og Adgang
```bash
TILLADTE_KALDERE=http://localhost:3000,http://127.0.0.1:3000,http://localhost:8080
```

**Format**: Kommasepareret liste af tilladte origins

#### Søgekvalitet
```bash
DISTANCE_THRESHOLD=0.5                    # Minimum similarity score for resultater
```

**Værdier:**
- `0.0-0.3`: Meget brede søgeresultater
- `0.4-0.6`: Balancerede resultater (anbefalet)
- `0.7-1.0`: Meget specifikke resultater

### 📝 **Logging Konfiguration**

```bash
LOG_LEVEL=INFO                           # Valg: DEBUG, INFO, WARNING, ERROR
```

**Log niveauer:**
- `DEBUG`: Detaljeret debugging information
- `INFO`: Generel procesflow (anbefalet)
- `WARNING`: Kun advarsler og fejl
- `ERROR`: Kun fejl

## 🚀 **Eksempel Konfigurationer**

### Lokal Udvikling med Ollama
```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=dev123
POSTGRES_DB=dhodb_dev

# Embeddings
PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=nomic-embed-text

# Processing
CHUNKING_STRATEGY=sentence_splitter
CHUNK_SIZE=500
LOG_LEVEL=DEBUG
```

### Produktion med OpenAI
```bash
# Database
POSTGRES_HOST=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=super_secure_password_123
POSTGRES_DB=dhodb

# Embeddings
PROVIDER=openai
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
OPENAI_MODEL=text-embedding-3-small

# Processing
CHUNKING_STRATEGY=word_overlap
CHUNK_SIZE=400
LOG_LEVEL=INFO
```

### Testing med Dummy Provider
```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_USER=test
POSTGRES_PASSWORD=test
POSTGRES_DB=test_db

# Embeddings
PROVIDER=dummy

# Processing
CHUNKING_STRATEGY=sentence_splitter
CHUNK_SIZE=300
LOG_LEVEL=DEBUG
```

## ✅ **Konfigurationsvalidering**

### Validér Konfiguration
```bash
# Via script
./scripts/process_books.sh --validate

# Direkte via Python
python -c "from create_embeddings.book_processor_wrapper import validate_config; print(validate_config())"
```

### Cross-Validation Funktionalitet

Systemet udfører automatisk cross-validation for at sikre konsistens mellem `PROVIDER` indstilling og relaterede miljøvariabler:

#### Automatiske Advarsler
- **OpenAI variabler med ikke-OpenAI provider**: Advarer hvis `OPENAI_API_KEY` eller `OPENAI_MODEL` er sat, men `PROVIDER` ikke er `openai`
- **Ollama variabler med ikke-Ollama provider**: Advarer hvis `OLLAMA_BASE_URL` eller `OLLAMA_MODEL` er sat, men `PROVIDER` ikke er `ollama`
- **Provider variabler med dummy provider**: Foreslår at ændre provider hvis du har sat rigtige API konfigurationer

#### Eksempel på Cross-Validation Advarsler
```bash
# Konfiguration med Ollama provider men OpenAI API key
PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=nomic-embed-text
OPENAI_API_KEY=sk-proj-xxxxx  # ← Trigger advarsel

# Output:
WARNING: Cross-validation advarsel: OpenAI variabler ['OPENAI_API_KEY'] er sat, 
men PROVIDER=ollama. Disse variabler vil blive ignoreret.
```

### Almindelige Fejl

#### Manglende Provider Konfiguration
```
❌ Fejl: Manglende påkrævede miljøvariabler: ['OPENAI_API_KEY']
✅ Løsning: Tilføj OPENAI_API_KEY til .env fil
```

#### Ugyldig Chunking Strategi
```
❌ Fejl: Ugyldig CHUNKING_STRATEGY: invalid_strategy
✅ Løsning: Brug 'sentence_splitter' eller 'word_overlap'
```

#### Ugyldig Chunk Størrelse
```
❌ Fejl: CHUNK_SIZE skal være et positivt tal
✅ Løsning: Sæt CHUNK_SIZE til et tal mellem 100-2000
```

## 🔒 **Sikkerhed**

### API Nøgler
- Gem aldrig API nøgler i git repositories
- Brug miljøvariabler eller secrets management
- Roter API nøgler regelmæssigt

### Database Passwords
- Brug stærke, unikke passwords
- Undgå standard passwords som 'password' eller '123456'
- Overvej at bruge password managers

### CORS Konfiguration
- Begræns `TILLADTE_KALDERE` til kendte domæner
- Undgå wildcards (*) i produktion
- Test CORS konfiguration grundigt

## 🐛 **Fejlfinding**

### Debugging Steps
1. Validér konfiguration: `./scripts/process_books.sh --validate`
2. Tjek log filer i `LOG_DIR`
3. Verificér database forbindelse
4. Test embedding provider separat

### Almindelige Problemområder
- Database forbindelsesproblemer
- Netværksforbindelse til embedding providers
- Manglende eller forkerte miljøvariabler
- Port konflikter i Docker environment

---

**Se også:**
- [Installation Guide](BRUGERGUIDER/INSTALLATION.md)
- [Chunking Strategier](TEKNISK/CHUNKING_STRATEGIER.md)
- [Fejlfinding Guide](BRUGERGUIDER/LOKAL_UDVIKLING.md#fejlfinding)
