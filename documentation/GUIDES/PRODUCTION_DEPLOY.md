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
3. Overfør den opdaterede fil sikkert til serveren, fx:
   ```bash
   scp env/production.env bruger@server:/opt/dho/env/production.env
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
3. Valider miljøvariablerne med streng mode:
   ```bash
   python scripts/validate_env.py --file /opt/dho/env/production.env --strict
   ```
   Løs alle fejl før du fortsætter.
4. Kopiér miljøfilen til søgemaskine-servicen (ikke check den ind):
   ```bash
   cp /opt/dho/env/production.env soegemaskine/.env
   ```
5. Træk opdaterede containere og start hele stacken (postgres + embeddings + edge):
   ```bash
   make -C soegemaskine up-prod
   ```
   - Kommandoen kombinerer `docker-compose.base.yml`, `docker-compose.embeddings.yml` og `docker-compose.edge.yml`.
   - Ved større kodeændringer: `docker compose --profile embeddings build searchapi book-processor` inde fra `soegemaskine/` før `make up-prod`.
6. Overvåg loggene i de første minutter:
   ```bash
   docker compose -f soegemaskine/docker-compose.base.yml logs -f searchapi
   docker compose -f soegemaskine/docker-compose.embeddings.yml logs -f book-processor
   ```
7. Sundhedstjek:
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
