Titel: Konfigurationsreference
Oprettet: 2025-10-07 12:46
Sidst ændret: 2025-10-07 12:46
Ejerskab: DevOps / Drift

# Formål
Samlet reference for miljøvariabler og `.env` håndtering på tværs af systemets subsystemer. Dokumentet afløser de tidligere filer `documentation/KONFIGURATION.md` og `documentation/REFERENCER/ENV_KONFIGURATION.md`.

# Grundprincipper
- Hvert subsystem bruger sin egen `.env` (bogproces, søge-API, test-GUI). Del aldrig filer mellem dem.
- Produktionshemmeligheder må aldrig versioneres; brug lokale kopier og sikre transportkanaler.
- Valider alle ændringer med `scripts/validate_env.py` før opstart eller deployment.
- Tests skal mocke `load_dotenv()` og anvende `patch.dict(..., clear=True)` for total isolation.

# Filstruktur
```
.env.template                 # Samlet skabelon med inline valgmuligheder
env/
  local.env                   # Lokal (Mac) standardprofil
  test.env                    # Test/CI (dummy provider)
  production.env              # Produktion (OpenAI eller Ollama)
soegemaskine/.env             # Aktiv fil til search stack (kopi af relevant env)
create_embeddings/.env        # Kun hvis pipeline køres uden Docker (sjældent)
```

# Variabeloversigt
| Nøgle | Beskrivelse | Påkrævet | Bemærkninger |
|-------|-------------|----------|--------------|
| `ENVIRONMENT` | Miljølabel (`local`, `test`, `production`) | Ja | Brugt af validator + logging |
| `POSTGRES_HOST` | Databasehost | Ja | `postgres` inde i compose, `localhost` fra værten |
| `POSTGRES_PORT` | Databaseport | Ja | 5432 inde i compose; 5433 er default host-port i `docker-compose.base.yml` |
| `POSTGRES_DB` | Databaseskema | Ja | Fx `dhodb` |
| `POSTGRES_USER` | DB-bruger | Ja | Matcher database-image |
| `POSTGRES_PASSWORD` | DB-adgangskode | Ja | Brug stærke, roterede værdier |
| `DATABASE_URL` | Samlet URL | Nej (men anbefalet) | `postgresql://user:pass@host:port/db` |
| `PROVIDER` | Embedding provider | Ja | `openai`, `ollama`, `dummy` |
| `OPENAI_API_KEY` | OpenAI nøgle | Hvis `PROVIDER=openai` | Skjul i logfiler |
| `OPENAI_MODEL` | OpenAI modelnavn | Nej | Standard `text-embedding-3-small` |
| `OLLAMA_BASE_URL` | Ollama endpoint | Hvis `PROVIDER=ollama` | Typisk `http://ollama:11434` |
| `OLLAMA_MODEL` | Ollama model | Hvis `PROVIDER=ollama` | Fx `nomic-embed-text` |
| `CHUNKING_STRATEGY` | Chunking-valg | Ja | `sentence_splitter` eller `word_overlap` |
| `CHUNK_SIZE` | Maks tokens/ord | Ja | Tal \> 0; respekteres af strategierne |
| `TILLADTE_KALDERE` | CORS origins | Nej | Kommasepareret liste |
| `DISTANCE_THRESHOLD` | Similarity cutoff | Nej | Standard `0.5` |
| `LOG_LEVEL` | Logging-niveau | Nej | `DEBUG`, `INFO`, ... |
| `LOG_FORMAT` | Log-format | Nej | `plain` eller `json` |

# Inline eksempler (uddelt i `.env` filer)
```
# Database (vælg én af kommentarerne efter behov)
POSTGRES_HOST=postgres        # Når search stack køres i Docker
# POSTGRES_HOST=localhost     # Når scripts/process_books.sh kører mod lokal DB udenfor Docker
POSTGRES_PORT=5432            # Container-port (bruges af services inde i compose)
# POSTGRES_PORT=5433          # Typisk host-port i udvikling (se docker-compose.base.yml)

# Embeddings (vælg én sektion)
PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=text-embedding-3-small
# PROVIDER=ollama
# OLLAMA_BASE_URL=http://ollama:11434
# OLLAMA_MODEL=nomic-embed-text
# PROVIDER=dummy               # Bruges i test.env / CI

# Chunking
CHUNKING_STRATEGY=sentence_splitter
# CHUNKING_STRATEGY=word_overlap
CHUNK_SIZE=500

# Søgning
TILLADTE_KALDERE=http://localhost:3000,http://localhost:8080
DISTANCE_THRESHOLD=0.5
```

# Validering
Kør validatoren for at fange fejl før runtime:
```bash
python scripts/validate_env.py --file env/local.env
python scripts/validate_env.py --file env/production.env --strict
```
- `--strict` eskalerer advarsler til fejl, hvilket anbefales før produktion.
- Hvis du bruger root `.env`, vil validatoren antage `ENVIRONMENT=local`, men målet er at fastholde miljøfiler i `env/`.

# Samspil med central konfiguration
`config/config_loader.py` indlæser miljøvariablerne og eksponerer et `AppConfig` objekt. Nye variabler skal tilføjes dér, hvis de skal bruges i koden. Metoderne `get_config()` og `refresh_config()` sørger for caching og reload i runtime (bruges bl.a. af admin-endpoints i `soegemaskine/searchapi/dhosearch.py`).

# Sikkerhed og best practices
- Produktionsfiler skal have rettigheder `600` og ejes af deployment-brugeren.
- Brug `scp` eller secret management til at distribuere `production.env`.
- Trim ubrugte provider-variabler for klarhed (validatoren giver warnings for mismatch).
- Dokumentér nøgleændringer i deployment-noter/changes log.

# Relaterede dokumenter
- `documentation/GUIDES/LOCAL_SETUP.md`
- `documentation/GUIDES/PRODUCTION_DEPLOY.md`
- `scripts/validate_env.py` (kildekode og ekstra flags)
- `config/config_loader.py`
