# Lokale Embeddings med Ollama - Brugerguide

## Oversigt
SlægtBib understøtter nu lokale embeddings med Ollama og Nomic Text Embed V2 modellen. Dette eliminerer API-omkostninger og holder alle data lokalt.

## Hurtig Start

### 1. Opsætning
```bash
# Kopiér miljøvariabler
cp .env.template .env

# Redigér .env filen:
PROVIDER=ollama
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=nomic-embed-text
```

### 2. Start Services
```bash
cd soegemaskine
docker-compose --profile embeddings up -d
```

### 3. Installér Model
```bash
# Vent på at Ollama starter, derefter:
../scripts/setup_ollama.sh
```

### 4. Verificér Installation
```bash
python ../scripts/test_ollama_setup.py
```

## Brug

### Processér Bøger
```bash
# Placer PDF filer i book_input/
docker-compose --profile book-processing up book-processor
```

### Søg i Bøger
Brug den eksisterende søge-API - den håndterer automatisk både OpenAI og Ollama embeddings.

## Tekniske Detaljer

### Fordele ved Ollama
- **Gratis**: Ingen API-omkostninger
- **Privat**: Alle data forbliver lokale
- **Offline**: Fungerer uden internetforbindelse
- **Hurtigt**: 768-dimensionelle embeddings

### Hardware Krav
- **RAM**: Minimum 4GB til Ollama container
- **Disk**: ~2GB til Nomic model
- **CPU**: Embeddings genereres via CPU (GPU ikke påkrævet)

### Database Schema
- **chunks_nomic**: Nye 768-dimensionelle embeddings
- **chunks**: Eksisterende OpenAI embeddings (1536 dim)
- **Kompatibilitet**: Begge tabeller understøttes samtidigt

## Fejlfinding

### Ollama starter ikke
```bash
# Check container status
docker ps | grep ollama

# Check logs
docker logs dho-ollama
```

### Model download fejler
```bash
# Manuel model download
docker exec dho-ollama ollama pull nomic-embed-text
```

### Embeddings genereres ikke
```bash
# Test Ollama API direkte
curl http://localhost:11434/api/health
```

### Performance problemer
- Øg Ollama container memory til 6-8GB
- Kontrollér CPU brug under processering

## Migration fra OpenAI

### Gradvis Migration
1. Start med `PROVIDER=ollama` for nye bøger
2. Eksisterende OpenAI embeddings forbliver funktionelle
3. Valgfrit: Regenerér gamle bøger med Ollama

### Sammenligning
| Feature | OpenAI | Ollama |
|---------|--------|---------|
| Omkostning | $$ | Gratis |
| Privatliv | Eksttern API | Lokalt |
| Dimensioner | 1536 | 768 |
| Hastighed | Hurtig | Moderat |
| Kvalitet | Høj | God |

## Support
Se `PRD_LOCAL_EMBEDDINGS.md` for tekniske detaljer eller kontakt udviklingsholdet.
