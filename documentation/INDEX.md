Titel: Dokumentationsindeks
Version: v1.1
Oprettet: 2025-09-04
Sidst ændret: 2025-10-07
Ejerskab: Projektvedligeholder
Formål: Hurtigt overblik over den aktuelle dokumentationsstruktur.

# Indholdsfortegnelse

## Guides (operationelle flows)
- `GUIDES/LOCAL_SETUP.md` – Lokal macOS bring-up
- `GUIDES/PRODUCTION_DEPLOY.md` – Produktionsudrulning på Linux
- `GUIDES/BOOK_UPDATES.md` – Indlæsning og vedligehold af bøger

## Core (principper & arkitektur)
- `CORE/01_ARKITEKTUR.md`
- `CORE/02_UDVIKLERGUIDE.md`
- `CORE/03_DEPLOYMENT.md`
- `CORE/04_BOG_PROCESSERING.md`
- `CORE/05_SOEGE_API_GUIDE.md`

## Reference (opslagsværk)
- `REFERENCE/KONFIGURATION.md` – Miljøvariabler og .env strategi
- `TEKNISK/CHUNKING_STRATEGIER.md`
- `TEKNISK/OPERATIONS_ENVIRONMENTS.md`
- `REFERENCER/PROVIDER_OVERSIGT.md`

## Arkiv
- `ARKIV/ARKIV_INDEX.md` – Indgang til historiske rapporter og afsluttede faser

# Målgrupper (hurtigt overblik)
| Dokumenttype | Udvikler | Drift | Support | Nye bidragsydere |
|--------------|----------|-------|---------|------------------|
| Guides | X | X | (X) | X |
| Core | X | X |  | X |
| Reference | X | X |  | (X) |
| Arkiv | (X) | (X) |  | (X) |

# Vedligeholdelsesnoter
- Opdater “Sidst ændret” ved strukturændringer eller væsentlige tilføjelser.
- Arkivfiler er skrivebeskyttede (kun append). Nye rapporter bør linkes fra `ARKIV/ARKIV_INDEX.md`.
- Nye providers eller ændringer i pipeline kræver opdatering af både `REFERENCE/KONFIGURATION.md` og relevante core-/guide-dokumenter.
