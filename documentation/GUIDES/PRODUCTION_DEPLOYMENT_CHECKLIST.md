# Production Deployment Checklist

**Creation date:** 10. december 2025  
**Last Modified:** 10. december 2025

## Formål

Komplet step-by-step checklist for sikker deployment af DHO Semantic Search System til Linux produktionsserver. Følg denne checklist ved hver deployment for at minimere fejl og nedetid.

## Pre-Deployment Forberedelse

### 1. Planlægning
- [ ] **Vælg deployment vindue** med lav brugeraktivitet
- [ ] **Notificer brugere** om planlagt nedetid (hvis relevant)
- [ ] **Identificer ændringer** siden sidste deployment
- [ ] **Review git commit log** for breaking changes

### 2. Lokal Verificering
Før deployment til produktion skal alle ændringer testes lokalt på Mac:

- [ ] **Stop eksisterende containere:**
  ```bash
  cd soegemaskine
  docker compose -f docker-compose.base.yml -f docker-compose.embeddings.yml -f docker-compose.edge.yml down
  ```

- [ ] **Rebuild images uden cache:**
  ```bash
  docker compose -f docker-compose.base.yml build --no-cache searchapi
  docker compose -f docker-compose.embeddings.yml build --no-cache book-processor
  ```

- [ ] **Test minimal deployment:**
  ```bash
  make up-minimal
  sleep 5
  curl http://localhost:8000/healthz
  curl http://localhost:8000/readyz
  ```

- [ ] **Test search deployment:**
  ```bash
  docker compose -f docker-compose.base.yml down
  make up-search
  sleep 5
  curl http://localhost:8080/healthz
  curl http://localhost:8080/readyz
  ```

- [ ] **Verificer container security:**
  ```bash
  docker exec dhosearch id
  # Forventet: uid=1000(searchuser) gid=1000(searchuser)
  
  docker exec nginx id
  # Forventet: uid=101(nginx) gid=101(nginx)
  ```

- [ ] **Test fuld lokal stack (med ollama):**
  ```bash
  docker compose -f docker-compose.base.yml -f docker-compose.edge.yml down
  make up-local
  sleep 10
  curl http://localhost:8000/healthz
  ```

- [ ] **Run test suite:**
  ```bash
  python -m pytest tests/ -v
  ```

### 3. Backup Produktion
Før du ændrer noget på produktionsserveren:

- [ ] **SSH til produktion server:**
  ```bash
  ssh bruger@production-server
  ```

- [ ] **Backup PostgreSQL database:**
  ```bash
  docker exec dhodb pg_dump -U <username> -d <database> > /opt/backup/dho_backup_$(date +%Y%m%d_%H%M%S).sql
  ```

- [ ] **Backup .env fil:**
  ```bash
  cp /opt/dho/env/production.env /opt/backup/production.env.$(date +%Y%m%d_%H%M%S)
  ```

- [ ] **Backup docker volumes (hvis relevant):**
  ```bash
  docker run --rm -v postgres_data:/data -v /opt/backup:/backup alpine tar czf /backup/postgres_data_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .
  ```

- [ ] **Tag nuværende git commit:**
  ```bash
  cd /opt/dho/src
  git tag "prod-pre-deploy-$(date +%Y%m%d-%H%M%S)"
  git push origin --tags
  ```

## Deployment til Produktion

### 4. Synkroniser Kode
- [ ] **Pull latest changes:**
  ```bash
  cd /opt/dho/src
  git fetch --all
  git checkout main
  git pull origin main
  ```

- [ ] **Verificer korrekt commit:**
  ```bash
  git log --oneline -5
  git status
  # Skal være "nothing to commit, working tree clean"
  ```

### 5. Opdater Konfiguration
- [ ] **Verificer .env fil:**
  ```bash
  ls -la /opt/dho/env/production.env
  # Skal have permissions: -rw------- (600)
  ```

- [ ] **Valider konfiguration:**
  ```bash
  python scripts/validate_env.py --file /opt/dho/env/production.env --strict
  ```

- [ ] **Kopiér .env til soegemaskine mappe:**
  ```bash
  cp /opt/dho/env/production.env /opt/dho/src/soegemaskine/.env
  chmod 600 /opt/dho/src/soegemaskine/.env
  ```

### 6. Stop Eksisterende Services
- [ ] **Check nuværende container status:**
  ```bash
  cd /opt/dho/src/soegemaskine
  docker compose -f docker-compose.base.yml -f docker-compose.edge.yml ps
  ```

- [ ] **Stop alle containere:**
  ```bash
  docker compose -f docker-compose.base.yml -f docker-compose.edge.yml down
  ```

- [ ] **Verificer alt er stoppet:**
  ```bash
  docker ps -a | grep dho
  # Skal ikke vise kørende containere
  ```

### 7. Build Nye Images
- [ ] **Build search API image:**
  ```bash
  docker compose -f docker-compose.base.yml build --no-cache searchapi
  ```

- [ ] **Build book processor image (hvis nødvendig):**
  ```bash
  docker compose -f docker-compose.embeddings.yml build --no-cache book-processor
  ```

- [ ] **Verificer image builds:**
  ```bash
  docker images | grep soegemaskine
  ```

### 8. Start Production Stack
**Vigtigt:** Produktion kører UDEN embeddings (ingen ollama). Brug kun base + edge:

- [ ] **Start produktion (postgres + searchapi + nginx):**
  ```bash
  docker compose -f docker-compose.base.yml -f docker-compose.edge.yml up -d
  ```

- [ ] **Vent på container opstart:**
  ```bash
  sleep 10
  ```

