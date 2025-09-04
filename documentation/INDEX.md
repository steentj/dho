Titel: Dokumentationsindeks
Version: v1.0
Oprettet: 2025-09-04
Sidst ændret: 2025-09-04
Ejerskab: Projektvedligeholder
Formål: Hurtigt overblik over dokumentationssættet

# Indeks

## CORE
- 01_ARKITEKTUR.md – Overblik over systemarkitektur
- 02_UDVIKLERGUIDE.md – Arbejdsgange, test og kvalitet
- 03_DEPLOYMENT.md – Udrulning lokalt, WSL og produktion
- 04_BOG_PROCESSERING.md – Indlæsning og behandling af bøger
- 05_SOEGE_API_GUIDE.md – Anvendelse af søge-API

## REFERENCER
- ENV_KONFIGURATION.md – Miljøvariabler og .env strategi
- CHUNKING_STRATEGIER.md – Reference for chunking strategier
- PROVIDER_OVERSIGT.md – Embedding / DB / Chunking providers

## ARKIV
- ARKIV_INDEX.md – Historiske filer og refactoringsrapporter

## Målgruppe Matrix (kort)
| Dokument | Udvikler | IT-Drift | Support | Ny Bidragsyder |
|----------|----------|----------|---------|----------------|
| 01 Arkitektur | X | X | (X) | X |
| 02 Udviklerguide | X | (X) |  | X |
| 03 Deployment | (X) | X | X |  |
| 04 Bog Processering | X | X | X | X |
| 05 Søge API | X | (X) | X | X |
| Referencer | X | X |  | (X) |
| Arkiv | (X) | (X) |  | (X) |

Parentes = sekundær relevans.

## Vedligeholdelsespolitik
- Ændringer i CORE kræver opdatering af Sidst ændret.
- Arkivfiler ændres ikke retroaktivt – kun tilføjelser.
- Nye providers kræver opdatering af PROVIDER_OVERSIGT + evt. Arkitektur.
