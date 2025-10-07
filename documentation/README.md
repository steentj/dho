# DHO Semantisk Søgemaskine System

## Oversigt

DHO Semantisk Søgemaskine er et komplet system til processering og søgning i historiske dokumenter med moderne AI-teknologier. Systemet understøtter lokale og cloud-baserede embedding modeller samt avancerede chunking strategier for optimal søgeperformance.

## 🚀 **Hurtig Start**

### Forudsætninger
- Docker og Docker Compose installeret
- Mindst 8GB RAM tilgængelig
- Git for kodebase adgang

### Installation
```bash
# Hent kodebase
git clone [repository-url]
cd SlægtBib/src

# Kopiér og konfigurér miljøvariabler
cp .env.template .env
# Redigér .env efter dine behov

# Start system
# DHO Semantisk Søgemaskine – Dokumentationsoverblik

## 📚 Struktur (hurtigt overblik)

- **Guides** – operationelle trin-for-trin beskrivelser
	- `GUIDES/LOCAL_SETUP.md`
	- `GUIDES/PRODUCTION_DEPLOY.md`
	- `GUIDES/BOOK_UPDATES.md`
- **Core** – overordnede principper og arkitektur
	- `CORE/01_ARKITEKTUR.md`
	- `CORE/02_UDVIKLERGUIDE.md`
	- `CORE/03_DEPLOYMENT.md`
	- `CORE/04_BOG_PROCESSERING.md`
	- `CORE/05_SOEGE_API_GUIDE.md`
- **Reference** – opslagsværk og konfigurationer
	- `REFERENCE/KONFIGURATION.md`
	- `TEKNISK/CHUNKING_STRATEGIER.md`
	- `REFERENCER/PROVIDER_OVERSIGT.md`
- **Arkiv** – historiske rapporter og afsluttede faser (`ARKIV/`)

## � Sædvanlige indgangspunkter

- Skal du starte lokalt? → læs `GUIDES/LOCAL_SETUP.md`.
- Skal du deploye en opdatering? → følg `GUIDES/PRODUCTION_DEPLOY.md` + `CORE/03_DEPLOYMENT.md`.
- Skal du indlæse nye bøger? → se `GUIDES/BOOK_UPDATES.md` + `CORE/04_BOG_PROCESSERING.md`.
- Mangler du miljøvariabler? → tjek `REFERENCE/KONFIGURATION.md`.

## 🔗 Yderligere ressourcer

- Kodeoverblik: se repository-roden `README.md`.
- Test- og udviklingspraksis: `CORE/02_UDVIKLERGUIDE.md`.
- API-detaljer: `CORE/05_SOEGE_API_GUIDE.md`.
- Shadow- og provider-sammenligning: scripts i `/scripts` + noter i `TEKNISK/OPERATIONS_ENVIRONMENTS.md`.

---
Denne fil opdateres når struktur eller væsentlige entrypoints ændres. Sidst opdateret: 2025-10-07.
- **Vector søgning**: Semantisk søgning i embedding space
