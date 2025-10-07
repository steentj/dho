Titel: Lokal Opsætning
Oprettet: 2025-10-07 12:35
Sidst ændret: 2025-10-07 12:35
Ejerskab: Udviklerteamet

# Formål
Denne guide beskriver den hurtigste måde at starte hele systemet på en macOS-udviklingsmaskine ved hjælp af de eksisterende Docker-kompositioner og hjælpe-scripts.

# Forudsætninger
- macOS 12 eller nyere med administratortilgange
- Docker Desktop \>= 4.31 (inkl. `docker compose` CLI)
- Git og en terminal (zsh eller bash)
- Netværksadgang til OpenAI hvis `PROVIDER=openai`

# Opsætningsworkflow
1. Klon repoet og gå til projektroden:
   ```bash
   git clone <REPO_URL> SlægtBib
   cd SlægtBib/src
   ```
2. Kopiér den lokale miljøfil og valider værdierne inden opstart:
   ```bash
   cp env/local.env soegemaskine/.env
   python scripts/validate_env.py --file env/local.env
   ```
   - Ret eventuelle fejl i `env/local.env` og kør valideringen igen, indtil status er OK.
3. Start lokal stack (postgres + embedding services + FastAPI) via Makefile:
   ```bash
   make -C soegemaskine up-local
   ```
   - Alternativt kan du køre `docker compose -f docker-compose.base.yml -f docker-compose.embeddings.yml up -d` inde fra `soegemaskine/`.
4. Bekræft at miljøet reagerer:
   ```bash
   curl http://localhost:8080/healthz
   curl http://localhost:8080/readyz
   ```
   Begge bør returnere status `ok`.
5. Validér bog-processeringskonfigurationen fra projektroden:
   ```bash
   ./scripts/process_books.sh --validate
   ```
   Kommandoen kører den containeriserede wrapper og sikrer database- og provider-adgang.

# Hurtig funktionstest
- Læg eksempel-URLer i en fil (én URL per linje) og kør:
  ```bash
  echo "https://example.com/bog.pdf" > sample_books.txt
  ./scripts/process_books.sh --file sample_books.txt
  ```
- Overvåg fremdriften:
  ```bash
  ./scripts/process_books.sh --monitor
  ```
- Resultater og logfiler findes i `soegemaskine/book_output/` og `soegemaskine/book_failed/`.

# Afslutning og oprydning
- Stop alle services, når du er færdig:
  ```bash
  make -C soegemaskine down-stacks
  ```
- Fjern kørende containere manuelt, hvis de er startet uden Makefile:
  ```bash
  cd soegemaskine
  docker compose down
  ```

# Typiske fejl og løsninger
- **Docker er ikke startet:** Åbn Docker Desktop og vent til “Engine Running” før `make up-local`.
- **Validering fejler på databaseport:** Sikr at `POSTGRES_PORT=5433` i `env/local.env`, og at ingen anden tjeneste bruger porten på værtsmaskinen.
- **`readyz` returnerer 503:** Kontroller at embedding provider matcher `.env`, og se container-logs via `docker compose logs -f searchapi`.
- **`process_books.sh --validate` fejler på provider:** Tjek at Ollama-containeren kører (`docker compose ps dho-ollama`) eller at OpenAI-nøglen er gyldig.
