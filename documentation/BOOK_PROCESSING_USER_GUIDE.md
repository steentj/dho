# Brugervejledning til Bogbehandling

## Docker Brug - Ingen Container Terminal Påkrævet

**Vigtigt**: Du kører alt fra din **værtsmaskine terminal** - du behøver aldrig at gå ind i Docker container terminaler. Systemet håndterer automatisk alle Docker operationer for dig.

## Hurtig Start

### Forudsætninger
1. Sørg for at Docker og Docker Compose er installeret
2. Naviger til projektmappen:
   ```bash
   cd /sti/til/SlægtBib/src
   ```

### 1. Valider Konfiguration
Først skal du sikre dig, at dit miljø er korrekt konfigureret:

```bash
./scripts/process_books.sh --validate
```

**Hvad sker der**: Denne kommando starter automatisk en midlertidig Docker container, validerer din `.env` fil, og fjerner derefter containeren. Du forbliver i din værtsmaskine terminal hele tiden.

### 2. Opret Bogliste  
Opret en tekstfil **på din værtsmaskine** med én URL per linje:

```bash
# Opret filen hvor som helst på din værtsmaskine
nano mine_boeger.txt
```

Indholdsformat (samme som eksisterende opret_bøger.py):
```
https://example.com/bog1.pdf
https://example.com/bog2.pdf
https://example.com/bog3.pdf
```

### 3. Behandl Bøger
Alle kommandoer køres fra din **værtsmaskine terminal**:

```bash
# Behandl nye bøger (køres automatisk i Docker)
./scripts/process_books.sh --file mine_boeger.txt

# Overvåg fremgang (i en anden værtsmaskine terminal - ingen Docker terminal)
./scripts/process_books.sh --monitor

# Prøv fejlede bøger igen (køres automatisk i Docker)  
./scripts/process_books.sh --retry-failed
```

**Hvad sker der**: Hver kommando automatisk:
1. Starter en Docker container med din bogbehandler
2. Monterer dine filer ind i containeren 
3. Kører behandlingen
4. Gemmer resultater tilbage til din værtsmaskine
5. Fjerner den midlertidige container

## Sådan Fungerer Det

Dette system indpakker den eksisterende `opret_bøger.py` funktionalitet uden at ændre den:

- ✅ **Samme chunking algoritme**: Sætningsbaseret opdeling med metadata inklusion (`##{titel}##chunk`)
- ✅ **Samme samtidige behandling**: 5 bøger behandles samtidigt ved hjælp af semaphore  
- ✅ **Samme database operationer**: Bruger eksisterende forbindelsespulje og forespørgsler
- ✅ **Samme embedding oprettelse**: Bruger eksisterende OpenAI integration med konfigurerbare modeller
- ✅ **Tilføjet**: Fremgangsovervågning, fejlhåndtering, containerisering

## Miljøvariabler

Systemet bruger de samme miljøvariabler som `opret_bøger.py`. Tilføj disse til din `.env` fil:

```bash
# Database Konfiguration
POSTGRES_DB=dit_database_navn
POSTGRES_USER=dit_brugernavn
POSTGRES_PASSWORD=din_adgangskode
POSTGRES_HOST=postgres  # Docker service navn

# Embedding Konfiguration
OPENAI_API_KEY=din_openai_api_noegle
OPENAI_MODEL=text-embedding-ada-002
PROVIDER=openai

# Behandlings Konfiguration
CHUNK_SIZE=500

# Logging Konfiguration
LOG_DIR=./logs  # Mappe til log filer - begge scripts vil bruge denne
```

### Miljøvariabel Detaljer

- **POSTGRES_HOST**: Sæt til `postgres` når du kører i Docker, eller din database host til lokal udvikling
- **OPENAI_MODEL**: Den embedding model der skal bruges (f.eks. `text-embedding-ada-002`, `text-embedding-3-small`)
- **PROVIDER**: Sæt til `openai` til produktion, eller `dummy` til test
- **CHUNK_SIZE**: Maksimale tokens per tekst chunk (standard: 500)
- **LOG_DIR**: Mappe hvor log filer vil blive oprettet (standard: nuværende mappe). Både `opret_bøger.py` og `book_processor_wrapper.py` vil skrive logs til denne placering

