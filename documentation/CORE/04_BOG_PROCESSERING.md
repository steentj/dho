Titel: Bogprocessering Guide
Version: v1.0
Oprettet: 2025-09-04
Sidst ændret: 2025-09-04
Ejerskab: Data Pipeline Ansvarlig
Formål: Vise hvordan nye bøger tilføjes og embeddings genereres

# 1. Formål
Instruktion i at køre pipeline for nye bøger.

# 2. Pipeline Oversigt
1. Input PDF → tekstudtræk
2. Chunking (strategi valgt)
3. Embedding generation
4. Persistens i PostgreSQL (chunks + vektorer)

# 3. Krævede Input
| Type | Beskrivelse | Eksempel |
|------|-------------|----------|
| PDF | Original kildefil | `pdf/krønike.pdf` |
| Batch fil | Liste over URL'er / lokationer | `example_books.txt` |
| Strategi | `sentence_splitter` eller `word_overlap` | miljøvariabel |

# 4. Scripts i `scripts/`
| Script | Funktion |
|--------|----------|
| `process_books.sh` | Hovedscript til bog-processering. Håndterer input filer, processeringsvalidering, overvågning, og genkørsler. Bruges via kommandolinjen med forskellige flags (`--file`, `--retry-failed`, `--monitor`, `--validate`, `--provider`, `--model`). |
| `setup_ollama.sh` | Opsætter Ollama containeren med den korrekte embedding model (`nomic-embed-text`). Skal køres efter Docker containere er startet hvis Ollama anvendes som embedding provider. |
| `validate_env.py` | Validerer konfigurationsvariabler i `.env` filer. Bruges af `process_books.sh --validate` men kan også køres selvstændigt. Verificerer korrekt opsætning af environment variabler for providers og database. |
| `run_shadow_search.sh` | Starter en sekundær søge-API (på port 18000) med mulighed for at bruge en anden embedding provider/model for sammenligning af søgeresultater. Nyttigt til at teste forskellige modeller eller providere uden at påvirke hovedinstansen. |
| `compare_search_results.py` | Sammenligner søgeresultater mellem hoved-API og shadow-API ved at køre prædefinerede søgninger og beregne overlap og Jaccard-score. Hjælper med at vurdere effekten af forskellige modeller/providere. |
| `replace_chunks_nomic_table.py` | Værktøj til at erstatte indholdet af `chunks_nomic` tabellen med data fra en SQL dump fil. Bruges til at gendanne eller opdatere embedding data. |
| `test_ollama_setup.py` | Tester Ollama-konfiguration og -funktionalitet ved at verificere service sundhed, modelhentning og test af embedding-generering. |

# 5. Valg af Providers
- Embedding: set `EMBEDDING_PROVIDER` (openai/ollama/dummy)
- Chunking: set `CHUNK_STRATEGY`

# 6. Kørselseksempel

### Anbefalet Workflow via Scripts
```bash
# 1. Validér konfiguration før kørsel
./scripts/process_books.sh --validate

# 2. Processér bøger fra fil
./scripts/process_books.sh --file example_books.txt

# 3. Overvåg fremgang
./scripts/process_books.sh --monitor

# 4. Genprøv fejlede bøger
./scripts/process_books.sh --retry-failed
```

### Med Provider/Model Overriding
```bash
# Brug specifik provider kun for denne kørsel
./scripts/process_books.sh --file example_books.txt --provider openai

# Brug specifik model
./scripts/process_books.sh --file example_books.txt --model text-embedding-3-large

# Midlertidig skift til lokal Ollama med specifik model
./scripts/process_books.sh --file example_books.txt --provider ollama --model nomic-embed-text
```

### Alternativ Direkte Kørsel (Avanceret)
```bash
# Aktivér miljø
source .venv/bin/activate

# Direkte kørsel via Python modul
python -m create_embeddings.book_processor_wrapper --input example_books.txt
```

### Via Docker Compose (Avanceret)
```bash
# Kør via Docker Compose
cd soegemaskine
docker-compose --profile embeddings run --rm book-processor --input-file example_books.txt
```

# 7. Overvågning

### Real-time Monitoring
```bash
# Se aktuel status og seneste logs
./scripts/process_books.sh --monitor
```

### Log Filer
- Log filer gemmes i `soegemaskine/book_output/opret_bøger_*.log` med tidsstempel
- Tjek seneste log:
```bash
tail -100 soegemaskine/book_output/opret_bøger_*.log | less
```

### Status Filer
- Processing status: `soegemaskine/book_output/processing_status.json`
- Fejlede bøger: `soegemaskine/book_failed/failed_books.json`

### Container Logs
```bash
# Se Docker container logs
docker logs dho-book-processor
```

# 8. Genkørsel & Idempotens
Systemet springer embeddings over hvis de allerede findes (provider + bog-ID).

# 9. Fejlfinding
| Problem | Årsag | Løsning |
|---------|-------|---------|
| "expected str, got list" | chunk_text var liste | Defensiv fix aktiv – check log |
| Manglende OpenAI key | ENV ikke sat | Tilføj i `.env` |
| Ingen chunks genereret | PDF extraction fejlede | Kontroller filsti / format |
| Connection failed (port) | DB port mismatch | Kontroller POSTGRES_PORT i `.env` matcher faktisk port |
| Ollama model ikke fundet | Model ikke installeret | Kør `./scripts/setup_ollama.sh` |
| Validering fejler | ENV konfig inkomplet | Kør `python scripts/validate_env.py` for detaljeret fejlinfo |
| Container starter ikke | Docker config problem | Tjek `docker-compose ps` og `docker logs` |
| Fejlede bøger | Timeout/format/access | Se detaljer med `cat book_failed/failed_books.json` |
| "No module named..." | Manglende dependency | Kontroller container rebuild efter ændringer |

# 10. Performance Tips
- Brug lokal Ollama for hurtig iteration
- Batch større bøger uden at blande meget små (stabil throughput)

# 11. Referencer
- CHUNKING_STRATEGIER
- PROVIDER_OVERSIGT
- ENV_KONFIGURATION
