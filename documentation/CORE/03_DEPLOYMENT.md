Titel: Deployment Guide
Version: v1.1
Oprettet: 2025-09-04
Sidst ændret: 2025-10-07
Ejerskab: Driftansvarlig
Formål: Sikre reproducerbar manuel udrulning i lokal og produktionsmiljø.

# 1. Scope
Fokuserer på to manuelle målmiljøer: macOS udviklingsmaskiner og den dedikerede Linux-produktionsserver. For staging/scenarie-test henvises til shadow-workflows nederst.

# 2. Centrale afhængigheder
- Docker Engine + Compose plugin (`docker compose` CLI)
- Git-adgang til repository
- SSH-nøgle til fjernservere
- Validerede miljøfiler i `env/`

Se også `documentation/GUIDES/LOCAL_SETUP.md` og `documentation/GUIDES/PRODUCTION_DEPLOY.md` for trin-for-trin eksempler.

# 3. Lokal udvikling (macOS opsummering)

## 3.1 Make-kommandoer forklaring
`make` er et build-automatiseringsværktøj der kører opgaver defineret i `soegemaskine/Makefile`. Flaget `-C soegemaskine` beder make skifte til `soegemaskine/`-mappen før kørsel.

Eksempel: `make -C soegemaskine up-local` = skift til `soegemaskine/` og kør target `up-local`, som internt kalder `docker compose -f docker-compose.base.yml -f docker-compose.embeddings.yml up -d`.

## 3.2 Kun søgning (minimal setup)
Hvis du kun vil teste **søge-API'et** uden bogbehandling:

1. Kopiér miljøfil:
	```bash
	cp env/local.env soegemaskine/.env
	```
2. Valider konfiguration:
	```bash
	python scripts/validate_env.py --file env/local.env
	```
3. Start **kun** PostgreSQL + SearchAPI (uden embedding/bogbehandling):
	```bash
	make -C soegemaskine up-minimal
	```
	Dette starter kun `postgres` og `searchapi` containers (port 8080).

4. Bekræft API-sundhed:
	```bash
	curl http://localhost:8080/healthz
	curl http://localhost:8080/readyz
	```

## 3.3 Med nginx reverse proxy (production-lignende)
For at teste med nginx reverse proxy (som i produktion):

1. Brug **up-prod** i stedet:
	```bash
	make -C soegemaskine up-prod
	```
	Dette kombinerer base + embeddings + edge (nginx), og eksponerer API via nginx på port 8080.

2. Test via nginx:
	```bash
	curl http://localhost:8080/healthz
	```

## 3.4 Fuld lokal udvikling (med bogbehandling)
Til både søgning **og** bogbehandling:

1. Kopiér miljøfil:
	```bash
	cp env/local.env soegemaskine/.env
	```
2. Valider konfiguration:
	```bash
	python scripts/validate_env.py --file env/local.env
	```
3. Start base + embeddings (PostgreSQL + SearchAPI + Ollama):
	```bash
	make -C soegemaskine up-local
	```
	Dette svarer til: `docker compose -f docker-compose.base.yml -f docker-compose.embeddings.yml up -d`

4. Bekræft API-sundhed:
	```bash
	curl http://localhost:8080/healthz
	curl http://localhost:8080/readyz
	```
5. Kør bog-pipelinevalidering eller batchjobs:
	```bash
	./scripts/process_books.sh
	```

## 3.5 Test GUI til søgning
For at teste søgning via en lokal webgrænseflade:

1. Sørg for at søge-API'et kører (se 3.2 eller 3.3 ovenfor).

2. Start test-GUI'en:
	```bash
	cd api_testgui
	./start_gui.sh
	```

3. Åbn browser på `http://localhost:8501` og test søgninger interaktivt.

**Bemærk:** GUI'en forventer at API'et kører på `http://localhost:8080/search` (nginx endpoint).

## 3.6 Nedlukning
Stop alle services:
```bash
make -C soegemaskine down-stacks
```

# 4. Produktion (Linux)
1. Synkronisér repositoriet:
	```bash
	ssh bruger@server
	cd /opt/dho/src
	git fetch --all
	git checkout main
	git pull origin main
	```