## Logging Konfiguration

Bogbehandlingssystemet bruger en delt logging konfiguration for at sikre konsistent logging på tværs af alle moduler.

### Miljøvariabler til Logging
- `LOG_DIR`: Mappe hvor log filer vil blive oprettet (standard: nuværende mappe)

### Log Fil Format
- Log filer navngives med tidsstempel: `opret_bøger_YYYY-MM-DD_HH-MM-SS.log`
- Både `opret_bøger.py` og `book_processor_wrapper.py` bruger samme logging konfiguration
- Logs skrives til både fil og konsol samtidigt

### Log Niveauer
- **Konsol**: INFO og højere
- **Fil**: INFO og højere  
- **Eksterne biblioteker** (openai, aiohttp): WARNING og højere (for at reducere støj)

### Delt Logging Implementation
Begge scripts bruger nu den delte `logging_config.setup_logging()` funktion:

```python
from logging_config import setup_logging

# Opsæt logging (vil bruge LOG_DIR env var eller nuværende mappe)
log_file = setup_logging()

# Eller specificer brugerdefineret mappe
log_file = setup_logging(log_dir="/sti/til/logs")
```

### Log Output Format
Alle log indgange følger dette konsistente format:
```
2025-06-05 14:22:35,123 - INFO - Behandling startet
2025-06-05 14:22:36,456 - WARNING - Forbindelse timeout, prøver igen...
2025-06-05 14:22:37,789 - ERROR - Fejl ved behandling af bog: example.pdf
2025-06-05 14:22:38,012 - INFO - ✓ Successfuldt behandlet: https://example.com/bog1.pdf
```

### Docker Logging
Når du bruger Docker, gemmes logs automatisk til `book_output/` mappen på din værtsmaskine:

```bash
# Vis seneste log fil
ls -t soegemaskine/book_output/opret_bøger_*.log | head -1 | xargs cat

# Følg realtids behandling (i en anden terminal)
tail -f soegemaskine/book_output/$(ls -t soegemaskine/book_output/opret_bøger_*.log | head -1)
```

## Kommando Reference

### Behandl Bøger fra Fil
```bash
./scripts/process_books.sh --file boeger.txt
```

Behandler alle URL'er listet i den specificerede fil ved hjælp af den eksisterende opret_bøger.py logik.

### Overvåg Fremgang
```bash
./scripts/process_books.sh --monitor
```

Viser:
- Nuværende behandlingsstatus (kører, afsluttet, fejl)
- Antal bøger behandlet vs total
- Antal fejlede bøger
- Seneste log indgange
- Fejlede bøger antal og retry instruktioner

### Prøv Fejlede Bøger Igen
```bash
./scripts/process_books.sh --retry-failed
```

Prøver automatisk alle bøger igen, der fejlede i tidligere kørsler. Fejlede bøger gemmes i `book_failed/failed_books.json`.

### Valider Konfiguration
```bash
./scripts/process_books.sh --validate
```

Tjekker at alle påkrævede miljøvariabler er sat og viser nuværende konfiguration.

## Fil Placeringer

Når du kører bogbehandleren, organiseres filer som følger:

```
soegemaskine/
├── book_input/           # Input filer (dine bog URL lister)
├── book_output/          # Behandlings logs og status
│   ├── processing_status.json
│   └── opret_bøger_*.log
└── book_failed/          # Fejlede bøger til retry
    └── failed_books.json
```

## Status Fil Format

`book_output/processing_status.json` filen indeholder:

```json
{
  "status": "afsluttet",
  "total_boeger": 10,
  "behandlet": 8,
  "fejlet": 2,
  "sidst_opdateret": "2025-06-04T12:30:00",
  "embedding_model": "text-embedding-ada-002",
  "udbyder": "openai"
}
```

## Fejlede Bøger Format

`book_failed/failed_books.json` filen indeholder:

