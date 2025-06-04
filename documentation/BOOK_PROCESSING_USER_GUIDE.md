# Book Processing User Guide

## Docker Usage - No Container Terminal Required

**Important**: You run everything from your **host machine terminal** - you never need to enter Docker container terminals. The system automatically handles all Docker operations for you.

## Quick Start

### Prerequisites
1. Ensure Docker and Docker Compose are installed
2. Navigate to the project directory:
   ```bash
   cd /path/to/SlægtBib/src
   ```

### 1. Validate Configuration
First, ensure your environment is properly configured:

```bash
./scripts/process_books.sh --validate
```

**What happens**: This command automatically starts a temporary Docker container, validates your `.env` file, then removes the container. You stay in your host terminal the entire time.

### 2. Create Book List  
Create a text file **on your host machine** with one URL per line:

```bash
# Create the file anywhere on your host machine
nano my_books.txt
```

Content format (same as existing opret_bøger.py):
```
https://example.com/book1.pdf
https://example.com/book2.pdf
https://example.com/book3.pdf
```

### 3. Process Books
All commands run from your **host terminal**:

```bash
# Process new books (runs in Docker automatically)
./scripts/process_books.sh --file my_books.txt

# Monitor progress (in another host terminal - no Docker terminal)
./scripts/process_books.sh --monitor

# Retry failed books (runs in Docker automatically)  
./scripts/process_books.sh --retry-failed
```

**What happens**: Each command automatically:
1. Starts a Docker container with your book processor
2. Mounts your files into the container 
3. Runs the processing
4. Saves results back to your host machine
5. Removes the temporary container

## How It Works

This system wraps the existing `opret_bøger.py` functionality without changing it:

- ✅ **Same chunking algorithm**: Sentence-based splitting with metadata inclusion (`##{title}##chunk`)
- ✅ **Same concurrent processing**: 5 books processed simultaneously using semaphore  
- ✅ **Same database operations**: Uses existing connection pooling and queries
- ✅ **Same embedding creation**: Uses existing OpenAI integration with configurable models
- ✅ **Added**: Progress monitoring, error recovery, containerization

## Environment Variables

The system uses the same environment variables as `opret_bøger.py`. Add these to your `.env` file:

```bash
# Database Configuration
POSTGRES_DB=your_database_name
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=postgres  # Docker service name

# Embedding Configuration
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=text-embedding-ada-002
PROVIDER=openai

# Processing Configuration
CHUNK_SIZE=500
```

### Environment Variable Details

- **POSTGRES_HOST**: Set to `postgres` when running in Docker, or your database host for local development
- **OPENAI_MODEL**: The embedding model to use (e.g., `text-embedding-ada-002`, `text-embedding-3-small`)
- **PROVIDER**: Set to `openai` for production, or `dummy` for testing
- **CHUNK_SIZE**: Maximum tokens per text chunk (default: 500)

## Commands Reference

### Process Books from File
```bash
./scripts/process_books.sh --file books.txt
```

Processes all URLs listed in the specified file using the existing opret_bøger.py logic.

### Monitor Progress
```bash
./scripts/process_books.sh --monitor
```

Shows:
- Current processing status (running, completed, error)
- Number of books processed vs total
- Number of failed books
- Recent log entries
- Failed books count and retry instructions

### Retry Failed Books
```bash
./scripts/process_books.sh --retry-failed
```

Automatically retries all books that failed in previous runs. Failed books are saved in `book_failed/failed_books.json`.

### Validate Configuration
```bash
./scripts/process_books.sh --validate
```

Checks that all required environment variables are set and displays current configuration.

## File Locations

When running the book processor, files are organized as follows:

```
prototype/
├── book_input/           # Input files (your book URL lists)
├── book_output/          # Processing logs and status
│   ├── processing_status.json
│   └── opret_bøger_*.log
└── book_failed/          # Failed books for retry
    └── failed_books.json
```

## Status File Format

The `book_output/processing_status.json` file contains:

```json
{
  "status": "completed",
  "total_books": 10,
  "processed": 8,
  "failed": 2,
  "last_updated": "2025-06-04T12:30:00",
  "embedding_model": "text-embedding-ada-002",
  "provider": "openai"
}
```

## Failed Books Format

The `book_failed/failed_books.json` file contains:

```json
[
  {
    "url": "https://example.com/problematic-book.pdf",
    "error": "HTTP 404: Not Found",
    "timestamp": "2025-06-04T12:25:00"
  }
]
```

## Troubleshooting

### Common Issues

**"Missing required environment variables"**
- Ensure your `.env` file contains all required variables
- Run `./scripts/process_books.sh --validate` to check

