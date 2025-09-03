# Drifts- & Miljøvejledning (Operations & Environments)

Oprettet: 2025-09-02  
Sidst Opdateret: 2025-09-03

## Formål
Én samlet, praktisk guide til at køre, vedligeholde og migrere mellem miljøer for SlægtBib semantisk søgesystem. Denne fil samler driftsrutiner, miljøskift, shadow-testing og provider-cutover.

## Miljøoversigt
| Miljø | Formål | Provider typisk | Log Format | Embeddings Tabel | Nøglekrav |
|-------|--------|-----------------|------------|------------------|-----------|
| local | Lokal udvikling / debugging | ollama / dummy | plain | `chunks_nomic` (ollama) eller `chunks` | Hurtig iteration, kan have begge tabeller |
| test  | CI / automatiske tests | dummy | plain | Ingen *krav* (syntetiske) | Ingen rigtige API-nøgler, determinisme |
| production | Brugertrafik | openai (eller ollama efter cutover) | json | `chunks` (openai) / `chunks_nomic` (ollama) | Sikkerhed, stabilitet |

## ENVIRONMENT Variablen
Alle miljøfiler (`env/*.env`) indeholder `ENVIRONMENT=`. Ved overgangsperioden accepteres manglende værdi i root `.env` som `local` (warning). Senere skal den gøres obligatorisk.

## Filstruktur for Miljøer
```
env/
  local.env
  test.env
  production.env
scripts/validate_env.py
```

## Skift af Miljø (manuel midlertidig metode)
Kopiér ønsket fil til `.env` i projektrod:
```
cp env/local.env .env
python scripts/validate_env.py
```
Fremtidig forbedring: `env_switch.sh` (kommende mulighed) til at undgå manuel kopi.

## Validering
```
python scripts/validate_env.py            # Validerer ./.env
python scripts/validate_env.py --file env/test.env --strict
make -C soegemaskine validate-env         # Make target (JSON output)
```
Fejl skal rettes før deploy. Warnings kan tolereres i local men ikke i production (brug `--strict`).

## Health & Readiness (Stage 8)
Endpoints (kører på port 8080 via searchapi container):
```
GET /healthz   # Liveness (ingen DB eller eksterne kald)
GET /readyz    # Readiness (DB + provider check)
```
Eksempel:
```
make -C soegemaskine health-check
```
`/readyz` strategi:
- dummy: altid OK
- openai: antages OK (undgår betalte micro-kald) => felt `assumed_provider_ready=true`
- ollama: lille embedding på "ping" med kort timeout (<=5s)

Statuskoder:
- 200 OK: { status: "ok" }
- 503 Service Unavailable: { status: "degraded" }

## Embedding Timeout & Retries
Nye miljøvariabler:
```
EMBEDDING_TIMEOUT=30          # Sekunder pr. kald
EMBEDDING_MAX_RETRIES=1       # Antal retry forsøg (ekskl. første)
EMBEDDING_RETRY_BACKOFF=0.5   # Grund-backoff i sekunder (eksponentiel)
```
Anvendelse:
- Ollama & OpenAI providers respekterer disse værdier.
- Retry kun på generelle fejl/undtagelser (forfining mulig i senere stage).

## Ressource Limits (Compose)
Tilføjet i `docker-compose.base.yml`:
```
postgres: limits memory 1g (reservation 256m)
searchapi: limits memory 512m (reservation 128m)
```
Formål: Forebyggende mod runaway memory. Justér ved tunings-behov.

## Docker Compose Layout (Modulært)
| Fil | Indhold |
|-----|---------|
| `docker-compose.base.yml` | postgres + searchapi |
| `docker-compose.embeddings.yml` | ollama + book-processor |
| `docker-compose.edge.yml` | nginx TLS layer |
| `docker-compose.shadow.yml` | shadow searchapi (port 18000) |

Typiske kommandoer:
```
make up-minimal            # Kun database + søgning
make up-minimal-clean      # Minimal + fjern orphans
make up-local              # Base + embeddings
make up-prod               # Base + embeddings + edge
make down-stacks           # Stop alle modulære services
```

## Book Processing med Provider Override
```
./scripts/process_books.sh --file mine_boeger.txt --provider ollama --model nomic-embed-text
```
Dette injicerer kun env-variabler i kørslen for book-processor og påvirker ikke kørende searchAPI.

## Shadow Search (Sammenligning / Cutover Forberedelse)
Start primary (fx `make up-prod` eller `make up-minimal`) og kør shadow:
```
make shadow-up-ollama         # Shadow på port 18000 med ollama
make shadow-up-openai         # Shadow med openai
make shadow-compare           # Generer JSON overlap rapport
make shadow-down              # Stop shadow
```
Eller script:
```
./scripts/run_shadow_search.sh --provider ollama --model nomic-embed-text --query "anden verdenskrig"
```
Rapport: `soegemaskine/shadow_comparison.json` + eventuelt ekstra filnavn angivet.