```json
[
  {
    "url": "https://example.com/problematisk-bog.pdf",
    "error": "HTTP 404: Not Found",
    "timestamp": "2025-06-04T12:25:00"
  }
]
```

## Fejlfinding

### Almindelige Problemer

**"Manglende påkrævede miljøvariabler"**
- Sørg for at din `.env` fil indeholder alle påkrævede variabler
- Kør `./scripts/process_books.sh --validate` for at tjekke

**"Input fil ikke fundet"**
- Verificer at filstien er korrekt
- Sørg for at filen eksisterer og er læsbar

**"Database forbindelse fejlede"**
- Tjek at PostgreSQL containeren kører: `docker-compose ps`
- Verificer database legitimationsoplysninger i `.env` fil
- Sørg for at databasen eksisterer og har pgvector udvidelse

**"OpenAI API fejl"**
- Verificer at `OPENAI_API_KEY` er sat korrekt
- Tjek API kvote og faktureringsstatus
- Overvej at bruge en anden model i `OPENAI_MODEL`

**"Log filer ikke fundet eller forkert placering"**
- Tjek at `LOG_DIR` miljøvariablen er sat korrekt
- Sørg for at log mappen eksisterer og er skrivbar
- Både `opret_bøger.py` og `book_processor_wrapper.py` vil oprette logs samme sted når `LOG_DIR` er sat

### Vis Detaljerede Logs

```bash
# Vis seneste log fil
ls -t book_output/opret_bøger_*.log | head -1 | xargs cat

# Følg realtids behandling (i en anden terminal)
tail -f book_output/opret_bøger_*.log
```

### Manuel Oprydning

```bash
# Ryd alle behandlingsdata (start forfra)
rm -rf book_output/* book_failed/*

# Ryd kun fejlede bøger (for at prøve alt igen)
rm -f book_failed/failed_books.json
```

## Performance Noter

- **Samtidig Behandling**: 5 bøger behandles samtidigt (samme som originale opret_bøger.py)
- **Database Forbindelser**: Bruger forbindelsespulje til effektiv database adgang
- **Hukommelsesbrug**: Hukommelsesforbrug skalerer med samtidige bøger og chunk størrelse
- **Rate Limiting**: OpenAI API kald begrænses naturligt af samtidig bog grænse

## Integration med Eksisterende System

Denne bogbehandler integrerer problemfrit med dit eksisterende søgesystem:

1. **Database Skema**: Bruger samme tabeller og struktur som den originale opret_bøger.py
2. **Embedding Format**: Opretter embeddings i samme format som søge API'et forventer
3. **Metadata**: Bevarer samme metadata struktur (`##{titel}##chunk`) til søgefunktionalitet
4. **Vector Lagring**: Gemmer vektorer i samme pgvector format brugt af søgesystemet

## Eksempler

### Behandl en Lille Test Batch
```bash
# Opret test fil
echo -e "https://example.com/bog1.pdf\nhttps://example.com/bog2.pdf" > test_boeger.txt

# Behandl med overvågning
./scripts/process_books.sh --file test_boeger.txt

# Tjek resultater
./scripts/process_books.sh --monitor
```

### Håndter Store Batches
```bash
# Behandl stor batch (hundreder af bøger)
./scripts/process_books.sh --file stor_bog_liste.txt

# Overvåg i separat terminal
watch './scripts/process_books.sh --monitor'

# Hvis nogle fejler, prøv dem igen
./scripts/process_books.sh --retry-failed
```

## Fordele

- ✅ **Ingen kode ændringer** til den afprøvede opret_bøger.py logik
- ✅ **Samme ydeevne** - identisk samtidig behandling (5 bøger ad gangen)
- ✅ **Samme kvalitet** - identisk chunking og embedding oprettelse  
- ✅ **Tilføjet overvågning** - spor fremgang og fejl i realtid
- ✅ **Tilføjet genoprettelse** - prøv fejlede bøger igen nemt uden manuel indgriben
- ✅ **Tilføjet portabilitet** - virker på lokal Mac og fjerne Linux servere
- ✅ **Brugervenlig** - simpel kommandolinje interface der ikke kræver teknisk viden
- ✅ **Produktionsklar** - containeriseret med ordentlig logging og fejlhåndtering