- [ ] **Check container status:**
  ```bash
  docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
  ```

## Post-Deployment Verificering

### 9. Health Checks
- [ ] **Verificer searchapi health:**
  ```bash
  curl -s https://<domain>/healthz | python3 -m json.tool
  # Forventet: {"status":"ok","service":"searchapi","provider":"openai",...}
  ```

- [ ] **Verificer readiness:**
  ```bash
  curl -s https://<domain>/readyz | python3 -m json.tool
  # Forventet: {"status":"ok","db":"ok","provider":"ok",...}
  ```

- [ ] **Test search endpoint:**
  ```bash
  curl -X POST https://<domain>/search \
    -H "Content-Type: application/json" \
    -d '{"query":"test søgning","top_n":5}' | python3 -m json.tool
  ```

### 10. Security Verification
- [ ] **Verificer non-root users:**
  ```bash
  docker exec dhosearch id
  # Forventet: uid=1000(searchuser) gid=1000(searchuser)
  ```

- [ ] **Check nginx process user:**
  ```bash
  docker exec nginx id
  # Forventet: uid=101(nginx) gid=101(nginx)
  ```

- [ ] **Verificer .env permissions:**
  ```bash
  ls -la /opt/dho/src/soegemaskine/.env
  # Skal være: -rw------- (600)
  ```

### 11. Log Monitoring
- [ ] **Monitor searchapi logs:**
  ```bash
  docker logs -f dhosearch --tail 50
  # Kig efter errors eller warnings
  ```

- [ ] **Monitor postgres logs:**
  ```bash
  docker logs -f dhodb --tail 50
  ```

- [ ] **Monitor nginx logs:**
  ```bash
  docker logs -f nginx --tail 50
  ```

### 12. Performance Checks
- [ ] **Test response times:**
  ```bash
  time curl -s https://<domain>/healthz
  # Skal være under 200ms
  ```

- [ ] **Check container resources:**
  ```bash
  docker stats --no-stream
  ```

- [ ] **Verificer database connections:**
  ```bash
  docker exec dhodb psql -U <user> -d <database> -c "SELECT count(*) FROM pg_stat_activity;"
  ```

## Post-Deployment Tasks

### 13. Documentation & Tagging
- [ ] **Tag successful deployment:**
  ```bash
  cd /opt/dho/src
  git tag "prod-deploy-$(date +%Y%m%d-%H%M%S)"
  git push origin --tags
  ```

- [ ] **Dokumenter deployment:**
  - Deployment dato og tid
  - Deployed git commit hash
  - Eventuelle issues under deployment
  - Response times og performance metrics

- [ ] **Opdater deployment log:**
  ```bash
  echo "$(date '+%Y-%m-%d %H:%M:%S') - Deployment successful - commit $(git rev-parse --short HEAD)" >> /opt/dho/logs/deployment.log
  ```

### 14. Cleanup
- [ ] **Fjern gamle images (valgfrit):**
  ```bash
  docker image prune -f
  ```

- [ ] **Verificer disk space:**
  ```bash
  df -h
  ```

- [ ] **Ryd gamle backups ældre end 30 dage:**
  ```bash
  find /opt/backup -name "dho_backup_*.sql" -mtime +30 -delete
  ```

### 15. Notifikation
- [ ] **Notificer brugere** at systemet er oppe igen
- [ ] **Opdater status page** (hvis relevant)
- [ ] **Send deployment rapport** til stakeholders

## Rollback Procedure

Hvis deployment fejler, følg denne rollback procedure:

### Hurtig Rollback
1. **Stop fejlende containere:**
   ```bash
   docker compose -f docker-compose.base.yml -f docker-compose.edge.yml down
   ```

2. **Checkout forrige version:**
   ```bash
   git checkout <previous-tag>
   # Eksempel: git checkout prod-deploy-20251209-143000
   ```

3. **Rebuild images:**
   ```bash
   docker compose -f docker-compose.base.yml build --no-cache searchapi
   ```

4. **Start services:**
   ```bash
   docker compose -f docker-compose.base.yml -f docker-compose.edge.yml up -d
   ```

5. **Verificer health:**
   ```bash
   curl -s https://<domain>/healthz
   curl -s https://<domain>/readyz
   ```

### Database Rollback (hvis nødvendig)
1. **Stop alle containere**
2. **Restore database backup:**
   ```bash
   docker exec -i dhodb psql -U <user> -d <database> < /opt/backup/dho_backup_YYYYMMDD_HHMMSS.sql
   ```
3. **Restart services**

### Security Rollback
Hvis permission issues opstår:
- Se detaljeret rollback procedure i `documentation/TEKNISK/DOCKER_SECURITY.md`
- Midlertidig root-user kan aktiveres i Dockerfile hvis kritisk

## Emergency Contacts
- **System Administrator:** [kontakt]
- **Database Administrator:** [kontakt]
- **On-Call Developer:** [kontakt]

## References
- `documentation/CORE/03_DEPLOYMENT.md` - Deployment overview
- `documentation/TEKNISK/DOCKER_SECURITY.md` - Security configuration
- `documentation/REFERENCE/KONFIGURATION.md` - Configuration guide
- `soegemaskine/Makefile` - Available make targets

## Changelog

### 2025-12-10: Initial Version
- Komplet production deployment checklist oprettet
- Inkluderer pre-deployment, deployment, og post-deployment steps
- Security verification inkluderet (non-root users)
- Rollback procedures dokumenteret
- Noterer at ollama KUN anvendes i development, ikke i produktion
