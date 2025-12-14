Titel: Produktionsudrulning
Oprettet: 2025-10-07 12:37
Sidst ændret: 2025-10-07 12:37
Ejerskab: Driftansvarlig

# Formål
Guiden beskriver den simpleste manuelle procedure for at opdatere produktionsmiljøet på den eksterne Linux-server ved hjælp af de eksisterende Docker-kompositioner.

# Forudsætninger
- Linux-vært med Docker Engine \>= 24 og Compose-plugin (`docker compose`)
- Ikke-root bruger i `docker`-gruppen
- HTTPS-certifikater placeret på serveren (jf. `soegemaskine/docker-compose.edge.yml`)
- Adgang til repository (SSH-nøgle)

# Før du logger ind
1. Afslut lokale tests og verificér at `main` eller den ønskede release er klar.
2. Opdater produktionsmiljøfil lokalt (`env/production.env`) med nye nøgler eller hosts.
3. **✅ Sikkerhed:** Verificér at `daemon.json` er konfigureret med user namespace remapping (se tjekliste nedenfor).
4. Overfør den opdaterede fil sikkert til serveren, fx:
   ```bash
   scp env/production.env bruger@server:/opt/dho/env/production.env
   ```

# Docker Daemon Sikkerhedskonfiguration (Første Gang)

**OBS:** Kun nødvendig ved første deployment eller hvis ikke allerede konfigureret.

1. **Verificér om namespace remapping er aktiveret:**
   ```bash
   ssh bruger@server
   docker info | grep -i "user namespace"
   ```
   
   Hvis output viser `User Namespaces: ID maps:`, er det allerede aktiveret. Spring til "Udrulning på serveren".

2. **Aktivér user namespace remapping (hvis ikke aktiveret):**
   ```bash
   # Backup eksisterende daemon.json (hvis den findes)
   sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.backup
   
   # Kopiér daemon.json fra projekt til Docker
   sudo cp daemon.json /etc/docker/daemon.json
   
   # Alternativt: tilføj kun userns-remap hvis filen eksisterer
   # sudo nano /etc/docker/daemon.json
   # Tilføj: "userns-remap": "default"
   ```

3. **Genstart Docker daemon:**
   ```bash
   sudo systemctl restart docker
   ```

4. **Verificér aktivering:**
   ```bash
   docker info | grep -i "user namespace"
   # Forventet: User Namespaces: ID maps: uid=100000-165535, gid=100000-165535
   
   grep dockremap /etc/subuid /etc/subgid
   # Forventet: dockremap:100000:65536
   ```

5. **Håndter volume ownership (kun nødvendigt efter første aktivering):**
   ```bash
   # Stop eventuelle kørende containere
   cd /opt/dho/src/soegemaskine
   docker compose down
   
   # Backup volumes
   sudo cp -a /var/lib/docker/volumes /var/lib/docker/volumes.backup
   
   # Find PostgreSQL volume og juster ownership (kun hvis nødvendigt)
   # Note: Docker håndterer normalt dette automatisk
   ```

# Udrulning på serveren
1. Log ind på værten og gå til projektet:
   ```bash
   ssh bruger@server
   cd /opt/dho/src
   ```
2. Hent seneste kode og evt. tag:
   ```bash
   git fetch --all --tags
   git checkout main
   git pull origin main
   ```
3. **Sikkerhedstjekliste:**
   - ✅ User namespace remapping aktiveret (se ovenfor)
   - ✅ Non-root bruger i Docker-gruppe
   - ✅ `.env` filer har rettigheder 600
   - ✅ Certifikater har korrekte rettigheder
   
4. Valider miljøvariablerne med streng mode:
   ```bash
   python scripts/validate_env.py --file /opt/dho/env/production.env --strict
   ```
   Løs alle fejl før du fortsætter.
   
5. Kopiér miljøfilen til søgemaskine-servicen (ikke check den ind):
   ```bash
   cp /opt/dho/env/production.env soegemaskine/.env
   ```
   
6. Træk opdaterede containere og start hele stacken (postgres + embeddings + edge):
   ```bash
   make -C soegemaskine up-prod
   ```
   - Kommandoen kombinerer `docker-compose.base.yml`, `docker-compose.embeddings.yml` og `docker-compose.edge.yml`.
   - Ved større kodeændringer: `docker compose --profile embeddings build searchapi book-processor` inde fra `soegemaskine/` før `make up-prod`.
   
7. Overvåg loggene i de første minutter:
   ```bash
   docker compose -f soegemaskine/docker-compose.base.yml logs -f searchapi
   docker compose -f soegemaskine/docker-compose.embeddings.yml logs -f book-processor
   ```
   
8. Sundhedstjek:
   ```bash
   curl -k https://<dit-domæne>/healthz
   curl -k https://<dit-domæne>/readyz
   ```
   Begge skal returnere HTTP 200.

# Efter udrulning
- Kør `./scripts/process_books.sh --validate` fra projektroden for at sikre bog-pipelinen kan forbinde til databasen.
- Hvis nye bøger skal behandles straks, følg `BOOK_UPDATES.md`.
- Gem relevante logs og opdater ændringsjournal.

# Rollback
1. Stop alle services:
   ```bash
   make -C soegemaskine down-stacks
   ```
2. Check tidligere tag eller commit ud:
   ```bash
   git checkout <forrige-tag>
   ```
3. Start igen:
   ```bash
   make -C soegemaskine up-prod
   ```
4. Bekræft `/readyz` og bog-validering som ovenfor.

# Fejlretning
- **Docker kan ikke starte containere:** kontroller fri diskplads og kør `docker system prune -f` ved behov.
- **`validate_env` rapporterer dummy-provider i produktion:** skift til `PROVIDER=openai` eller `PROVIDER=ollama` i miljøfilen.
- **TLS-relaterede fejl:** sikr at certifikatstier matcher bind mounts i `docker-compose.edge.yml` og at certifikaterne har korrekte rettigheder (typisk 600).
- **Databasemigrering krævet:** `make -C soegemaskine up-prod` genskaber automatisk tabeller; hvis du anvender migrations, kør dem før service-start.
