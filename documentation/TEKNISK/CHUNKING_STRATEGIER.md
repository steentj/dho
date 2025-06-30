# Chunking Strategier Guide

## Oversigt

DHO Semantisk Søgemaskine understøtter flere tekst chunking strategier til optimal behandling af forskellige dokumenttyper. Denne guide forklarer hver strategi og hvornår de skal bruges.

## 🧩 **Chunking Koncepter**

### Hvad er Chunking?
Chunking opdeler lange dokumenter i mindre, håndterbare tekststykker der kan:
- Generere meningsfulde embeddings
- Passe inden for model token limits
- Bevare kontekst og sammenhæng
- Optimere søgeperformance

### Vigtige Parametre
- **Chunk Size**: Maksimum tokens per chunk
- **Overlap**: Delte ord mellem tilstødende chunks
- **Boundary Respect**: Om chunks respekterer sætnings-/afsnitsgrænser
- **Title Injection**: Om bog titel tilføjes til chunks

## 📝 **Tilgængelige Strategier**

### 1. Sentence Splitter (Standard)

#### Konfiguration
```bash
CHUNKING_STRATEGY=sentence_splitter
CHUNK_SIZE=500  # Respekteres
```

#### Funktionalitet
- **Opdeling**: Splitter tekst ved sætningsgrænser
- **Token Limit**: Respekterer CHUNK_SIZE parameter
- **Titel Prefiks**: Tilføjer bog titel til starten af hver chunk
- **Boundary Respect**: Ja - splitter aldrig midt i sætning
- **Cross-Page**: Håndterer tekst på tværs af sider

#### Algoritme
```python
1. Udvind bog titel fra metadata
2. For hver side:
   a. Opdel tekst i sætninger
   b. Kombiner sætninger til chunks
   c. Tilføj titel prefiks
   d. Respektér max_tokens limit
3. Håndtér cross-page chunks
4. Returner titel-præfiksede chunks
```

#### Fordele
- **Bevarar sprog flow**: Chunks slutter ved naturlige pauser
- **Høj søgekvalitet**: Titel hjælper med relevans
- **Fleksibel størrelse**: Tilpasser til CHUNK_SIZE
- **God til korte/mellemlange dokumenter**

#### Ulemper
- **Variabel chunk størrelse**: Kan give uens performance
- **Titel overhead**: Bruger tokens på titel i hver chunk

#### Bedst til
- Generel dokumentbehandling
- Søgekvalitet prioriteret
- Dokumenter med god sætningsstruktur
- Når titel kontekst er værdifuld

#### Eksempel Output
```
Input: "Dette er første sætning. Dette er anden sætning. Dette er tredje sætning."
Titel: "Min Test Bog"
Chunk Size: 15 tokens

Output Chunk:
"Min Test Bog: Dette er første sætning. Dette er anden sætning."
```

### 2. Word Overlap

#### Konfiguration
```bash
CHUNKING_STRATEGY=word_overlap
CHUNK_SIZE=400  # Ignoreres - bruger fast størrelse
```

#### Funktionalitet
- **Opdeling**: Fast 400-ord chunks med 50-ord overlap
- **Token Limit**: Ignorerer CHUNK_SIZE parameter
- **Titel Prefiks**: Ingen - kun ren tekst
- **Overlap**: 50 ord deles mellem tilstødende chunks
- **Cross-Page**: Fuld support på tværs af sider

#### Algoritme
```python
1. Kombiner al tekst fra alle sider
2. Opdel i individuelle ord
3. Opret 400-ord chunks med 50-ord overlap:
   - Chunk 1: ord 1-400
   - Chunk 2: ord 351-750 (overlap: 351-400)
   - Chunk 3: ord 701-1100 (overlap: 701-750)
4. Returner chunks uden titel prefiks
```

#### Fordele
- **Konsistent størrelse**: Alle chunks er samme størrelse
- **Kontekst bevarelse**: Overlap bevarer sammenhæng
- **Optimal for ML**: Ensartede input til embedding models
- **Cross-page seamless**: Ingen tab ved sidegrænser

#### Ulemper
- **Ignorerer CHUNK_SIZE**: Kan ikke tilpasse størrelse
- **Kan splitte midt i sætning**: Mindre respekt for sprog boundaries
- **Ingen titel kontekst**: Chunks mangler bog identificering

#### Bedst til
- Lange dokumenter
- Når overlap er kritisk
- Machine learning training
- Når konsistent chunk størrelse er vigtig
- Cross-document analyse

#### Eksempel Output
```
Input: 500 ord tekst
Fast Configuration: 400 ord chunks, 50 ord overlap

Chunk 1: ord 1-400
Chunk 2: ord 351-500 (overlap med chunk 1: ord 351-400)
```

## ⚙️ **Konfiguration og Tuning**

### Chunk Size Optimering