## Fortolkning af Sammenligningsrapport
Felter:
- `overlap_ratio`: Andel af fælles top-resultater i forhold til den mindste mængde.
- `jaccard`: |A ∩ B| / |A ∪ B| — robust overlapmål.
- `avg_jaccard` i summary: gennemsnit over alle forespørgsler.
Tommelfingerregel før cutover: `avg_jaccard >= 0.4` + manuel relevans verificeret.

## Cutover Procedure (OpenAI -> Ollama)
1. Udfyld Ollama embeddings for alle bøger:
   - Kør batch med `--provider ollama` indtil `SELECT COUNT(DISTINCT book_id) FROM chunks` ≈ `chunks_nomic`.
2. Shadow test:
   - `make shadow-up-ollama` + `make shadow-compare`.
3. Kvalitet:
   - Manuel spot-check i shadow svar.
4. Backup:
   - Tag database backup (`pg_dump` schema + data for chunks/chunks_nomic).
5. Flip provider i production env (`PROVIDER=ollama`) & redeploy (`make up-prod`).
6. Overvåg logs og latens (første 24 timer). Rollback: revert til `PROVIDER=openai`.

## Rollback (Efter Cutover)
1. Stop search: `docker compose -f docker-compose.base.yml down` (eller `make down-stacks`).
2. Sæt `.env` tilbage til OpenAI værdier.
3. Start igen: `make up-prod`.
4. Kør hurtig queries sanity test.

## Logning
- `LOG_LEVEL` styrer verbosity.
- `LOG_FORMAT=json` anbefales i production (fremtidig parsing pipeline).
- Lokal udvikling: `plain` for læsbarhed.

## Typiske Fejl & Løsninger
| Problem | Årsag | Løsning |
|---------|-------|---------|
| Orphan container warning | Tidligere services ikke defineret i ny stack | Brug `make up-minimal-clean` eller `make down-stacks` |
| Mangler ENVIRONMENT | `.env` uden ENVIRONMENT | Tilføj linjen eller acceptér transitional warning |
| Dummy i production fejl | Validator blokerer | Skift provider til openai/ollama |
| Ingen resultater i shadow | Forkert provider config | Tjek `PROVIDER`, model vars & logs |
| Lav overlap | Ikke alle bøger re-indekseret | Fortsæt batch processing med ny provider |

## Sikkerhed / Beskyttelse
- Ingen rigtige nøgler i test env.
- Rotér OpenAI nøgle ved mistanke om læk.
- Overvej fremtidig secret manager integration.

## Backup & Gendannelse (Kort)
```
pg_dump -h localhost -p 5433 -U postgres -d dhodb > backup.sql
psql -h localhost -p 5433 -U postgres -d dhodb < backup.sql
```
Fuld strategi bør inkludere versionsstemplede off-site kopier.

## Fremtidige Forbedringer
- `env_switch.sh` script.
- CI gate på overlap rapport (shadow) før provider cutover.
- JSON log parsing pipeline.
- Per-provider health endpoint.
- Dynamisk reload af konfiguration uden restart (planlagt efter Stage 9).

## Central Konfiguration (Stage 9)

Stage 9 introducerer et centralt konfigurationsmodul: `config/config_loader.py`.
Formål: Erstatte spredte `os.getenv` kald med et typed objekt (`AppConfig`) for bedre vedligehold, testbarhed og konsistens.

Nøglebrug:
```
from config.config_loader import get_config
cfg = get_config()
print(cfg.provider.name)
```

Struktur (uddrag):
```
AppConfig
   .provider.name            # openai | ollama | dummy
   .provider.openai_model
   .provider.ollama_model
   .embedding.timeout
   .embedding.max_retries
   .embedding.retry_backoff
   .search.distance_threshold
   .cors.allowed_origins
   .service.version
```

Singleton & Refresh:
```
from config.config_loader import refresh_config
refresh_config()  # Genindlæser miljøvariabler (bruges ved app startup)
```

Sikker Maskering:
```
cfg.to_safe_dict()  # Returnerer dict med maskerede secrets
```

Migreringsstrategi (inkrementel):
1. Kritisk API (`dhosearch.py`) migreret først.
2. Øvrige moduler (providers, book processing) migreres senere for at minimere regressions.
3. Ny kode bør undgå direkte `os.getenv`.

Health-check (`make health-check`) uændret – endpoints bruger nu central config men API kontrakten er identisk.

Fordele:
- Ensartet parsing af tal/float defaults.
- Tidlig validering af provider (fail-fast).
- Testbarhed (kan injicere dict i `load_config`).
- Forbereder dynamisk reload og evt. admin endpoint.

Begrænsninger midlertidigt:
- Kun distance-threshold + provider/embedding runtime anvendt aktivt i search API indtil fuld adoption.

Testdækning:
- `tests/test_config_loader.py` dækker defaults, invalid provider, parsing, singleton cache og masking.

Planlagt udbygning:
- Providers flyttes til central config konsum.
- Validation via Pydantic eller stricte enums.
- Eksperimentelt live-refresh endpoint.

---
Feedback eller forslag: opdater denne fil med dato + ændringsnotat.
