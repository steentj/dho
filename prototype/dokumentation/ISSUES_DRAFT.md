**Title:** Update Search Response URLs (remove page number in user-facing links)

**Description:**
Update the search API and frontend so that the URLs shown to users do not include the `#page={sidenr}` fragment, but keep the page number in the backend/database for internal use. 

When not showing the page numbers it becomes necessary that if there are more than one search result from the same book the results (chunks) are concatenated in one text string. The individual test chunks found for same book must be clearly separated in the search result. 

As it is now only 5 search results are returned. It should be changed to return all search results with a distance less than a specified number. This number must be read from the environment file. Initially it must be set to 0.5.

**Tasks:**
- Update new parameter in the environment file
- Change the SQL querying the database
- Update the response to collect all results from the same book in one result. 
- Update backend to provide both full and user-facing URLs.
- Update frontend to display only the user-facing URL.
- Create new unit tests and update existing unit tests with the updated behavior.
- Create new integration tests and update existing integration tests with the updated behavior.

---

**Title:** Streamline Adding Books to Vector Database

**Description:**
Make it easier to add new books (from URLs) to the vector database. Right now the script opret_bøger.py in the folder create_embeddings is run manually on the local development machine. The data is then moved manually to the production database.
The process must be changed to:
- opret_bøger script must be placed in a Docker container
- It must be possible to start the script in the Docker container from outside the Docker container. How to do that must be determined.
- When starting and running the script it must be able to give input in form if a file with the url's of the books to create embeddings for
- It must be possible to monitor progress, i.e. books processed, errors etc. 
- If the processing of a book fails, the script must continue with the next book.
- When all books are processed, a list of failed books must be available. The list must be usable as input for a new run of the script.
- There easy to follow user guide must be made in a markdown file. It must be able to follow the user guide without deep knowledge of the system or Docker. 

**Tasks:**
- Document the current process.
- Refactor the script or CLI tool for:
  - Downloading books from URLs.
  - Chunking and embedding.
  - Inserting into the database.
- Create new tests and update existing tests (unit and integration tests)
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

---

**Title:** Create Simple Test GUI for API Testing ✅ **COMPLETED**

**Description:**
~~Create a modern, user-friendly GUI application that allows users to test the semantic search API through the nginx endpoint. The GUI should provide an intuitive interface for querying the API and displaying results in a nicely formatted way with clickable links.~~

**Status:** ✅ **COMPLETED** - Modern Streamlit-based GUI successfully implemented and fully functional.

**Implementation Summary:**
- ✅ **Created modern Danish-localized Streamlit GUI** in `api_testgui/` folder
- ✅ **Proper nginx endpoint integration** - Correctly calls `http://localhost:8080/search`
- ✅ **Updated API format support** - Handles SearchResult format from dhosearch.py
- ✅ **Advanced result display** with grouped chunks, metadata, and dual URL support
- ✅ **Cross-platform compatibility** with build scripts for Linux and macOS
- ✅ **Comprehensive documentation** and troubleshooting guide in Danish
- ✅ **Professional error handling** for API connectivity and timeout issues
- ✅ **Quick start script** for easy launch and dependency checking

**Key Features Delivered:**
- Modern, clean interface with Danish localization
- Search input with real-time API calls to nginx endpoint
- Formatted result display with book titles, authors, relevance scores
- Clickable links for both user-facing URLs and internal URLs with page numbers
- Advanced chunk display with separators and page information
- Comprehensive error handling and user feedback
- Cross-platform build scripts and documentation

**Files Created/Updated:**
- `api_testgui/app.py` - Main Streamlit application (completely rewritten)
- `api_testgui/README.md` - Comprehensive Danish documentation
- `api_testgui/requirements.txt` - Updated with version specifications
- `api_testgui/start_gui.sh` - Quick start script with dependency checking
- `api_testgui/build_linux.sh` - Linux build script
- `api_testgui/build_macos.sh` - macOS build script  
- `api_testgui/streamlit_config.toml` - Theme configuration

~~**Requirements:**~~
~~- Input field for search queries at the top of the page~~
~~- Results list displayed beneath the input field~~
~~- Nicely formatted result presentation~~
~~- Clickable URLs that open books in the default browser~~
~~- Modern, clean, and easy-to-use interface design~~
~~- Cross-platform compatibility~~

~~**Technical Specifications:**~~
~~- Create in a new appropriately named folder (e.g., `test_gui` or `api_tester`)~~
~~- Use a suitable Python GUI framework (recommendations: Tkinter for simplicity, PyQt6/PySide6 for modern look, or Streamlit for web-based GUI)~~
~~- Include proper error handling for API connectivity issues~~
~~- Support for the updated API response format with grouped results~~

~~**Tasks:**~~
~~- Research and select optimal Python GUI framework~~
~~- Design modern and intuitive user interface layout~~
~~- Implement search query input functionality~~
~~- Implement API communication with nginx endpoint~~
~~- Create formatted result display with clickable links~~
~~- Add error handling and user feedback~~
~~- Implement link opening in default browser~~
~~- Create comprehensive user guide in markdown format~~
~~- Test GUI on multiple platforms (macOS, Windows, Linux)~~
~~- Package GUI for easy distribution/installation~~

~~**Deliverables:**~~
~~- Complete GUI application in new folder~~
~~- User guide (README.md) with installation and usage instructions~~
~~- Requirements.txt for dependencies~~
~~- Optional: Executable build scripts for different platforms~~
