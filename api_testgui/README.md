# Dansk Historie Online - Semantisk Søgning API Test GUI

En moderne, brugervenlig web-baseret GUI til test af den semantiske søge API gennem nginx endpointet. Bygget med Streamlit for cross-platform kompatibilitet og brugervenlighed.

## ✨ Funktioner

- **Modern grænseflade**: Pæn og intuitiv brugergrænseflade med dansk lokalisering
- **Avanceret søgning**: Søg i semantisk database via nginx endpoint
- **Formaterede resultater**: Resultater vises med:
  - Bogtitel og forfatter
  - Relevans score (distance-baseret)
  - Sidetal og antal tekstafsnit
  - Forhåndsvisning af indhold
- **Clickable links**: Åbn bøger direkte i din browser på to måder:
  - Åbn bog (brugervenlig URL uden sidenummer)
  - Åbn på specifik side (intern URL med sidenummer)
- **Fejlhåndtering**: Omfattende fejlhåndtering for API-forbindelsesproblemer
- **Gruppperede resultater**: Understøtter det opdaterede API response format med grupperede chunks per bog

## 🚀 Installation

### Forudsætninger
- Python 3.8+ installeret
- Docker-containere kørende (nginx på port 8080)

### Trin-for-trin installation

1. **Navigér til mappen:**
   ```bash
   cd api_testgui
   ```

2. **Installér afhængigheder:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Kontrollér at nginx containeren kører:**
   ```bash
   # Fra soegemaskine mappen
   docker-compose ps
   # Nginx skal køre på port 8080
   ```

## 📖 Brug

### Quick Start (Anbefalet)
```bash
./start_gui.sh
```
Dette script kontrollerer afhængigheder og starter GUI'en automatisk.

### Manuel start
```bash
streamlit run app.py
```

### Brug interface
1. **Åbn browser** automatisk eller gå til http://localhost:8501
2. **Indtast søgeord** i tekstfeltet øverst
3. **Tryk "🔍 Søg"** eller tryk Enter
4. **Se resultater** nedenfor med:
   - Detaljerede metadata
   - Tekstforhåndsvisning
   - Klikbare knapper til at åbne bøger

### API Information
- GUI'en kalder: `http://localhost:8080/search`
- Request format: `{"query": "din søgetekst"}`
- Response format: Liste af SearchResult objekter (se dhosearch.py)

## ⚙️ Konfiguration

### API Endpoint
Standard endpoint er konfigureret til nginx containeren:
```python
API_ENDPOINT = "http://localhost:8080/search"
```

Hvis du har brug for at ændre endpointet, rediger denne linje i `app.py`.

### Docker Setup
GUI'en forventer at nginx containeren kører på port 8080, eksponeret via `docker-compose.edge.yml` (start fx med `make -C soegemaskine up-prod`):
```yaml
# soegemaskine/docker-compose.edge.yml
ports:
   - "8080:80"  # nginx HTTP port
```

## 🖥️ Platform Support

Testet og understøttet på:
- ✅ **macOS** (primær platform)
- ✅ **Linux** (Ubuntu/Debian)  
- ✅ **Windows** (Windows 10/11)

## 🔧 Fejlfinding

### Connection Errors
```
❌ Connection Error: Kunne ikke forbinde til API serveren
```
**Løsning:**
- Kontrollér at stakken kører: `make -C soegemaskine ps-stacks`
- Genstart edge stack: `make -C soegemaskine down-stacks && make -C soegemaskine up-prod`
- Kontrollér at port 8080 er tilgængelig: `curl http://localhost:8080`

### Timeout Errors
```
⏱️ Timeout Error: API kaldet tog for lang tid
```
**Løsning:**
- Kontrollér database forbindelse i containeren
- Prøv med en kortere søgeforespørgsel
- Kontrollér system ressourcer (CPU/RAM)

### HTTP Errors
```
❌ HTTP Error: 500 - Internal Server Error
```
**Løsning:**
- Kontrollér API logs: `docker compose -f soegemaskine/docker-compose.base.yml logs searchapi`
- Kontrollér nginx logs: `docker compose -f soegemaskine/docker-compose.edge.yml logs nginx`
- Kontrollér environment variabler i `.env` filen

### Browser Link Issues
**Problem:** Links åbner ikke korrekt
**Løsning:**
- Kontrollér at du har en standard browser konfigureret
- På Linux: installer `xdg-open`
- På macOS: Links skulle virke automatisk

## 📦 Build og Distribution

### Quick Start Script
For nem opstart er der et automatisk script:
```bash
./start_gui.sh
```

### Linux Build Script
```bash
./build_linux.sh
```

### macOS Build Script  
```bash
./build_macos.sh
```

### Manual PyInstaller Build
For avancerede brugere:
```bash
pip install pyinstaller
pyinstaller --onefile --add-data "app.py:." app.py
```

### Streamlit Cloud Deployment
GUI'en kan også deployes til Streamlit Cloud for nem deling.

## 🧪 Test Eksempler

Prøv disse søgeforespørgsler:
- "første verdenskrig"
- "Danmark i 1940"
- "resistancebevægelsen"
- "besættelsen"

## 🔗 Relaterede Filer

- `dhosearch.py`: API implementation med response format
- Modulariserede compose filer i `soegemaskine/`: `docker-compose.base.yml`, `docker-compose.embeddings.yml`, `docker-compose.edge.yml`
- `nginx/default.conf`: Nginx routing konfiguration

## 📝 Udvikling

### Code Structure
```
api_testgui/
├── app.py                 # Hoved Streamlit applikation
├── requirements.txt       # Python afhængigheder
├── README.md             # Denne fil
├── start_gui.sh          # Quick start script (anbefalet)
├── build_linux.sh        # Linux build script
├── build_macos.sh        # macOS build script
└── streamlit_config.toml # Streamlit tema konfiguration
```

### Bidrag
For at bidrage til projektet:
1. Test din ændring grundigt
2. Opdater dokumentation hvis nødvendigt
3. Kontrollér at alle platforms understøttes

---

**Udviklet som del af Dansk Historie Online - Semantisk Søgning **

For spørgsmål eller problemer, kontakt projektteamet.
