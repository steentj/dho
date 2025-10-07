Titel: Udviklerguide
Version: v1.0
Oprettet: 2025-09-04
Sidst ændret: 2025-09-04
Ejerskab: Tech Lead
Formål: Ensret udviklingspraksis, test og kvalitetskontrol

# 1. Formål & Målgruppe
For udviklere og bidragsydere der ændrer eller udvider kodebasen.

# 2. Arbejdscyklus
1. Opret lille feature branch
2. Skriv/justér tests (unit/integration)
3. Implementér minimal kode
4. Kør fuld test suite
5. Refaktorer og dokumentér
6. PR med checkliste

# 3. Miljøhåndtering
- Brug altid container-stacken (`make -C soegemaskine up-local`) til end-to-end tests; supplér med lokal venv ved behov.
- Isolér hemmeligheder i subsystem-specifik `.env` (se `REFERENCE/KONFIGURATION.md`).
- Del aldrig faktiske nøgler; brug `.env.template` eller `env/<miljø>.env` kopier.

# 4. .env og Konfiguration
- Tests må ikke læse rigtige `.env`: mock `load_dotenv()`.
- Brug `with patch.dict(os.environ, {...}, clear=True)` for total isolation.
- Se `REFERENCE/KONFIGURATION.md` for variabeloversigt og inline eksempler.

# 5. Providers – ændringscheckliste
Når du ændrer embedding/chunking/database:
- [ ] Impact analyse (batch + søgning)
- [ ] Opdater tests for begge veje
- [ ] Kør fuld suite (ingen delvise godkendelser)
- [ ] Test manuelt med Streamlit GUI
- [ ] Dokumentér ændring i PROVIDER_OVERSIGT

# 6. Testtyper
| Type | Fokus | Eksempler |
|------|-------|-----------|
| Unit | Små enheder, mock alt eksternt | chunking strategi output |
| Integration | Samspil mellem moduler | DB + embedding dummy |
| End-to-end (valgfrit) | Hel pipeline | Bog → søgning |

Kørsel:
```
python -m pytest --cov --cov-fail-under=80
```

Isolation:
```
with patch("dotenv.load_dotenv"):
    with patch.dict(os.environ, {...}, clear=True):
        ...
```

# 7. Kvalitetsporte
- Alle tests grønne.
- Coverage ≥ 80% (kritiske stier dækket)
- Ingen nye linter-fejl.
- Ingen TODO-kommentarer i submitted kode uden opgave.

# 8. Kendte faldgruber
| Problem | Løsning |
|---------|---------|
| chunk_text som liste | Sikr streng + defensiv join (allerede implementeret) |
| Manglende miljøisolation i test | Brug clear=True og mock load_dotenv |
| Provider navnekollision | Konsistent tabelforfiks + test |
| Concurrency issues | Begræns delt mutable state, log race conditions |

# 9. PR Tjekliste (kort)
- [ ] Nye tests tilføjet/justeret
- [ ] Fuld suite kørt lokalt
- [ ] Dokumentation opdateret (CORE/eller REFERENCER)
- [ ] Ingen hårdkodede hemmeligheder
- [ ] Ingen død/ubrugt kode

# 10. Mini Eksempel (unit test skeleton)
```
def test_sentence_splitter_basic():
    text = "A. B. C."
    strategy = SentenceSplitterStrategy(max_length=400)
    chunks = strategy.chunk(text, title="T")
    assert len(chunks) >= 1
```

# 11. Referencer
- Arkitektur (overblik)
- `REFERENCE/KONFIGURATION.md`
- `REFERENCER/PROVIDER_OVERSIGT.md`
