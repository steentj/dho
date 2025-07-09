"""
Shared logging configuration for book processing modules.
"""
import logging
import os
from datetime import datetime
from pathlib import Path


def setup_logging(log_dir: str = None, log_level: int = logging.INFO) -> Path:
    """
    Setup consistent logging configuration for all book processing modules.
    
    Args:
        log_dir: Directory where log files should be written. 
                If None, uses current directory or LOG_DIR environment variable.
        log_level: Logging level (default: INFO)
    
    Returns:
        Path to the created log file
    """
    # Determine log directory
    if log_dir is None:
        log_dir = os.getenv("LOG_DIR", ".")
    
    log_dir_path = Path(log_dir)
    log_dir_path.mkdir(parents=True, exist_ok=True)
    
    # Create timestamped log file
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = log_dir_path / f"opret_bøger_{timestamp}.log"
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True  # Override any existing configuration
    )
    
    # Suppress verbose logs from external libraries
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    logging.info(f"Logging configured. Log file: {log_file}")
    return log_file


def get_log_directory() -> str:
    """
    Get the configured log directory.
    Priority: LOG_DIR env var > current directory
    """
    return os.getenv("LOG_DIR", ".")
