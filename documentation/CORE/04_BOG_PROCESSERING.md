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

# 4. Scripts i `scripts/` (udfyld ved behov)
| Script | Funktion |
|--------|----------|
| (TBD) | (Eksempel) |

# 5. Valg af Providers
- Embedding: set `EMBEDDING_PROVIDER` (openai/ollama/dummy)
- Chunking: set `CHUNK_STRATEGY`

# 6. Kørselseksempel
```
# Aktivér miljø
source .venv/bin/activate
# Kør bogprocessering (eksempel – tilpas til faktisk entrypoint)
python -m create_embeddings.book_processor_wrapper --input example_books.txt
```
Eller via Docker (eksempel):
```
docker compose run --rm processor python -m create_embeddings.book_processor_wrapper --input example_books.txt
```

# 7. Overvågning
- Se logfil i root (rotationsnavngivning)
- Advarsler om konvertering af chunk_text listes

# 8. Genkørsel & Idempotens
Systemet springer embeddings over hvis de allerede findes (provider + bog-ID).

# 9. Fejlfinding
| Problem | Årsag | Løsning |
|---------|-------|---------|
| "expected str, got list" | chunk_text var liste | Defensiv fix aktiv – check log |
| Manglende OpenAI key | ENV ikke sat | Tilføj i `.env` |
| Ingen chunks genereret | PDF extraction fejlede | Kontroller filsti / format |

# 10. Performance Tips
- Brug lokal Ollama for hurtig iteration
- Batch større bøger uden at blande meget små (stabil throughput)

# 11. Referencer
- CHUNKING_STRATEGIER
- PROVIDER_OVERSIGT
- ENV_KONFIGURATION
