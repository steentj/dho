#!/bin/bash
# Streamlined book processing control script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -f, --file FILE         Input file with book URLs"
    echo "  -r, --retry-failed      Retry previously failed books"
    echo "  -m, --monitor          Show monitoring status"
    echo "  -v, --validate         Validate configuration" 
    echo "  -h, --help             Show this help"
    echo ""
    echo "Input file format: One URL per line (same as existing opret_bøger.py)"
    echo ""
    echo "Examples:"
    echo "  $0 --file books.txt     # Process books from file"
    echo "  $0 --retry-failed       # Retry previously failed books"
    echo "  $0 --monitor           # Show current status"
    echo "  $0 --validate          # Check configuration"
}

# Parse arguments
INPUT_FILE=""
RETRY_FAILED=false
MONITOR_ONLY=false
VALIDATE_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--file) INPUT_FILE="$2"; shift 2 ;;
        -r|--retry-failed) RETRY_FAILED=true; shift ;;
        -m|--monitor) MONITOR_ONLY=true; shift ;;
        -v|--validate) VALIDATE_ONLY=true; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
done

cd "$PROJECT_ROOT/prototype"

# Create necessary directories
mkdir -p book_input book_output book_failed

if [ "$VALIDATE_ONLY" = true ]; then
    echo "=== Validating Configuration ==="
    docker-compose run --rm book-processor --validate-config
    exit $?
fi

if [ "$MONITOR_ONLY" = true ]; then
    echo "=== Current Status ==="
    if [ -f book_output/processing_status.json ]; then
        cat book_output/processing_status.json | python3 -m json.tool
    else
        echo "No processing status found"
    fi
    echo ""
    echo "=== Recent Logs ==="
    if ls book_output/opret_bøger_*.log 1> /dev/null 2>&1; then
        tail -20 book_output/opret_bøger_*.log | tail -20
    else
        echo "No log files found"
    fi
    
    echo ""
    echo "=== Failed Books ==="
    if [ -f book_failed/failed_books.json ]; then
        echo "Failed books count: $(cat book_failed/failed_books.json | python3 -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")"
        echo "Use --retry-failed to retry them"
    else
        echo "No failed books"
    fi
    exit 0
fi

# Process books
if [ "$RETRY_FAILED" = true ]; then
    echo "=== Retrying Failed Books ==="
    if [ ! -f book_failed/failed_books.json ]; then
        echo "No failed books file found. Nothing to retry."
        exit 0
    fi
    
    failed_count=$(cat book_failed/failed_books.json | python3 -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
    if [ "$failed_count" = "0" ]; then
        echo "No failed books to retry."
        exit 0
    fi
    
    echo "Retrying $failed_count failed books..."
    docker-compose run --rm book-processor --retry-failed
    
elif [ -n "$INPUT_FILE" ]; then
    if [ ! -f "$INPUT_FILE" ]; then
        echo "Error: Input file not found: $INPUT_FILE"
        exit 1
    fi
    
    # Copy to docker volume
    cp "$INPUT_FILE" book_input/
    INPUT_FILENAME=$(basename "$INPUT_FILE")
    
    echo "=== Processing Books ==="
    echo "Input file: $INPUT_FILE"
    echo "Using existing opret_bøger.py logic with monitoring..."
    echo ""
    
    docker-compose run --rm book-processor --input-file "$INPUT_FILENAME"
else
    echo "Error: Either --file or --retry-failed required"
    usage
    exit 1
fi

echo ""
echo "=== Processing Complete ==="
echo "Check results:"
echo "  Status: $0 --monitor"
echo "  Detailed status: cat book_output/processing_status.json"
echo "  Logs: ls book_output/opret_bøger_*.log"
if [ -f book_failed/failed_books.json ]; then
    failed_count=$(cat book_failed/failed_books.json | python3 -c "import sys, json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
    if [ "$failed_count" != "0" ]; then
        echo "  Failed books ($failed_count): $0 --retry-failed"
    fi
fi
