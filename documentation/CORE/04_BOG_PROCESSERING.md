docker-compose --profile embeddings run --rm book-processor --input-file example_books.txt
docker logs dho-book-processor
Titel: Bogprocessering Guide
Version: v1.1
Oprettet: 2025-09-04
Sidst ændret: 2025-10-07
Ejerskab: Data Pipeline Ansvarlig
Formål: Beskrive den driftsmæssige proces for at indlæse bøger i databasen via pipeline og scripts.

# 1. Overblik
Pipeline-forløbet består af fire trin:
1. Indlæsning af PDF via URL (download & ekstraktion)
2. Chunking efter valgt strategi
3. Embedding-generation via provider
4. Persistens i PostgreSQL (chunks + vektorer)

Workflowen køres via Docker-containeren `book-processor` og orkestreres af `scripts/process_books.sh`.

# 2. Forudsætninger
- Search stack kører allerede (`make -C soegemaskine up-local` eller `up-prod`)
- `soegemaskine/.env` peger på den ønskede database + provider
- Inputfil med én URL til en PDF pr. linje
- Scriptet eksekveres på værten hvor Docker kører (lokal Mac eller via SSH på produktion)

# 3. Nøgleværktøjer
| Element | Formål |
|---------|--------|
| `scripts/process_books.sh` | Kontrolskript for validering, kørsel, monitorering og genkørsler |
| `create_embeddings/book_processor_wrapper.py` | Containermodul der udfører selve pipeline arbejdet |
| `soegemaskine/docker-compose.embeddings.yml` | Definerer book-processor og Ollama services |
| `scripts/setup_ollama.sh` | Trækker embedding-modellen i Ollama-containeren |

# 4. Standardprocedure
```bash
# 1) Validér at miljøet er korrekt
./scripts/process_books.sh --validate

# 2) Kør batchen (erstatt filnavn med din egen liste)
./scripts/process_books.sh --file batches/oktober.txt

# 3) Følg status undervejs
./scripts/process_books.sh --monitor

# 4) Genkør evt. fejlede bøger
./scripts/process_books.sh --retry-failed
```

- `--file` forventer en fil i værtsfilsystemet; scriptet kopierer den til `soegemaskine/book_input/`.
- `--monitor` viser konsolideret status (json + loguddrag).
- `--retry-failed` læser `book_failed/failed_books.json` og opretter en midlertidig kø.

# 5. Midlertidige overrides
| Flag | Funktion |
|------|----------|
| `--provider <navn>` | Forbigår PROVIDER i `.env` for den aktuelle kørsel (openai/ollama/dummy) |
| `--model <model>` | Sætter modelvariabel ift. valg (OPENAI_MODEL eller OLLAMA_MODEL) |
| `--validate` | Opretter mapper, sikrer rettigheder og kører containervalidering |
| `--monitor` | Viser status, seneste loglinjer og fejlede bøger |

Eksempel på override:
```bash
./scripts/process_books.sh --file batches/ollama.txt --provider ollama --model nomic-embed-text
```

# 6. Artefakter og logfiler
- Inputkopier: `soegemaskine/book_input/<filnavn>`
- Status: `soegemaskine/book_output/processing_status.json`
- Detaljerede logfiler: `soegemaskine/book_output/opret_bøger_<timestamp>.log`
- Fejloversigt: `soegemaskine/book_failed/failed_books.json`

Bevar relevante logfiler efter produktskørsler til audit og fejlanalyse.

# 7. Idempotens og databasen
- Pipeline springer automatisk bøger over, hvor embeddings allerede eksisterer for den aktive provider.
- Postgres tabeller følger navngivning efter provider (`chunks`, `chunks_nomic`, `chunks_dummy`).
- Kontrollér databasevolumen og backup rutiner før store batches.

# 8. Typiske fejl og afhjælpning
| Symptomer | Årsag | Handling |
|-----------|-------|----------|
| `DATABASE_URL` mangler | `.env` ikke kopieret/valid | `cp env/<miljø>.env soegemaskine/.env` og kør `--validate` |
| `Connect call failed` mod DB | Forkert host/port eller DB stoppet | Bekræft compose stack og port (5432 i containere, 5433 på værten) |
| Provider-timeout | OpenAI/Ollama utilgængelig | Tjek `docker compose logs -f dho-ollama` eller API-nøgle |
| `expected str, got list` | Defensiv fix skal logge konvertering | Undersøg logfil for bog og PDF-kvalitet |
| Ingen nye chunks | PDF download/ekstraktion fejlede | Se logfil for details, valider URL og tilgængelighed |

# 9. Best practices
- Kør små testbatcher (1-3 bøger) efter konfigurationsændringer.
- Planlæg store kørsler uden for spidsbelastning.
- Brug `--monitor` jævnligt og gem loguddrag.
- Fjern forældede filer fra `book_input/` og `book_failed/` for at holde strukturen ren.

# 10. Relaterede dokumenter
- `documentation/GUIDES/BOOK_UPDATES.md`
- `documentation/CORE/03_DEPLOYMENT.md`
- `documentation/REFERENCE/KONFIGURATION.md`
- `documentation/TEKNISK/CHUNKING_STRATEGIER.md`
