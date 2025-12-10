# Docker Container Sikkerhed

**Creation date:** 10. december 2025  
**Last Modified:** 10. december 2025

## Formål

Dette dokument beskriver sikkerhedskonfigurationen for DHO Semantic Search System's Docker-containere, med fokus på non-root bruger princippet og least privilege security model.

## Security Audit Resultat

**Audit dato:** 10. december 2025  
**Status:** ✅ Alle produktions-containere sikret

### Container Security Oversigt

| Container | Service | USER Setting | UID | Security Status |
|-----------|---------|--------------|-----|-----------------|
| `dhosearch` | Search API | searchuser | 1000 | ✅ Non-root |
| `dhodb` | PostgreSQL | (default) | variabel | ℹ️ Vendor default |
| `nginx` | Reverse Proxy | nginx | 101 | ✅ Non-root (vendor) |
| `dho-book-processor` | Book Processing | bookuser | 1000 | ✅ Non-root |
| `dho-ollama` | Embeddings (dev only) | (default) | 0 | ⚠️ Dev only, root |

## Sikkerhedsprincipper

### 1. Non-Root Container Execution

**Rationale:** Containere der kører som root udgør en betydelig sikkerhedsrisiko. Hvis en angriber kompromitterer containeren, har de root-rettigheder, hvilket kan bruges til:
- Privilege escalation på host-systemet
- Modification af container images
- Adgang til host resources via volume mounts

**Implementation:** Alle produktions-containere kører nu som non-root brugere med UID 1000 (searchuser, bookuser) eller vendor defaults (nginx uid=101).

### 2. Least Privilege Principle

Hver container har kun de rettigheder der er nødvendige for dens specifikke funktion:
- **Search API:** Read-only database access, ingen volume mounts
- **Book Processor:** Write access kun til output directories via controlled volumes
- **PostgreSQL:** Isoleret data directory med strenge permissions
- **Nginx:** Read-only config og certificate files

### 3. Network Isolation

- Internal `dho-network` bridge network
- Kun nginx eksponerer eksterne porte (80, 443, 8080)
- PostgreSQL bundet til localhost (127.0.0.1:5432)
- Inter-container kommunikation via intern DNS

## Container Konfiguration Detaljer

### dhosearch (Search API)

**Dockerfile:** `soegemaskine/searchapi/Dockerfile`

```dockerfile
# Security configuration
RUN groupadd -r searchuser -g 1000 && useradd -r -g searchuser -u 1000 searchuser
RUN chown -R searchuser:searchuser /code
USER searchuser
```

**Properties:**
- UID/GID: 1000
- Arbejdsmappe: `/code` (ejet af searchuser)
- Ingen volume mounts (stateless)
- Netværk: Intern kommunikation til dhodb

**Verificering:**
```bash
docker exec dhosearch id
# Output: uid=1000(searchuser) gid=1000(searchuser) groups=1000(searchuser)
```

### dho-book-processor

**Dockerfile:** `create_embeddings/Dockerfile`

```dockerfile
# Security configuration
RUN useradd -m -u 1000 bookuser && chown -R bookuser:bookuser /app
USER bookuser
```

**Properties:**
- UID/GID: 1000 (samme som searchuser for konsistens)
- Arbejdsmappe: `/app` (ejet af bookuser)
- Volume mounts:
  - `./book_input:/app/input:ro` (read-only)
  - `./book_output:/app/output` (read-write)
  - `./book_failed:/app/failed` (read-write)
- Permission validation via `scripts/setup_permissions.sh`

**Verificering:**
```bash
docker exec dho-book-processor id
# Output: uid=1000(bookuser) gid=1000(bookuser) groups=1000(bookuser)
```

### dhodb (PostgreSQL)

**Image:** `pgvector/pgvector:pg16` (official)

**Properties:**
- Bruger: Default postgres user fra vendor image
- UID: Typisk 999, men varierer baseret på image version
- Data directory: `/var/lib/postgresql/data` med strenge permissions (700)
- Netværk: Kun tilgængelig på localhost:5432 og intern docker network

**Note:** PostgreSQL vendor image håndterer selv user security og permission management. Containeren starter som root men dropper til postgres-bruger ved opstart af databasen.

### nginx (Reverse Proxy)

**Image:** `nginx:latest` (official)

**Properties:**
- Bruger: nginx (UID 101) fra vendor image
- Config files: Read-only mounts
- TLS certificates: Read-only mounts fra `/etc/letsencrypt`
- Netværk: Eksponer porte 80, 443, 8080

**Note:** Official nginx image kører som non-root user som standard.

### dho-ollama (Development Only)

**Image:** `ollama/ollama:latest` (official)

**Properties:**
- Bruger: root (UID 0) - vendor limitation
- Anvendelse: **KUN development/test miljøer**
- Volume: `${HOME}/dhoOllamaModels:/root/.ollama`
- Netværk: Port 11434

**Security Note:** Ollama-containeren kører som root pga. vendor image design. Dette accepteres fordi:
1. Containeren anvendes KUN i development (`make up-local`)
2. Containeren er IKKE inkluderet i produktion deployments
3. Netværk isolation begrænser eksponering