#### Små Chunks (200-300 tokens)
```bash
CHUNK_SIZE=250
```
- **Fordele**: Præcise matches, hurtig processering
- **Ulemper**: Mangler kontekst, flere chunks per dokument
- **Bedst til**: Korte dokumenter, faktuelle spørgsmål

#### Medium Chunks (400-600 tokens)
```bash
CHUNK_SIZE=500
```
- **Fordele**: God balance mellem præcision og kontekst
- **Ulemper**: Moderat processering tid
- **Bedst til**: Generel brug, de fleste dokumenttyper

#### Store Chunks (700-1000 tokens)
```bash
CHUNK_SIZE=800
```
- **Fordele**: Maksimal kontekst, færre chunks
- **Ulemper**: Mindre præcise matches, længere processering
- **Bedst til**: Komplekse dokumenter, kontekst-sensitive søgninger

### Provider-Specifik Optimering

#### OpenAI Optimering
```bash
# OpenAI text-embedding-3-small: 8191 token limit
CHUNKING_STRATEGY=sentence_splitter
CHUNK_SIZE=500  # Sikker margin under limit
```

#### Ollama Optimering
```bash
# Nomic-embed-text: 2048 token limit
CHUNKING_STRATEGY=sentence_splitter
CHUNK_SIZE=400  # Sikker margin
```

### Performance Tuning

#### Høj Throughput
```bash
CHUNKING_STRATEGY=word_overlap  # Konsistent processering
CHUNK_SIZE=400  # Ignoreres men sat for reference
```

#### Høj Kvalitet
```bash
CHUNKING_STRATEGY=sentence_splitter  # Respekterer sprog struktur
CHUNK_SIZE=500  # Optimal balance
```

## 🔬 **Teknisk Implementation**

### Chunking Strategy Factory
```python
from .chunking import ChunkingStrategyFactory

# Opret strategi baseret på environment
strategy = ChunkingStrategyFactory.create_strategy(
    os.getenv("CHUNKING_STRATEGY", "sentence_splitter")
)
```

### Custom Strategy Development
For at tilføje nye strategier:

1. **Udvid ChunkingStrategy base class**
2. **Implementér chunk_text metoden**
3. **Registrér i factory**
4. **Tilføj til environment validation**

### Strategy Interface
```python
class ChunkingStrategy(ABC):
    @abstractmethod
    def chunk_text(self, text: str, max_tokens: int, title: str = "") -> List[str]:
        pass
```

## 📊 **Performance Sammenligning**

| Aspekt | Sentence Splitter | Word Overlap |
|--------|------------------|--------------|
| **Konsistens** | Variabel chunk størrelse | Fast chunk størrelse |
| **Sprog Respekt** | Høj (sætningsgrænser) | Medium (kan splitte) |
| **Kontekst** | Medium (titel + chunk) | Høj (overlap) |
| **Cross-Page** | God | Fremragende |
| **Performance** | Medium | Høj |
| **Søgekvalitet** | Høj (med titel) | God (uden titel) |
| **Memory Usage** | Lavere | Højere |

## 🧪 **Test og Validering**

### Test Chunking Strategy
```bash
# Test med lille dokument
echo "Test bog URL" > test_input.txt

# Test sentence splitter
CHUNKING_STRATEGY=sentence_splitter ./scripts/process_books.sh --file test_input.txt

# Test word overlap
CHUNKING_STRATEGY=word_overlap ./scripts/process_books.sh --file test_input.txt

# Sammenlign resultater
```

### Debugging Chunking
```bash
# Detaljeret logging
LOG_LEVEL=DEBUG CHUNKING_STRATEGY=sentence_splitter python -c "
from create_embeddings.chunking import ChunkingStrategyFactory
strategy = ChunkingStrategyFactory.create_strategy('sentence_splitter')
chunks = strategy.chunk_text('Test tekst her.', 100, 'Test Titel')
print(f'Chunks: {chunks}')
"
```

## 🚀 **Best Practices**

### Strategi Valg Guidelines

#### Vælg Sentence Splitter når:
- Dokumenter har god sætningsstruktur
- Søgekvalitet er højeste prioritet
- Titel kontekst er værdifuld
- Dokumenterne er korte til mellemlange

#### Vælg Word Overlap når:
- Dokumenter er meget lange
- Kontekst på tværs af chunks er kritisk
- Konsistent chunk størrelse er nødvendig
- Performance er højeste prioritet

### Optimering Workflow
1. **Start med sentence_splitter** for de fleste use cases
2. **Test search kvalitet** med representative queries
3. **Målinger performance** med din hardware
4. **Eksperimentér med word_overlap** hvis nødvendigt
5. **Tune CHUNK_SIZE** baseret på resultater

---

**Se også:**
- [Konfigurationsguide](../KONFIGURATION.md) for parameter detaljer
- [Bog Processering](../BRUGERGUIDER/BOG_PROCESSERING.md) for praktisk brug
- [API Reference](API_REFERENCE.md) for teknisk implementation