## Docker Workflow Forklaret

### Hvordan Docker Integration Virker

Du arbejder udelukkende fra din **værtsmaskine** (Mac/Linux terminal). Her er hvad der sker bag kulisserne:

```
Din Værtsmaskine                    Docker Container
    ┌─────────────────┐                ┌──────────────────┐
    │ 1. Du kører:    │                │                  │
    │ ./scripts/      │                │                  │
    │ process_books.sh│───────────────▶│ 2. Container     │
    │                 │                │    starter       │
    │                 │                │    automatisk    │
    └─────────────────┘                └──────────────────┘
           │                                      │
           │                                      ▼
    ┌─────────────────┐                ┌──────────────────┐
    │ 4. Resultater   │                │ 3. Behandling    │
    │    gemt til     │◀───────────────│    sker i        │
    │    værtsmapper  │                │    container     │
    │                 │                │                  │
    └─────────────────┘                └──────────────────┘
```

### Fil Placeringer på Din Værtsmaskine

Alle filer forbliver på din værtsmaskine i disse placeringer:

```bash
/sti/til/SlægtBib/src/
├── mine_boeger.txt                 # Din input fil (du opretter denne)
├── scripts/process_books.sh        # Scriptet du kører
└── soegemaskine/
    ├── book_input/                 # Input filer (auto-oprettet)
    ├── book_output/                # Resultater du kan se
    │   ├── processing_status.json  # Status fil
    │   └── opret_bøger_*.log      # Log filer
    └── book_failed/                # Fejlede bøger
        └── failed_books.json       # Fejlede bøger liste
```

**Vigtigt**: Du kan se, redigere og administrere alle disse filer direkte fra din værtsmaskine - ingen grund til at tilgå Docker containere.

## Trin-for-Trin Docker Brug

### Komplet Workflow Eksempel

```bash
# 1. Naviger til projektet (på din værtsmaskine)
cd /Users/steen/Library/Mobile\ Documents/com~apple~CloudDocs/Projekter/SlægtBib/src

# 2. Tjek at Docker kører
docker --version
docker-compose --version

# 3. Valider konfiguration (starter container midlertidigt automatisk)
./scripts/process_books.sh --validate

# 4. Opret din bogliste (på værtsmaskinen)
echo -e "https://example.com/bog1.pdf\nhttps://example.com/bog2.pdf" > mine_boeger.txt

# 5. Behandl bøger (starter container automatisk, behandler, derefter stopper)
./scripts/process_books.sh --file mine_boeger.txt

# 6. Tjek resultater (filer er på din værtsmaskine)
./scripts/process_books.sh --monitor

# 7. Hvis nødvendigt, prøv fejl igen (starter container automatisk igen)
./scripts/process_books.sh --retry-failed
```

### Hvad Du Vil Se Under Behandling

Når du kører `./scripts/process_books.sh --file mine_boeger.txt`:

```
=== Behandler Bøger ===
Input fil: mine_boeger.txt
Bruger eksisterende opret_bøger.py logik med overvågning...

[+] Building 0.0s (0/0)                                    
[+] Running 1/0
 ✔ Container dho-book-processor  Created                   0.0s
Attaching to dho-book-processor
dho-book-processor  | 2025-06-04 12:30:00 - INFO - Behandler 2 bøger ved hjælp af eksisterende opret_bøger logik
dho-book-processor  | 2025-06-04 12:30:15 - INFO - ✓ Successfuldt behandlet: https://example.com/bog1.pdf
dho-book-processor  | 2025-06-04 12:30:30 - INFO - ✓ Successfuldt behandlet: https://example.com/bog2.pdf
dho-book-processor  | 2025-06-04 12:30:31 - INFO - Behandling afsluttet: 2 vellykket, 0 fejlet
[+] Container dho-book-processor  Exited (0)

=== Behandling Afsluttet ===
Tjek resultater:
  Status: ./scripts/process_books.sh --monitor
```

### Overvågning i Realtid

Åbn en **anden terminal på din værtsmaskine** og kør:

