Titel: Miljøkonfiguration (.env)
Version: v1.0
Oprettet: 2025-09-04
Sidst ændret: 2025-09-04
Ejerskab: DevOps / Drift
Formål: Ensartet håndtering af miljøvariabler på tværs af subsystemer

# 1. Principper
- Én `.env` pr. subsystem (ingen deling)
- Ingen hemmeligheder i versioneret kode
- `.env.template` angiver fuld liste
- Tests isoleres via patch.dict(..., clear=True)

# 2. Subsystem Filer
| Subsystem | Placering | Skabelon |
|-----------|-----------|----------|
| Bogprocessering | create_embeddings/.env | create_embeddings/.env.template |
| Søgning API | soegemaskine/.env | soegemaskine/.env.template |
| Test GUI | api_testgui/.env | api_testgui/.env.template |

# 3. Variabelmatrix (eksempel)
| Variabel | Beskrivelse | Påkrævet | Eksempel |
|----------|-------------|----------|----------|
| EMBEDDING_PROVIDER | Valgt embedding backend | Ja | openai |
| OPENAI_API_KEY | OpenAI nøgle | Hvis provider=openai | sk-*** |
| OLLAMA_BASE_URL | Lokal Ollama endpoint | Hvis provider=ollama | http://localhost:11434 |
| DB_HOST | DB host | Ja | localhost |
| DB_PORT | DB port | Ja | 5432 |
| DB_NAME | Databasenavn | Ja | dho |
| DB_USER | DB bruger | Ja | dho_user |
| DB_PASSWORD | DB password | Ja | ******** |
| CHUNK_STRATEGY | Chunking strategi | Ja | sentence_splitter |
| LOG_LEVEL | Logging niveau | Nej | INFO |
| API_PORT | Lytteport for søge-API | Ja (API) | 8000 |
| ALLOWED_ORIGINS | CORS origins | Nej | * |

# 4. Skabeloneksempel
```
EMBEDDING_PROVIDER=ollama
OPENAI_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434
DB_HOST=localhost
DB_PORT=5432
DB_NAME=dho
DB_USER=dho_user
DB_PASSWORD=CHANGE_ME
CHUNK_STRATEGY=sentence_splitter
LOG_LEVEL=INFO
API_PORT=8000
ALLOWED_ORIGINS=*
```

# 5. Indlæsning i Kode
- Brug `dotenv.load_dotenv()` i runtime.
- I tests: mock `load_dotenv` og injicér miljø direkte.

# 6. Sikkerhed
- Prod `.env` rettigheder: `chmod 600`
- Roter hemmeligheder kvartalsvis
- Aldrig logge nøgler – kun navne

# 7. Fejlfinding
| Problem | Årsag | Løsning |
|---------|-------|---------|
| Tomme embeddings | Forkert provider / nøgle | Tjek ENV vars |
| DB connection error | Forkert host/port | Verificér netværk |
| CORS fejl | ALLOWED_ORIGINS mangler | Tilføj domæne |

# 8. Referencer
- Udviklerguide (miljøhåndtering)
- Deployment (prod håndtering)
