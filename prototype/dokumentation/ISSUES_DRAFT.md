**Title:** Update Search Response URLs (remove page number in user-facing links)

**Description:**
Update the search API and frontend so that the URLs shown to users do not include the `#page={sidenr}` fragment, but keep the page number in the backend/database for internal use.

**Tasks:**
- Update backend to provide both full and user-facing URLs.
- Update frontend to display only the user-facing URL.
- Test that internal logic still works with page numbers.

---

**Title:** Streamline Adding Books to Vector Database

**Description:**
Make it easier to add new books (from URLs) to the vector database.

**Tasks:**
- Document the current process.
- Refactor the script or CLI tool for:
  - Downloading books from URLs.
  - Chunking and embedding.
  - Inserting into the database.
- Update documentation for the new workflow.

---

**Title:** Create unit and integration tests

**Description:**
Setup local testing on Mac, including both unit tests (with mocks) and integration tests.

**Tasks:**
- Add `requirements-dev.txt` for test dependencies.
- Refactor code if necessary to prepare for and to enable good and easy unit and integration tests
- Add unit tests for backend logic (use mocks where possible).
- Add integration tests for
  - Embedding script
    - Use a mock book
    - Use mock embedding provider (substitute for OpenAI)
    - Verify chunking is correct and that embeddings are correctly created and stored in the (mock) database
  - Search API
    - Verify correct parsing and receipt of search request
    - Verify that embedding for search text is created (use mock api provider)
    - Verify that database search query is correct setup
    - Verify that search results are returned correctly
- Document how to run tests locally.

---

**Title:** A/B Test: Book Title in Embeddings

**Description:**
Enable local A/B testing to compare search results with and without book titles in the chunk embeddings.

**Tasks:**
- Add config option to include/exclude book titles in embeddings.
- Make a local database to hold the embeddings used for the tests
- Generate two sets of embeddings.
- Update local test UI to switch between embeddings.
- Document how to run the A/B test.
- Record user feedback/results.
