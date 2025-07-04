# DHO Semantisk Søgemaskine System

## Oversigt

DHO Semantisk Søgemaskine er et komplet system til processering og søgning i historiske dokumenter med moderne AI-teknologier. Systemet understøtter lokale og cloud-baserede embedding modeller samt avancerede chunking strategier for optimal søgeperformance.

## 🚀 **Hurtig Start**

### Forudsætninger
- Docker og Docker Compose installeret
- Mindst 8GB RAM tilgængelig
- Git for kodebase adgang

### Installation
```bash
# Hent kodebase
git clone [repository-url]
cd SlægtBib/src

# Kopiér og konfigurér miljøvariabler
cp .env.template .env
# Redigér .env efter dine behov

# Start system
./scripts/process_books.sh --validate
```

## 📚 **Dokumentation**

### Brugerguider
- **[Installation Guide](BRUGERGUIDER/INSTALLATION.md)** - Komplet installationsvejledning med container management
- **[Bog Processering](BRUGERGUIDER/BOG_PROCESSERING.md)** - Processering af bøger og container rebuilding
- **[Bog Processering](BRUGERGUIDER/BOG_PROCESSERING.md)** - Guide til at tilføje bøger til systemet
- **[Lokal Udvikling](BRUGERGUIDER/LOKAL_UDVIKLING.md)** - Udvikling og testing guide

### Teknisk Dokumentation
- **[System Arkitektur](TEKNISK/ARKITEKTUR.md)** - Teknisk systemoversigt
- **[Konfiguration](KONFIGURATION.md)** - Komplet konfigurationsreference
- **[Konfigurationseksempler](EKSEMPLER/)** - Komplette .env eksempler for forskellige scenarier
- **[Chunking Strategier](TEKNISK/CHUNKING_STRATEGIER.md)** - Guide til tekst chunking
- **[API Reference](TEKNISK/API_REFERENCE.md)** - API dokumentation

## 🔧 **Hovedkomponenter**

### Database Layer
- **Pluggable arkitektur**: Understøtter flere database typer
- **PostgreSQL implementation**: Fuldt implementeret og testet
- **Dependency injection**: Nem udskiftning af database providers

### Embedding Providers
- **OpenAI**: Cloud-baserede embeddings med høj kvalitet
- **Ollama**: Lokale embeddings uden API omkostninger
- **Dummy**: Test provider til udvikling

### Chunking Strategier
- **Sentence Splitter**: Opdeler efter sætninger med titel prefiks
- **Word Overlap**: Fast chunk størrelse med overlap for kontekst

### Søgemaskine
- **Flask-baseret API**: RESTful søge interface
- **Vector søgning**: Semantisk søgning i embedding space
- **Filtrering**: Avancerede søgefiltre og sortering

## 🛠 **Centrale Scripts**

### Python Scripts
- `opret_bøger.py` - Kerne bog processering funktionalitet
- `book_processor_wrapper.py` - Brugervenligt wrapper med monitoring

### Bash Scripts
- `process_books.sh` - Hovedscript til bog processering
- `setup_ollama.sh` - Opsætning af lokale embeddings

## 📊 **Systemstatus**

| Komponent | Status | Beskrivelse |
|-----------|--------|-------------|
| Database Layer | ✅ Komplet | Pluggable PostgreSQL implementation |
| Embedding Providers | ✅ Komplet | OpenAI, Ollama, Dummy providers |
| Chunking Strategier | ✅ Komplet | Multiple strategies implementeret |
| Konfigurationshåndtering | ✅ Komplet | Unified template og validering |
| Dokumentation | ✅ Komplet | Struktureret dansk dokumentation |
| Test Suite | ✅ Komplet | Omfattende unit og integration tests |

## 🔗 **Eksterne Afhængigheder**

- **Docker & Docker Compose**: Container orkestrering
- **PostgreSQL**: Database motor
- **Ollama**: Lokal embedding server (valgfri)
- **OpenAI API**: Cloud embeddings (valgfri)

## 📝 **Bidrag og Udvikling**

Se [Lokal Udvikling](BRUGERGUIDER/LOKAL_UDVIKLING.md) for information om:
- Development environment setup
- Test kørsler
- Code contribution guidelines
- Debugging guides

## 📞 **Support**

For spørgsmål og support:
1. Tjek denne dokumentation først
2. Se [troubelshooting guide](BRUGERGUIDER/LOKAL_UDVIKLING.md#fejlfinding)
3. Kontakt development team

---

**Version**: 2025.1  
**Sidst opdateret**: Juni 2025  
**Sprog**: Dansk
