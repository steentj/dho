Titel: Søge API Guide
Version: v1.0
Oprettet: 2025-09-04
Sidst ændret: 2025-09-04
Ejerskab: API Ansvarlig
Formål: Forklare brug af søge-API fra eksterne klienter

# 1. Formål
Hvordan man foretager semantiske søgninger programmatisk.

# 2. Basis Endpoints
| Endpoint | Metode | Beskrivelse |
|----------|--------|-------------|
| `/search` | POST | Semantisk søgning |
| `/health` | GET | Simpelt sundhedstjek |

# 3. Request / Response (eksempel)
Request:
```
POST /search
{
  "query": "slægtsoptegnelser 1600 tallet",
  "top_k": 5,
  "provider": "openai"
}
```
Response:
```
{
  "query": "slægtsoptegnelser 1600 tallet",
  "results": [
    {"score": 0.89, "book_id": 12, "page": 45, "text": "..."}
  ],
  "provider": "openai",
  "elapsed_ms": 123
}
```

# 4. Parametre
| Felt | Default | Beskrivelse |
|------|---------|-------------|
| query | (krævet) | Fritekst |
| top_k | 5 | Antal resultater |
| provider | miljø default | Embedding provider |

# 5. Curl Eksempel
```
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query":"slægtsoptegnelser 1600 tallet", "top_k":3}'
```

# 6. JavaScript Fetch
```
fetch('http://localhost:8000/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: 'slægtsoptegnelser 1600 tallet', top_k: 3 })
}).then(r => r.json()).then(console.log);
```

# 7. Python Requests
```
import requests
resp = requests.post('http://localhost:8000/search', json={
    'query': 'slægtsoptegnelser 1600 tallet',
    'top_k': 3
})
print(resp.json())
```

# 8. Fejlkoder
| Status | Betydning |
|--------|-----------|
| 400 | Ugyldig request (fx mangler query) |
| 500 | Internt problem (embedding provider / DB) |

# 9. Performance Tips
- Debounce søgninger i UI (250–400 ms)
- Cache sidste resultat for identisk query

# 10. Lokal Test
- Brug Streamlit GUI (`api_testgui`) til manuel validering.

# 11. Fremtidig Udvidelse (placeholder)
- Paginering, facets, filter på bog-ID

# 12. Referencer
- Arkitektur
- PROVIDER_OVERSIGT
