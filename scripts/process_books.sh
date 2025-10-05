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
    echo "  -p, --provider NAME     Override embedding provider only for this run (openai|ollama|dummy)" 
    echo "  -M, --model MODEL       Override embedding model for this run (provider-specific)" 
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
OVERRIDE_PROVIDER=""
OVERRIDE_MODEL=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--file) INPUT_FILE="$2"; shift 2 ;;
        -r|--retry-failed) RETRY_FAILED=true; shift ;;
        -m|--monitor) MONITOR_ONLY=true; shift ;;
        -v|--validate) VALIDATE_ONLY=true; shift ;;
        -p|--provider) OVERRIDE_PROVIDER="$2"; shift 2 ;;
        -M|--model) OVERRIDE_MODEL="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
done

cd "$PROJECT_ROOT/soegemaskine"

# Create necessary directories
mkdir -p book_input book_output book_failed

if [ "$VALIDATE_ONLY" = true ]; then
    echo "=== Validating Configuration ==="
    # Ensure required directories exist with minimal necessary permissions
    REQUIRED_DIRS=(book_input book_output book_failed)
    for dir in "${REQUIRED_DIRS[@]}"; do
        mkdir -p "$dir"
        chmod 700 "$dir"

        if ! test -w "$dir"; then
            echo "Adjusting permissions so $(whoami) can write to $dir..."
            chmod u+rwx "$dir" || { echo "Failed to grant write access to $dir" >&2; exit 1; }
        fi

        if command -v setfacl >/dev/null 2>&1; then
            setfacl -m u:1000:rwx "$dir"
            setfacl -m d:u:1000:rwx "$dir"
        else
            chmod 770 "$dir"
        fi

        if ! touch "$dir/.permission_test" >/dev/null 2>&1; then
            echo "Permission check failed for $dir (cannot create files)" >&2
            exit 1
        fi
        rm -f "$dir/.permission_test"
    done
    # Stage 2 addition: local validation before container-based validation
    if [ -f .env ]; then
        echo "Running host-side validation (scripts/validate_env.py)..."
        python3 ../scripts/validate_env.py || { echo "Host validation failed"; exit 1; }
    else
        echo "Warning: .env file not found in soegemaskine directory; skipping host validation" >&2
    fi
    # --no-deps ensures we reuse production postgres/ollama instead of trying to start new ones
    docker-compose run --rm --no-deps book-processor --validate-config
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
    # Allow provider/model overrides on retry as well
    DOCKER_CMD=(docker-compose run --rm --no-deps)
    if [ -n "$OVERRIDE_PROVIDER" ]; then
        case "$OVERRIDE_PROVIDER" in
            openai|ollama|dummy) DOCKER_CMD+=( -e PROVIDER="$OVERRIDE_PROVIDER" ) ;;
            *) echo "Error: Invalid provider override: $OVERRIDE_PROVIDER"; exit 1 ;;
        esac
    fi
    if [ -n "$OVERRIDE_MODEL" ]; then
        if [ "$OVERRIDE_PROVIDER" = "openai" ]; then
            DOCKER_CMD+=( -e OPENAI_MODEL="$OVERRIDE_MODEL" )
        elif [ "$OVERRIDE_PROVIDER" = "ollama" ]; then
            DOCKER_CMD+=( -e OLLAMA_MODEL="$OVERRIDE_MODEL" )
        else
            DOCKER_CMD+=( -e OPENAI_MODEL="$OVERRIDE_MODEL" -e OLLAMA_MODEL="$OVERRIDE_MODEL" )
        fi
    fi
    DOCKER_CMD+=( book-processor --retry-failed )
    echo "Running: ${DOCKER_CMD[*]}"
    "${DOCKER_CMD[@]}"
    
elif [ -n "$INPUT_FILE" ]; then
    if [ ! -f "$INPUT_FILE" ]; then
        echo "Error: Input file not found: $INPUT_FILE"
        exit 1
    fi

    # Pre-run validation (fails fast before starting container)
    if [ -f .env ]; then
        echo "Validating environment before processing..."
        python3 ../scripts/validate_env.py || { echo "Environment validation failed"; exit 1; }
    fi

    # Validate provider override if provided
    if [ -n "$OVERRIDE_PROVIDER" ]; then
        case "$OVERRIDE_PROVIDER" in
            openai|ollama|dummy) : ;;
            *) echo "Error: Invalid provider override: $OVERRIDE_PROVIDER"; exit 1 ;;
        esac
    fi

    # Show execution summary
    echo "=== Execution Summary ==="
    if [ -n "$OVERRIDE_PROVIDER" ]; then
        echo "Provider override: $OVERRIDE_PROVIDER"
    else
        echo "Provider override: (none) - will use .env PROVIDER inside container"
    fi
    if [ -n "$OVERRIDE_MODEL" ]; then
        echo "Model override: $OVERRIDE_MODEL"
    else
        echo "Model override: (none)"
    fi
    echo "Input file: $INPUT_FILE"
    echo "=========================="
    
    # Copy to docker volume
    cp "$INPUT_FILE" book_input/
    INPUT_FILENAME=$(basename "$INPUT_FILE")
    
    echo "=== Processing Books ==="
    echo "Input file: $INPUT_FILE"
    echo "Using existing opret_bøger.py logic with monitoring..."
    echo ""
    
    # Build docker compose run command with ephemeral env overrides
    DOCKER_CMD=(docker-compose run --rm --no-deps)
    if [ -n "$OVERRIDE_PROVIDER" ]; then
        DOCKER_CMD+=( -e PROVIDER="$OVERRIDE_PROVIDER" )
    fi
    if [ -n "$OVERRIDE_MODEL" ]; then
        # Decide which variable to set based on provider if specified, else set both openai/ollama model vars
        if [ "$OVERRIDE_PROVIDER" = "openai" ]; then
            DOCKER_CMD+=( -e OPENAI_MODEL="$OVERRIDE_MODEL" )
        elif [ "$OVERRIDE_PROVIDER" = "ollama" ]; then
            DOCKER_CMD+=( -e OLLAMA_MODEL="$OVERRIDE_MODEL" )
        else
            # Fallback: set both potential model variables (harmless if unused)
            DOCKER_CMD+=( -e OPENAI_MODEL="$OVERRIDE_MODEL" -e OLLAMA_MODEL="$OVERRIDE_MODEL" )
        fi
    fi
    # Container expects files under /app/input mounted from host book_input
    CONTAINER_INPUT_PATH="input/$INPUT_FILENAME"
    DOCKER_CMD+=( book-processor --input-file "$CONTAINER_INPUT_PATH" )
    echo "Running: ${DOCKER_CMD[*]}"
    "${DOCKER_CMD[@]}"
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
