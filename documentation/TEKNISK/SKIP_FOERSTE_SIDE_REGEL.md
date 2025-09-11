# Regel: Springer Første Side Over for Multi-Page PDF'er

Oprettelsesdato: 11-09-2025  (kl. ~15:45)
Sidst ændret: 11-09-2025  (kl. ~15:45)

## Formål
Forsiden (første side) i mange historiske PDF'er indeholder typisk kun titel, årstal, dekoration eller anden metadata uden semantisk indhold. For at forbedre relevansen af embeddings til semantisk søgning springer systemet nu automatisk side 1 over, når et dokument har flere end én side.

## Gældende Regel
- Hvis PDF'en har mere end 1 side: Side 1's tekst fjernes før chunking og embedding.
- Hvis PDF'en kun har 1 side: Den bevares (ingen ændring).
- Originale sidetal bevares (dvs. første reelle indhold kan stå som side 2, 3, ...). Vi renummererer ikke.

## Implementering
Implementeret i `BookProcessingPipeline.parse_pdf_to_book_data()`:

```python
if len(pdf_pages) > 1 and 1 in pdf_pages:
    logger.debug(
        "Springer første side over for multi-page PDF (%s sider) i %s",
        len(pdf_pages),
        book_url,
    )
    del pdf_pages[1]
```

Placering: `create_embeddings/book_processing_pipeline.py`

## Testdækning
Følgende tests verificerer reglen:
- `test_parse_book_integration_word_overlap` (opdateret)
- `test_parse_book_integration_sentence_splitter` (opdateret)
- `test_skip_first_page_rule.py` (nyt) – dækker:
  - Multi-page WordOverlap
  - Multi-page SentenceSplitter
  - Single-page (må ikke fjernes)

## Påvirkede Komponenter
- Book processing pipeline (parse-fasen)
- Chunking strategier modtager nu ikke page 1 i multi-page scenarier
- Ingen ændring i database lag / schema
- Ingen ændring i søge-API (sidetal referencer stadig korrekte)

## Rationale
1. Reducerer støj i embeddings (titler / ornamenter / forside-layout)
2. Øger kvalitet af similarity matches
3. Bevarer kompatibilitet med eksisterende referencesystemer (sidetal uændret)

## Risiko & Overvejelser
| Risiko | Afdækning |
|--------|-----------|
| Forside indeholder reelt relevant tekst | Kan genovervejes senere med heuristik (fx ordtælling) |
| Brugere forstår ikke manglende side 1 i søgeresultater | Dokumenteret her + kan tilføjes i bruger-guide |
| Forskellige PDF-strukturer (fx scannede billeder) | I sådanne tilfælde vil side 1 ofte være endnu mindre semantisk |

## Mulige Fremtidige Udvidelser
- Konfigurationsflag (ENV) til at aktivere/deaktivere reglen
- Heuristisk evaluering (spring kun over hvis < N ord)
- Logging-metrik: hvor ofte side 1 droppes

## Konklusion
Reglen er nu implementeret, testet og dokumenteret. Den forventes at forbedre søgepræcision uden at skabe inkonsistens i downstream funktionalitet.
