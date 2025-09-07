Titel: Deployment Guide
Version: v1.0
Oprettet: 2025-09-04
Sidst ændret: 2025-09-04
Ejerskab: Driftansvarlig
Formål: Sikre reproducerbar manuel udrulning i tre miljøer

# 1. Scope
Dækker lokal udvikling og produktion på fjern Linux. Ingen automatiseret CI/CD.

# 2. Miljøtyper
| Miljø | Formål | Kendetegn |
|-------|--------|-----------|
| Lokal (Mac) | Udvikling & hurtig test | venv + Docker Compose |
| Produktion | Endelig drift | Hardened Linux, backup, overvågning |

# 3. Forudsætninger
- Docker & Docker Compose installeret
- SSH nøgle (ed25519 anbefales)
- Adgang til repository (git)
- PostgreSQL port åben internt (typisk 5432)

Eksterne kilder:
- Docker: https://docs.docker.com/
- SSH nøgle: https://www.ssh.com/academy/ssh/keygen

# 4. Lokal Opsætning
1. Klon repo
2. Opret `.env` filer fra `.env.template` i relevante kataloger
3. Validér konfiguration:
```bash
python scripts/validate_env.py
```
4. Byg & start services med embedding profil:
```bash
cd soegemaskine
docker-compose --profile embeddings up --build -d
```
5. Opsæt Ollama, hvis dette bruges som provider:
```bash
../scripts/setup_ollama.sh
```
6. Kør tests:
```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install -r create_embeddings/requirements.txt
python -m pytest
```

# 5. Staging (valgfri, Linux)
En valgfri staging-miljø kan opsættes på en almindelig Linux-vært for accepttest og shadow-sammenligning:

1. Klon repository på staging-værten
2. Opret separat `.env` (fx `env/staging.env`) uden produktionshemmeligheder
3. Validér miljø:
```bash
python scripts/validate_env.py --file env/staging.env
```
4. Start services med staging `.env` (kopiér midlertidigt til roden som `.env` eller brug make/compose overrides)
```bash
cd soegemaskine
docker-compose --profile embeddings up -d
```
5. Shadow-test efter behov (se scripts og docker-compose.shadow.yml)

# 6. Produktion
1. Opret dedikeret linuxbruger (ingen root login)
2. Hardening (ufw allow 22/tcp, 80/tcp, 443/tcp; deny resten)
3. Installer Docker + Compose plugin
4. Opret sikre `.env` filer (ikke committe)
5. Pull repository (tag'et release anbefales)
6. Validér konfiguration:
```bash
python scripts/validate_env.py
```
7. Byg og start:
```bash
cd soegemaskine
docker-compose --profile embeddings pull
docker-compose --profile embeddings up -d --build
```
8. Opsæt Ollama (hvis dette anvendes som provider):
```bash
../scripts/setup_ollama.sh
```
9. Tjek logs:
```bash
docker-compose logs --tail=100 -f
```
10. Sundhedstjek: curl API `/health`
11. Backup DB:
```bash
docker exec -t dho-postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup_$(date +%F).sql
```

# 7. .env Håndtering
- Skabelon i hvert subsystem.
- Produktionsfiler ejes af root:root med 600 rettigheder.
- Rotation af hemmeligheder planlægges kvartalsvis.

# 8. Fejlfinding
| Symptomer | Handling |
|-----------|----------|
| API svarer ikke | `docker compose ps` → container status |
| DB fejl ved embeddings | Kontroller tabelforfiks og migationer |
| Manglende netværk | Firewall/ufw regler |
| Høj latenstid | Tjek embedding provider latency |
| Konfigurationsfejl | Kør `python scripts/validate_env.py` |
| Ollama problemer | Kør `scripts/test_ollama_setup.py` |
| Shadow Search comparison | Kør `scripts/compare_search_results.py` |

### Environment Validation
```bash
# Kør validering og få detaljeret fejlinfo
python scripts/validate_env.py --strict

# JSON output for automatisering
python scripts/validate_env.py --json > env_validation.json
```

### Ollama Setup Troubleshooting
```bash
# Test om Ollama er korrekt konfigureret
python scripts/test_ollama_setup.py

# Genopsæt model hvis nødvendigt
./scripts/setup_ollama.sh
```

# 9. Rollback Procedure
1. Find tidligere image tag `docker images`.
2. Stop nuværende: `docker compose down` (bevar volumener).
3. Checkout tidligere git tag.
4. Start igen: `docker compose up -d --build`.

# 10. Sikkerhedsnoter
- Ingen deling af `.env` via chat / mail.
- SSH nøgle passphrase kræves.
- Opdater pakker regelmæssigt (`apt update && apt upgrade`).

# 11. Deployment Scripts

| Script | Funktion | Anvendelse |
|--------|----------|------------|
| `validate_env.py` | Validerer konfigurationsvariabler i `.env` filer | Før deployment eller konfigurationsændringer |
| `setup_ollama.sh` | Opsætter Ollama med korrekt embedding model | Efter container opstart hvis Ollama bruges |
| `run_shadow_search.sh` | Starter sekundær søge-API til A/B test | Til test af alternative modeller uden at påvirke hovedsøgning |
| `compare_search_results.py` | Sammenligner søgeresultater mellem APIs | Efter kørsel af shadow search for kvalitetssammenligning |

## Monitoring Scripts

### Status Verification
```bash
# Kør for at validere systemets nuværende sundhed
./scripts/process_books.sh --validate
```

### Container Status
```bash
# Tjek containere
cd soegemaskine
docker-compose ps

# Tjek embedding service
docker logs dho-ollama  # Hvis Ollama bruges
```

# 12. Referencer
- ENV_KONFIGURATION
- Arkitektur (overblik)
