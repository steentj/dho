Titel: PostgreSQL Port Fix Checklist
Oprettet: 2025-10-07 15:28
Sidst ændret: 2025-10-07 15:28

# PostgreSQL Port Fix - Checklist

## 🎯 **Efter Port Fix Implementation**

Du har rettet PostgreSQL port problemet i `book_processor_wrapper.py`. Her er hvad du skal gøre nu:

### ✅ **Verificeringsscript**

1. **Tjek din database port:**
   ```bash
   pg_isready -h localhost -p 5432
   pg_isready -h localhost -p 5433
   ```

2. **Verificér .env konfiguration:**
   ```bash
   grep POSTGRES_PORT .env
   # Skal vise: POSTGRES_PORT=5433 (eller hvilken port du bruger)
   ```

3. **Validér systemkonfiguration:**
   ```bash
   ./scripts/process_books.sh --validate
   ```
   
   **Forventet output:**
   ```
   ✅ Alle påkrævede miljøvariabler er sat og gyldige
   Udbyder: ollama
   Chunking Strategy: sentence_splitter
   Database forbindelse: OK
   ```

### 🚀 **Test Processing**

4. **Test med en enkelt bog:**
   ```bash
   echo "https://example.com/test.pdf" > test_single.txt
   ./scripts/process_books.sh --file test_single.txt
   ```

5. **Hvis test går godt, prøv din oprindelige kommando:**
   ```bash
   ./scripts/process_books.sh --file "/Users/steen/Library/Mobile Documents/com~apple~CloudDocs/Projekter/SlægtBib/src/create_embeddings/samlet_input.txt"
   ```

### 🔍 **Hvis Der Stadig Er Problemer**

**Tjek disse ting i rækkefølge:**

1. **Database connection:**
   ```bash
   docker ps | grep postgres
   docker logs dhodb
   ```

2. **Port forwarding (hvis du bruger Docker):**
   ```bash
   docker port dhodb
   ```

3. **Environment variables i container:**
   ```bash
   docker exec -it soegemaskine-book-processor-1 printenv | grep POSTGRES
   ```

4. **Netværk connectivity:**
   ```bash
   docker exec -it soegemaskine-book-processor-1 nc -zv postgres 5432
   ```

### 📝 **Dokumentation Opdateringer**

Følgende dokumenter er opdateret med port troubleshooting:

- ✅ `documentation/GUIDES/BOOK_UPDATES.md` - Fejlfindingsafsnit inkluderer port tjekliste
- ✅ `documentation/GUIDES/LOCAL_SETUP.md` - Opsætningsafsnit beskriver portvalg
- ✅ `.env.template` - Indeholder kommentarer om standardporte

### 🎉 **Succes Indikatorer**

Du ved at fixet virker når:
- `./scripts/process_books.sh --validate` passerer uden database fejl
- Book processing starter uden "Connect call failed" fejl
- Du ser log linjer som: `"Behandler X bøger ved hjælp af eksisterende opret_bøger logik"`

### ⚠️ **Vigtigt at Huske**

- **Altid validér konfiguration først:** `./scripts/process_books.sh --validate`
- **POSTGRES_PORT skal matche den faktiske database port**
- **Restart processing efter .env ændringer**
- **Tjek både localhost og container networking**

---

**Næste skridt:** Når alt virker, kan du fortsætte med din normale bog processing workflow!