## Deployment Scenarios

### Minimal Production (Anbefalet)
```bash
make up-minimal    # postgres + searchapi
```
**Containers:** dhodb, dhosearch  
**Security:** ✅ Alle non-root eller vendor defaults

### Production med Nginx
```bash
make up-search     # base + nginx
```
**Containers:** dhodb, dhosearch, nginx  
**Security:** ✅ Alle non-root eller vendor defaults

### Local Development
```bash
make up-local      # base + embeddings (inkl. ollama)
```
**Containers:** dhodb, dhosearch, dho-ollama, dho-book-processor  
**Security:** ⚠️ Ollama kører som root (accepteret i dev)

## Verificering af Security Configuration

### Quick Security Check

Kør følgende kommandoer for at verificere non-root status:

```bash
# Check search API
docker exec dhosearch id
docker exec dhosearch whoami

# Check book processor (hvis kørende)
docker exec dho-book-processor id

# Check alle kørende containere
docker ps --format "table {{.Names}}\t{{.Image}}" | while read name image; do
    [ "$name" = "NAMES" ] && continue
    echo "=== $name ==="
    docker exec "$name" id 2>/dev/null || echo "Container not running or no shell"
done
```

### Expected Output

**dhosearch:**
```
uid=1000(searchuser) gid=1000(searchuser) groups=1000(searchuser)
```

**dho-book-processor:**
```
uid=1000(bookuser) gid=1000(bookuser) groups=1000(bookuser)
```

**nginx:**
```
uid=101(nginx) gid=101(nginx) groups=101(nginx)
```

## Rollback Procedure

Hvis der opstår permission issues efter deployment, kan containers midlertidigt køres som root:

### Emergency Rollback Steps

1. **Stop containere:**
```bash
cd soegemaskine
docker compose -f docker-compose.base.yml down
```

2. **Kommenter USER direktivet ud i Dockerfile:**
```dockerfile
# Midlertidig rollback - FJERN SENERE
# USER searchuser
```

3. **Rebuild og start:**
```bash
docker compose -f docker-compose.base.yml build --no-cache searchapi
docker compose -f docker-compose.base.yml up -d
```

4. **Verificer root status:**
```bash
docker exec dhosearch id
# Output: uid=0(root) gid=0(root) groups=0(root)
```

5. **Løs permission issues:**
```bash
# Eksempel: Fix file ownership
docker exec dhosearch chown -R 1000:1000 /code/problemdir
```

6. **Genetabler non-root:**
   - Uncommit USER direktiv i Dockerfile
   - Rebuild med `--no-cache`
   - Redeploy

**VIGTIGT:** Rollback til root skal kun anvendes som midlertidig løsning. Identificer og løs den underliggende permission issue hurtigst muligt.

## Best Practices

### 1. Konsistent UID Strategi
- Brug samme UID (1000) for applikations-containere hvor muligt
- Dokumenter vendor default UIDs (nginx=101, postgres=999)
- Undgå UID konflikter mellem containers der deler volumes

### 2. Volume Mount Permissions
```bash
# Host-side preparation før container start
mkdir -p book_output book_failed
chown -R 1000:1000 book_output book_failed
chmod 700 book_output book_failed
```

Alternativt brug `scripts/setup_permissions.sh` som håndterer dette automatisk.

### 3. Minimal Volume Mounts
- Kun mount hvad der er nødvendigt
- Brug `:ro` (read-only) flag hvor muligt
- Undgå mounting af sensitive host directories

### 4. Regular Security Audits
```bash
# Månedlig security check
for container in $(docker ps --format '{{.Names}}'); do
    echo "=== $container ==="
    docker exec "$container" id 2>/dev/null || echo "No shell access"
done
```

### 5. Container Scanning
```bash
# Scan images for vulnerabilities (kræver tools)
docker scout cves soegemaskine-searchapi
trivy image soegemaskine-searchapi
```

## Known Issues & Limitations

### 1. PostgreSQL Container Reports Root
PostgreSQL container starter som root men postgres-processen selv kører som postgres-bruger. Dette er vendor default behavior og accepteret.

### 2. Ollama Kræver Root
Ollama vendor image kræver root. Limitation accepteret fordi containeren kun bruges i development.

### 3. Nginx Container Starter som Root
Nginx container starter som root men nginx worker processes kører som nginx-bruger (UID 101). Dette er standard nginx behavior.

## Referencer

- [Docker Security Best Practices](https://docs.docker.com/develop/security-best-practices/)
- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)

## Changelog

### 2025-12-10: Initial Security Audit
- ✅ Opdateret `soegemaskine/searchapi/Dockerfile` med searchuser (UID 1000)
- ✅ Verificeret dho-book-processor kører som bookuser (UID 1000)
- ✅ Dokumenteret vendor default security for nginx og postgres
- ✅ Markeret dho-ollama som development-only med root limitation
- ✅ Fjernet shadow container infrastructure (ikke længere nødvendig)
- ✅ Testet alle deployment scenarios (minimal, search, local)