**"Input file not found"**
- Verify the file path is correct
- Ensure the file exists and is readable

**"Database connection failed"**
- Check that PostgreSQL container is running: `docker-compose ps`
- Verify database credentials in `.env` file
- Ensure the database exists and has pgvector extension

**"OpenAI API errors"**
- Verify `OPENAI_API_KEY` is set correctly
- Check API quota and billing status
- Consider using a different model in `OPENAI_MODEL`

### Viewing Detailed Logs

```bash
# View latest log file
ls -t book_output/opret_bøger_*.log | head -1 | xargs cat

# Follow real-time processing (in another terminal)
tail -f book_output/opret_bøger_*.log
```

### Manual Cleanup

```bash
# Clear all processing data (start fresh)
rm -rf book_output/* book_failed/*

# Clear only failed books (to retry everything)
rm -f book_failed/failed_books.json
```

## Performance Notes

- **Concurrent Processing**: 5 books are processed simultaneously (same as original opret_bøger.py)
- **Database Connections**: Uses connection pooling for efficient database access
- **Memory Usage**: Memory consumption scales with concurrent books and chunk size
- **Rate Limiting**: OpenAI API calls are naturally throttled by concurrent book limit

## Integration with Existing System

This book processor integrates seamlessly with your existing search system:

1. **Database Schema**: Uses the same tables and structure as the original opret_bøger.py
2. **Embedding Format**: Creates embeddings in the same format expected by the search API
3. **Metadata**: Preserves the same metadata structure (`##{title}##chunk`) for search functionality
4. **Vector Storage**: Stores vectors in the same pgvector format used by the search system

## Examples

### Process a Small Test Batch
```bash
# Create test file
echo -e "https://example.com/book1.pdf\nhttps://example.com/book2.pdf" > test_books.txt

# Process with monitoring
./scripts/process_books.sh --file test_books.txt

# Check results
./scripts/process_books.sh --monitor
```

### Handle Large Batches
```bash
# Process large batch (hundreds of books)
./scripts/process_books.sh --file large_book_list.txt

# Monitor in separate terminal
watch './scripts/process_books.sh --monitor'

# If some fail, retry them
./scripts/process_books.sh --retry-failed
```

## Benefits

- ✅ **No code changes** to proven opret_bøger.py logic
- ✅ **Same performance** - identical concurrent processing (5 books at once)
- ✅ **Same quality** - identical chunking and embedding creation  
- ✅ **Added monitoring** - track progress and failures in real-time
- ✅ **Added recovery** - retry failed books easily without manual intervention
- ✅ **Added portability** - works on local Mac and remote Linux servers
- ✅ **User-friendly** - simple command-line interface requiring no technical knowledge
- ✅ **Production-ready** - containerized with proper logging and error handling

## Docker Workflow Explained

### How Docker Integration Works

You work entirely from your **host machine** (Mac/Linux terminal). Here's what happens behind the scenes:

```
Your Host Machine                    Docker Container
    ┌─────────────────┐                ┌──────────────────┐
    │ 1. You run:     │                │                  │
    │ ./scripts/      │                │                  │
    │ process_books.sh│───────────────▶│ 2. Container     │
    │                 │                │    starts        │
    │                 │                │    automatically  │
    └─────────────────┘                └──────────────────┘
           │                                      │
           │                                      ▼
    ┌─────────────────┐                ┌──────────────────┐
    │ 4. Results      │                │ 3. Processing    │
    │    saved to     │◀───────────────│    happens in    │
    │    host folders │                │    container     │
    │                 │                │                  │
    └─────────────────┘                └──────────────────┘
```

### File Locations on Your Host Machine

All files remain on your host machine in these locations:

```bash
/path/to/SlægtBib/src/
├── my_books.txt                    # Your input file (you create this)
├── scripts/process_books.sh        # The script you run
└── prototype/
    ├── book_input/                 # Input files (auto-created)
    ├── book_output/                # Results you can view
    │   ├── processing_status.json  # Status file
    │   └── opret_bøger_*.log      # Log files
    └── book_failed/                # Failed books
        └── failed_books.json       # Failed books list
```

**Important**: You can view, edit, and manage all these files directly from your host machine - no need to access Docker containers.

## Step-by-Step Docker Usage

### Complete Workflow Example

```bash
# 1. Navigate to project (on your host machine)
cd /Users/steen/Library/Mobile\ Documents/com~apple~CloudDocs/Projekter/SlægtBib/src

# 2. Check Docker is running
docker --version
docker-compose --version

# 3. Validate configuration (auto-starts container temporarily)
./scripts/process_books.sh --validate

# 4. Create your book list (on host machine)
echo -e "https://example.com/book1.pdf\nhttps://example.com/book2.pdf" > my_books.txt

# 5. Process books (auto-starts container, processes, then stops)
./scripts/process_books.sh --file my_books.txt

# 6. Check results (files are on your host machine)
./scripts/process_books.sh --monitor

# 7. If needed, retry failures (auto-starts container again)
./scripts/process_books.sh --retry-failed
```

