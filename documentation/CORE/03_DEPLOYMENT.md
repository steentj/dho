Titel: Deployment Guide
Version: v1.0
Oprettet: 2025-09-04
Sidst ændret: 2025-09-04
Ejerskab: Driftansvarlig
Formål: Sikre reproducerbar manuel udrulning i tre miljøer

# 1. Scope
Dækker lokal udvikling, WSL preprod og produktion på fjern Linux. Ingen automatiseret CI/CD.

# 2. Miljøtyper
| Miljø | Formål | Kendetegn |
|-------|--------|-----------|
| Lokal (Mac) | Udvikling & hurtig test | venv + Docker Compose |
| WSL (LAN) | Preprod / accept | WSL2 Ubuntu, delt netværk |
| Produktion | Endelig drift | Hardened Linux, backup, overvågning |

# 3. Forudsætninger
- Docker & Docker Compose installeret
- SSH nøgle (ed25519 anbefales)
- Adgang til repository (git)
- PostgreSQL port åben internt (typisk 5432)

Eksterne kilder:
- Docker: https://docs.docker.com/
- WSL: https://learn.microsoft.com/windows/wsl/
- SSH nøgle: https://www.ssh.com/academy/ssh/keygen

# 4. Lokal Opsætning
1. Klon repo
2. Opret `.env` filer fra `.env.template` i relevante kataloger
3. Byg & start services:
```
docker compose up --build
```
4. Kør tests:
```
python -m venv .venv && source .venv/bin/activate
python -m pip install -r create_embeddings/requirements.txt
python -m pytest
```

# 5. WSL Preprod
1. Installer WSL2 + Ubuntu
2. Installer Docker Engine (ikke Desktop) i WSL
3. Kopiér kode (git clone eller rsync)
4. Opret produktionslignende `.env` (uden rigtige prod keys hvis ikke nødvendigt)
5. Start:
```
docker compose up -d
```
6. Verificér med `docker ps` og API `/health` endpoint

# 6. Produktion
1. Opret dedikeret linuxbruger (ingen root login)
2. Hardening (ufw allow 22/tcp, 80/tcp, 443/tcp; deny resten)
3. Installer Docker + Compose plugin
4. Opret sikre `.env` filer (ikke committe)
5. Pull repository (tag'et release anbefales)
6. Byg og start:
```
docker compose pull
docker compose up -d --build
```
7. Tjek logs:
```
docker compose logs --tail=100 -f
```
8. Sundhedstjek: curl API `/health`
9. Backup DB:
```
docker exec -t <db_container> pg_dump -U $DB_USER $DB_NAME > backup_$(date +%F).sql
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

# 9. Rollback Procedure
1. Find tidligere image tag `docker images`.
2. Stop nuværende: `docker compose down` (bevar volumener).
3. Checkout tidligere git tag.
4. Start igen: `docker compose up -d --build`.

# 10. Sikkerhedsnoter
- Ingen deling af `.env` via chat / mail.
- SSH nøgle passphrase kræves.
- Opdater pakker regelmæssigt (`apt update && apt upgrade`).

# 11. Referencer
- ENV_KONFIGURATION
- Arkitektur (overblik)
