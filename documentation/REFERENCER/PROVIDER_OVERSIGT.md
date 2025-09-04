Titel: Provider Oversigt
Version: v1.0
Oprettet: 2025-09-04
Sidst ændret: 2025-09-04
Ejerskab: Arkitekturansvarlig
Formål: Samlet reference over udskiftelige providers

# 1. Oversigt
Systemet benytter Dependency Injection for nemt at skifte implementeringer.

# 2. Embedding Providers
| Navn | Brug | Fordele | Begrænsninger |
|------|------|---------|---------------|
| openai | Produktion / kvalitet | Høj kvalitet, stabilitet | Omkostning, netværkslatens |
| ollama | Lokal udvikling | Hurtig iteration, ingen ekstern afhængighed | Kvalitet varierer efter model |
| dummy | Tests | Deterministisk, hurtig | Ingen semantisk værdi |

# 3. Chunking Strategier
Se CHUNKING_STRATEGIER.

# 4. Database Provider
| Navn | Teknologi | Funktioner |
|------|-----------|------------|
| postgresql | PostgreSQL + pgvector | ACID, vector similarity søgning |

# 5. Udvidelse – Embedding Provider
1. Opret ny fil i `providers/`
2. Implementér interface (get_embedding, get_table_name, has_embeddings_for_book)
3. Registrér i factory
4. Tilføj tests (dummy inputs + integration mod DB)
5. Opdater dokumentation (dette dokument + Arkitektur)

# 6. Navngivningskonventioner
- Tabeller: `chunks_<provider>` (fx `chunks_openai`)
- Miljøvariabel: `EMBEDDING_PROVIDER`
- Strategievariabel: `CHUNK_STRATEGY`

# 7. Kendte Faldgruber
| Problem | Løsning |
|---------|---------|
| Tabelforkert ved ny provider | Sørg for unikt navn i `get_table_name` |
| Manglende dimensionstjek | Tilføj test der verificerer vektorlængde |

# 8. Referencer
- Arkitektur
- Udviklerguide
- ENV_KONFIGURATION
