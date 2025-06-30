# Streamlined Book Processing System

This system provides a user-friendly wrapper around the existing `opret_bøger.py` functionality for adding books to the vector database.

## Key Features

- ✅ **Preserves existing functionality** - wraps `opret_bøger.py` without changes
- ✅ **Batch processing** - process multiple books from a file
- ✅ **Progress monitoring** - real-time status tracking
- ✅ **Error recovery** - retry failed books automatically
- ✅ **Containerized** - works on both local Mac and remote Linux servers
- ✅ **User-friendly** - simple command-line interface

## Quick Start

1. **Validate setup:**
   ```bash
   ./scripts/process_books.sh --validate
   ```

2. **Process books:**
   ```bash
   ./scripts/process_books.sh --file example_books.txt
   ```

3. **Monitor progress:**
   ```bash
   ./scripts/process_books.sh --monitor
   ```

4. **Retry failures:**
   ```bash
   ./scripts/process_books.sh --retry-failed
   ```

## Documentation

- [**User Guide**](documentation/BOOK_PROCESSING_USER_GUIDE.md) - Complete usage instructions
- [**Environment Template**](create_embeddings/.env.template) - Required environment variables

## Architecture

```
User Input (book URLs)
        ↓
Control Script (process_books.sh)
        ↓
Docker Container (book-processor)
        ↓
Wrapper (book_processor_wrapper.py)
        ↓
Existing Logic (opret_bøger.py)
        ↓
Vector Database
```

## File Structure

```
scripts/
└── process_books.sh          # Main control script

create_embeddings/
├── book_processor_wrapper.py # Wrapper around opret_bøger.py
├── opret_bøger.py            # Existing book processing logic
├── Dockerfile                # Container definition
└── .env.template             # Environment variables template

soegemaskine/
├── docker-compose.yml        # Updated with book-processor service
├── book_input/               # Input files (created when first used)
├── book_output/              # Processing logs and status
└── book_failed/              # Failed books for retry

documentation/
└── BOOK_PROCESSING_USER_GUIDE.md  # Complete user documentation
```

## Environment Variables

The system reuses the same environment variables as `opret_bøger.py`:

```bash
# Database
POSTGRES_DB=database_name
POSTGRES_USER=username
POSTGRES_PASSWORD=password
POSTGRES_HOST=postgres

# Embedding
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=text-embedding-ada-002
PROVIDER=openai

# Processing
CHUNK_SIZE=500
```

## Benefits Over Manual Process

| Manual Process | Streamlined Process |
|---|---|
| Run script locally | Run anywhere (containerized) |
| Manual error handling | Automatic retry of failures |
| No progress visibility | Real-time monitoring |
| Manual data transfer | Direct database integration |
| Technical expertise required | User-friendly commands |

## Development Notes

This implementation:
- **Wraps** existing `opret_bøger.py` rather than rewriting it
- **Preserves** all existing chunking and embedding logic
- **Maintains** the same concurrent processing (5 books simultaneously)
- **Adds** only monitoring, error handling, and user interface layers
- **Integrates** with existing Docker infrastructure and database
