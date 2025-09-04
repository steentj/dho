Titel: Chunking Strategier
Version: v1.0
Oprettet: 2025-09-04
Sidst ændret: 2025-09-04
Ejerskab: NLP Ansvarlig
Formål: Opslagsreference for tilgængelige chunking strategier

# 1. Oversigt
Strategier opdeler rå tekst til mindre enheder for embedding.

# 2. Strategier
## sentence_splitter
- Segmenterer efter sætningsgrænser.
- Tilføjer titel som præfiks (`##<title>##`).
- Bevarer kontekst og læsbarhed.
- Anbefalet ved semantisk søgning i fortællende tekst.

## word_overlap
- Faste 400 ord pr. chunk med 50 ord overlap.
- Ingen titelpræfiks.
- Mere deterministisk størrelse – god til meget lange værker.

# 3. Valgskriterier
| Kriterium | sentence_splitter | word_overlap |
|-----------|------------------|--------------|
| Kontekstbevarelse | Høj | Medium |
| Ensartet chunk-size | Lav | Høj |
| Læselighed | Høj | Medium |
| Hastighed | Medium | Høj |

# 4. Konfiguration
- Styres af miljøvariabel `CHUNK_STRATEGY`.

# 5. Udvidelse
1. Implementér ny klasse i `chunking.py`.
2. Registrér i fabrik.
3. Tilføj tests (unit + integration)
4. Opdater dette dokument + PROVIDER_OVERSIGT

# 6. Kendte Faldgruber
- For lang titel kan forstørre tokens – trim inden præfiks.
- Overdreven overlap øger embedding omkostning.

# 7. Referencer
- Arkitektur
- Udviklerguide