2. Opdater miljøfil:
	```bash
	cp /opt/dho/env/production.env soegemaskine/.env
	python scripts/validate_env.py --file /opt/dho/env/production.env --strict
	```
3. Byg/pull images ved behov (afhængigt af ændringer):
	```bash
	make -C soegemaskine up-prod
	```
	Dette kombinerer base-, embeddings- og edge-compose-filer. Hvis kode/requirements ændres, kør `docker compose --profile embeddings build searchapi book-processor` først.
4. Overvåg opstart:
	```bash
	docker compose -f soegemaskine/docker-compose.base.yml logs -f searchapi
	```
5. Sundhedstjek (med TLS):
	```bash
	curl -k https://<domæne>/healthz
	curl -k https://<domæne>/readyz
	```
6. Efter bekræftet drift, kør bogpipeline-validering:
	```bash
	./scripts/process_books.sh --validate
	```

# 5. Shadow / staging (valgfrit)
- Brug `make shadow-up` / `shadow-up-ollama` til parallel søgning på port 18000.
- Sammenlign resultater med `make shadow-compare` eller `scripts/compare_search_results.py`.
- Stop med `make shadow-down`.

# 6. Konfigurationsstyring
- Primære skabeloner findes i `.env.template` og `env/`-mapperne.
- Læs detaljer i `documentation/REFERENCE/KONFIGURATION.md`.
- Production `.env` skal have filrettigheder `600` og opbevares uden for git (fx `/opt/dho/env/`).

# 7. Rollback strategi
1. Stop services: `make -C soegemaskine down-stacks`.
2. Tjek foregående tag/commit ud: `git checkout <tag>`.
3. Start igen med `make -C soegemaskine up-prod`.
4. Gentag sundhedstjek og pipeline-validering.

# 8. Fejlfinding (udvalg)
| Problem | Handling |
|---------|----------|
| API utilgængelig | `docker compose ps`, check searchapi-logs |
| `readyz` 503 | Bekræft databaseforbindelse og embedding-provider |
| Provider-timeout | For OpenAI: kontroller netværk/nøgle. For Ollama: `docker compose logs -f dho-ollama` |
| Validator-fejl | Ret manglende/mismatch variabler og kør `validate_env.py` igen |
| TLS-fejl i edge | Kontroller bind mounts i `docker-compose.edge.yml` og certifikat-rettigheder |

# 9. Scripts og værktøjer
- `scripts/validate_env.py` – miljøvalidering (`--strict`, `--json` flag)
- `scripts/process_books.sh` – validering, kørsel, monitorering af batchjobs
- `scripts/setup_ollama.sh` – trækker `nomic-embed-text` ind i Ollama-containeren
- `scripts/test_ollama_setup.py` – sundhedstjek af lokal Ollama
- `api_testgui/app.py` – Streamlit-baseret web-GUI til interaktiv søgetestning (kræver `streamlit run`)

# 10. Make targets oversigt
Nyttige `make`-targets i `soegemaskine/Makefile`:

| Target | Beskrivelse |
|--------|-------------|
| `make -C soegemaskine up-minimal` | Start kun postgres + searchapi (minimal setup) |
| `make -C soegemaskine up-local` | Start base + embeddings (postgres + searchapi + ollama) |
| `make -C soegemaskine up-prod` | Start alt inkl. nginx edge (production-lignende) |
| `make -C soegemaskine down-stacks` | Stop alle services |
| `make -C soegemaskine ps-stacks` | Vis kørende containers |
| `make -C soegemaskine logs-stacks` | Følg logs fra alle services |
| `make -C soegemaskine health-check` | Curl /healthz og /readyz endpoints |
| `make -C soegemaskine shadow-up` | Start shadow search til A/B-test (port 18000) |

# 11. Referencer
- `documentation/GUIDES/LOCAL_SETUP.md`
- `documentation/GUIDES/PRODUCTION_DEPLOY.md`
- `documentation/REFERENCE/KONFIGURATION.md`
- `documentation/CORE/04_BOG_PROCESSERING.md`