### What You'll See During Processing

When you run `./scripts/process_books.sh --file my_books.txt`:

```
=== Processing Books ===
Input file: my_books.txt
Using existing opret_bøger.py logic with monitoring...

[+] Building 0.0s (0/0)                                    
[+] Running 1/0
 ✔ Container dho-book-processor  Created                   0.0s
Attaching to dho-book-processor
dho-book-processor  | 2025-06-04 12:30:00 - INFO - Processing 2 books using existing opret_bøger logic
dho-book-processor  | 2025-06-04 12:30:15 - INFO - ✓ Successfully processed: https://example.com/book1.pdf
dho-book-processor  | 2025-06-04 12:30:30 - INFO - ✓ Successfully processed: https://example.com/book2.pdf
dho-book-processor  | 2025-06-04 12:30:31 - INFO - Processing completed: 2 successful, 0 failed
[+] Container dho-book-processor  Exited (0)

=== Processing Complete ===
Check results:
  Status: ./scripts/process_books.sh --monitor
```

### Monitoring in Real-Time

Open a **second terminal on your host machine** and run:

```bash
# This shows status without starting containers
./scripts/process_books.sh --monitor
```

Output:
```
=== Current Status ===
{
  "status": "running",
  "total_books": 10,
  "processed": 3,
  "failed": 0,
  "last_updated": "2025-06-04T12:30:00",
  "embedding_model": "text-embedding-ada-002",
  "provider": "openai"
}

=== Recent Logs ===
2025-06-04 12:30:00 - INFO - ✓ Successfully processed: https://example.com/book1.pdf
2025-06-04 12:30:15 - INFO - Processing book 4/10: https://example.com/book4.pdf
```

## Docker Commands Reference

### All Commands Run from Host Terminal

**Never run these commands inside Docker containers** - they automatically manage containers for you:

| Command | What It Does | Docker Behavior |
|---------|-------------|-----------------|
| `./scripts/process_books.sh --validate` | Check configuration | Starts container → validates → stops container |
| `./scripts/process_books.sh --file books.txt` | Process books | Starts container → processes → stops container |
| `./scripts/process_books.sh --monitor` | Show status | **No container** - reads files from host |
| `./scripts/process_books.sh --retry-failed` | Retry failures | Starts container → retries → stops container |

### Manual Docker Commands (If Needed)

If you need to manually interact with Docker (rarely needed):

```bash
# Check if containers are running
docker-compose ps

# View container logs (only while processing)
docker-compose logs book-processor

# Stop all containers if needed
docker-compose down

# Rebuild container after code changes
docker-compose build book-processor
```

### Troubleshooting Docker Issues

**"docker-compose command not found"**
```bash
# Install docker-compose or use newer syntax
docker compose --version  # Try this instead
```

**"Permission denied"**
```bash
# Make script executable
chmod +x ./scripts/process_books.sh
```

**"No such file or directory"**
```bash
# Ensure you're in the correct directory
cd /path/to/SlægtBib/src
pwd  # Should show the project directory
```

**Container won't start**
```bash
# Check Docker is running
docker --version
docker-compose --version

# Check your .env file exists
ls -la prototype/.env

# Validate configuration
./scripts/process_books.sh --validate
```

## Remote Linux Server Usage

### Same Commands, Different Location

On a remote Linux server, the workflow is identical:

```bash
# SSH to your server first
ssh user@your-server.com

# Navigate to project
cd /path/to/SlægtBib/src

# Use exact same commands
./scripts/process_books.sh --validate
./scripts/process_books.sh --file books.txt
./scripts/process_books.sh --monitor
```

### File Transfer to Remote Server

```bash
# Copy book list to server
scp my_books.txt user@server:/path/to/SlægtBib/src/

# Process on server
ssh user@server "cd /path/to/SlægtBib/src && ./scripts/process_books.sh --file my_books.txt"

# Copy results back (optional)
scp user@server:/path/to/SlægtBib/src/prototype/book_output/* ./results/
```

## Key Benefits of This Docker Approach

✅ **No container terminal access needed** - everything controlled from host

✅ **Automatic container management** - containers start and stop as needed

✅ **File persistence** - all files remain on your host machine

✅ **Cross-platform** - identical commands on Mac and Linux

✅ **Resource efficient** - containers only run when processing

✅ **Easy monitoring** - view files and status without Docker knowledge
