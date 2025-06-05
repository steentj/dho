# Logging Configuration

This project uses a shared logging configuration to ensure consistent logging across all modules.

## Configuration

### Environment Variables
- `LOG_DIR`: Directory where log files will be created (default: current directory)

### Log Files
- Log files are named with timestamp: `opret_bøger_YYYY-MM-DD_HH-MM-SS.log`
- Both `opret_bøger.py` and `book_processor_wrapper.py` use the same logging configuration

### Log Levels
- Console: INFO and above
- File: INFO and above  
- External libraries (openai, aiohttp): WARNING and above

## Usage

Both scripts now use the shared `logging_config.setup_logging()` function:

```python
from logging_config import setup_logging

# Setup logging (will use LOG_DIR env var or current directory)
log_file = setup_logging()

# Or specify custom directory
log_file = setup_logging(log_dir="/path/to/logs")
```

## Output Format
```
2025-01-12 14:22:35,123 - INFO - Processing started
2025-01-12 14:22:36,456 - WARNING - Connection timeout, retrying...
2025-01-12 14:22:37,789 - ERROR - Failed to process book: example.pdf
```
