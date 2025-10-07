Titel: Opdatering af Bøger
Oprettet: 2025-10-07 12:39
Sidst ændret: 2025-10-07 12:39
Ejerskab: Data Pipeline Ansvarlig

# Formål
Guiden beskriver den anbefalede arbejdsgang til at indlæse nye bøger eller reprocessere eksisterende bøger i databasen ved hjælp af `scripts/process_books.sh`.

# Forudsætninger
- `soegemaskine/.env` peger på den ønskede database og embedding-provider
- Docker stack kører allerede (`make -C soegemaskine up-local` eller `up-prod`)
- Inputfil med én PDF-URL per linje (offentligt tilgængelige filer)

# 1. Før du starter
1. Valider konfigurationen fra projektroden:
   ```bash
   ./scripts/process_books.sh --validate
   ```
   - Scriptet sikrer korrekte katalogrettigheder og kører containerens `--validate-config`.
2. Kontroller at nødvendige mapper eksisterer (`soegemaskine/book_input`, `book_output`, `book_failed`). Scriptet opretter og sikrer tilladelser automatisk, men noter hvis der er rettighedsproblemer.

# 2. Normal kørsel
1. Forbered inputfilen (eksempel):
   ```bash
   nano batches/oktober.txt
   ```
   Indhold:
   ```
   https://example.com/a.pdf
   https://example.com/b.pdf
   ```
2. Start behandling:
   ```bash
   ./scripts/process_books.sh --file batches/oktober.txt
   ```
   Scriptet kopierer filen til `soegemaskine/book_input/` og kører book-processor-containeren med de aktive miljøvariabler.
3. Overvåg status undervejs:
   ```bash
   ./scripts/process_books.sh --monitor
   ```
   - `book_output/processing_status.json` viser totale, behandlede og fejlede bøger.
   - Logfiler navngives `book_output/opret_bøger_<timestamp>.log`.

# 3. Genkørsel af fejlede bøger
- Når `book_failed/failed_books.json` indeholder poster, kan de genkøres:
  ```bash
  ./scripts/process_books.sh --retry-failed
  ```
- Scriptet genererer en midlertidig URL-liste og genbruger samme konfiguration.

# 4. Midlertidige provider- og modelskift
- Overstyr provider for en enkelt kørsel (uden at ændre `.env`):
  ```bash
  ./scripts/process_books.sh --file batches/oktober.txt --provider ollama
  ```
- Angiv modelnavn, som matches på den valgte provider:
  ```bash
  ./scripts/process_books.sh --file batches/oktober.txt --provider openai --model text-embedding-3-large
  ```
- Hvis både `--provider` og `--model` angives, sætter scriptet relevante miljøvariabler kun for den aktuelle `docker compose run`.

# 5. Efterbehandling og kontrol
- Tjek at antallet af chunks pr. bog er steget i databasen (fx via `psql` eller metrikker).
- Søg i API’en med nye termer for at bekræfte resultater (`curl http://localhost:8080/search ...`).
- Ryd eventuelt gamle inputfiler fra `soegemaskine/book_input/` når de ikke længere behøves.

# 6. Ofte sete fejl
| Fejl | Årsag | Løsning |
|------|-------|---------|
| `DATABASE_URL` mangler | `.env` er ikke synkroniseret | Kopiér korrekt miljøfil og kør `--validate` igen |
| `expected str, got list` | Skulle allerede være fikset; indikerer defekt PDF eller uprøvet pipeline | Tjek logfil for konvertering, og prøv at genkøre eller udelad PDF |
| `Connect call failed` mod DB | Forkert port eller database stoppet | Verificér at stack kører og at `POSTGRES_PORT` matcher Compose-konfigurationen (typisk 5432 internt) |
| Timeout fra provider | OpenAI/Ollama utilgængelig | Bekræft nettværk, kør `docker compose logs -f dho-ollama` eller kontroller API-nøglen |

# 7. Noter til produktion
- Kør altid kommandoerne over SSH direkte på produktionsværten.
- Brug samme inputfilnavn på værten (upload via `scp`), og gem logudskrifter for revision.
- Planlæg kørsel udenfor peak-time; containeren er sat til at stoppe efter jobben er færdigt (`restart: "no"`).