```bash
# Dette viser status uden at starte containere
./scripts/process_books.sh --monitor
```

Output:
```
=== Nuværende Status ===
{
  "status": "kører",
  "total_boeger": 10,
  "behandlet": 3,
  "fejlet": 0,
  "sidst_opdateret": "2025-06-04T12:30:00",
  "embedding_model": "text-embedding-ada-002",
  "udbyder": "openai"
}

=== Seneste Logs ===
2025-06-04 12:30:00 - INFO - ✓ Successfuldt behandlet: https://example.com/bog1.pdf
2025-06-04 12:30:15 - INFO - Behandler bog 4/10: https://example.com/bog4.pdf
```

## Docker Kommando Reference

### Alle Kommandoer Køres fra Værtsmaskine Terminal

**Kør aldrig disse kommandoer inde i Docker containere** - de håndterer automatisk containere for dig:

| Kommando | Hvad Den Gør | Docker Adfærd |
|---------|-------------|-----------------|
| `./scripts/process_books.sh --validate` | Tjek konfiguration | Starter container → validerer → stopper container |
| `./scripts/process_books.sh --file boeger.txt` | Behandl bøger | Starter container → behandler → stopper container |
| `./scripts/process_books.sh --monitor` | Vis status | **Ingen container** - læser filer fra værtsmaskine |
| `./scripts/process_books.sh --retry-failed` | Prøv fejl igen | Starter container → prøver igen → stopper container |

### Manuelle Docker Kommandoer (Hvis Nødvendigt)

Hvis du har brug for at interagere manuelt med Docker (sjældent nødvendigt):

```bash
# Tjek om containere kører
docker-compose ps

# Se container logs (kun under behandling)
docker-compose logs book-processor

# Stop alle containere hvis nødvendigt
docker-compose down

# Genopbyg container efter kode ændringer
docker-compose build book-processor
```

### Fejlfinding af Docker Problemer

**"docker-compose kommando ikke fundet"**
```bash
# Installer docker-compose eller brug nyere syntaks
docker compose --version  # Prøv dette i stedet
```

**"Tilladelse nægtet"**
```bash
# Gør script eksekverbart
chmod +x ./scripts/process_books.sh
```

**"Ingen sådan fil eller mappe"**
```bash
# Sørg for at du er i den korrekte mappe
cd /sti/til/SlægtBib/src
pwd  # Skulle vise projektmappen
```

**Container vil ikke starte**
```bash
# Tjek at Docker kører
docker --version
docker-compose --version

# Tjek at din .env fil eksisterer
ls -la soegemaskine/.env

# Valider konfiguration
./scripts/process_books.sh --validate
```

## Fjern Linux Server Brug

### Samme Kommandoer, Forskellig Placering

På en fjern Linux server er workflow'et identisk:

```bash
# SSH til din server først
ssh bruger@din-server.com

# Naviger til projekt
cd /sti/til/SlægtBib/src

# Brug præcis samme kommandoer
./scripts/process_books.sh --validate
./scripts/process_books.sh --file boeger.txt
./scripts/process_books.sh --monitor
```

### Fil Overførsel til Fjern Server

```bash
# Kopier bogliste til server
scp mine_boeger.txt bruger@server:/sti/til/SlægtBib/src/

# Behandl på server
ssh bruger@server "cd /sti/til/SlægtBib/src && ./scripts/process_books.sh --file mine_boeger.txt"

# Kopier resultater tilbage (valgfrit)
scp bruger@server:/sti/til/SlægtBib/src/soegemaskine/book_output/* ./resultater/
```

## Nøgle Fordele ved Denne Docker Tilgang

✅ **Ingen container terminal adgang nødvendig** - alt styres fra værtsmaskinen

✅ **Automatisk container håndtering** - containere starter og stopper efter behov

✅ **Fil persistens** - alle filer forbliver på din værtsmaskine

✅ **Krydsplatform** - identiske kommandoer på Mac og Linux

✅ **Ressource effektiv** - containere kører kun under behandling

✅ **Let overvågning** - se filer og status uden Docker viden
