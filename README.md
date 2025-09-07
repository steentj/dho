# Semantisk Søgning (Slægtsbiblioteket) – Oversigt

Kort projektbeskrivelse: Systemet muliggør semantisk søgning i danske historiske PDF-kilder via embeddings i PostgreSQL (pgvector). To hoveddele: batch bogprocessering (indtager, chunker, embedder) og transaktionel søge-API (FastAPI) med valgfri embedding provider (OpenAI, Ollama, dummy til tests).

## Kodeoversigt
- `create_embeddings/` – Bogprocessering pipeline & orkestrering
- `soegemaskine/` – Søge-API (FastAPI) + konfigurationssystem
- `api_testgui/` – Lokal Streamlit testklient
- `database/` – DB services og repositories
- `config/` – Central konfiguration (Stage 9+10)
- `documentation/` – Struktureret dokumentationssæt (CORE, REFERENCER, ARKIV)

## Hurtig Kom-i-Gang
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r create_embeddings/requirements.txt
docker compose up --build
```

## Centrale Dokumenter
Se fuldt indeks i `documentation/INDEX.md`.

| Dokument | Formål |
|----------|-------|
| 01_ARKITEKTUR | Systemoverblik |
| 02_UDVIKLERGUIDE | Arbejdsgange & tests |
| 03_DEPLOYMENT | Udrulning lokal/produktion |
| 04_BOG_PROCESSERING | Tilføjelse af nye bøger |
| 05_SOEGE_API_GUIDE | Brug af søge-API |
| ENV_KONFIGURATION | Miljøvariabler & .env strategi |
| PROVIDER_OVERSIGT | Embedding / chunking / DB providers |
| CHUNKING_STRATEGIER | Strategidetaljer |
| ARKIV_INDEX | Historiske rapporter |

## Nøgleprincipper
- Dependency Injection & udskiftelige providers
- Testisolering med mock af `load_dotenv` + `patch.dict(clear=True)`
- Fail-fast i udvikling, robust batchkørsel (fortsætter ved enkelte fejl)

## Licens & Bidrag
Internt projekt (ingen offentlig licens defineret). Bidrag gennem Pull Requests med opdateret dokumentation hvor relevant.

## Support
Se `02_UDVIKLERGUIDE` og `03_DEPLOYMENT` for fejlfinding. Arkivrapporter findes i `documentation/ARKIV/`.

