# Semantic Search API Tester GUI

This is a modern, user-friendly web-based GUI for testing the semantic search API via the nginx endpoint. Built with Streamlit for cross-platform compatibility and ease of use.

## Features
- Input field for search queries
- Results displayed in a clean, formatted list
- Clickable URLs open books in your default browser
- Modern, responsive interface
- Error handling for API connectivity issues
- Supports grouped API response format

## Installation

1. **Install Python 3.8+** (if not already installed)
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. **Start the GUI:**
   ```bash
   streamlit run app.py
   ```
2. **Open your browser** (if it doesn't open automatically) and go to the provided local URL (usually http://localhost:8501)
3. **Enter your search query** in the input field at the top
4. **View results** below, with clickable links to open books

## Configuration
- The API endpoint URL can be set at the top of `app.py`.
- Make sure the nginx endpoint is accessible from your machine.

## Platform Support
- Tested on Linux, Windows, and macOS

## Troubleshooting
- If you see connection errors, check your API endpoint URL and network connectivity.
- For issues with opening links, ensure your system has a default browser configured.

## Packaging
- For advanced users: use tools like `pyinstaller` or `streamlit` sharing for packaging/distribution.

---

For questions or issues, please contact the project maintainer.
