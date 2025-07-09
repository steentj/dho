import os
import logging
import pytest
from datetime import datetime
from create_embeddings.logging_config import setup_logging, get_log_directory

@pytest.fixture
def temp_log_dir(tmp_path):
    """Fixture to provide a temporary log directory."""
    return tmp_path

@pytest.fixture
def clean_env():
    """Fixture to provide a clean environment for testing."""
    old_env = dict(os.environ)
    if "LOG_DIR" in os.environ:
        del os.environ["LOG_DIR"]
    yield
    os.environ.clear()
    os.environ.update(old_env)

def test_setup_logging_default_directory(temp_log_dir):
    """Test setup_logging with default parameters."""
    # Call setup_logging with default parameters
    log_file = setup_logging(log_dir=str(temp_log_dir))
    
    # Verify the log file is created
    assert log_file.exists()
    assert str(log_file).startswith(str(temp_log_dir))
    assert str(log_file).endswith(".log")
    
    # Verify the root logger is configured correctly
    root_logger = logging.getLogger()
    assert root_logger.level == logging.INFO
    
    # Verify handlers are configured
    handlers = root_logger.handlers
    assert len(handlers) == 2  # FileHandler and StreamHandler
    
    # Verify file handler
    file_handler = next(h for h in handlers if isinstance(h, logging.FileHandler))
    assert file_handler.baseFilename == str(log_file)
    assert file_handler.encoding == "utf-8"

def test_setup_logging_custom_level(temp_log_dir):
    """Test setup_logging with custom log level."""
    log_file = setup_logging(log_dir=str(temp_log_dir), log_level=logging.DEBUG)
    
    # Verify the root logger level is set to DEBUG
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG
    
    # Verify the log file exists
    assert log_file.exists()

def test_setup_logging_creates_directory(temp_log_dir):
    """Test setup_logging creates log directory if it doesn't exist."""
    new_log_dir = temp_log_dir / "nested" / "log" / "dir"
    log_file = setup_logging(log_dir=str(new_log_dir))
    
    # Verify directory is created
    assert new_log_dir.exists()
    assert new_log_dir.is_dir()
    
    # Verify log file is created in the new directory
    assert log_file.exists()
    assert log_file.parent == new_log_dir

def test_setup_logging_suppresses_external_loggers(temp_log_dir):
    """Test setup_logging suppresses verbose logs from external libraries."""
    setup_logging(log_dir=str(temp_log_dir))
    
    # Verify external loggers are set to WARNING
    openai_logger = logging.getLogger("openai")
    aiohttp_logger = logging.getLogger("aiohttp")
    httpx_logger = logging.getLogger("httpx")
    
    assert openai_logger.level == logging.WARNING
    assert aiohttp_logger.level == logging.WARNING
    assert httpx_logger.level == logging.WARNING

def test_get_log_directory_with_env_var(clean_env):
    """Test get_log_directory with LOG_DIR environment variable."""
    test_dir = "/test/log/dir"
    os.environ["LOG_DIR"] = test_dir
    
    assert get_log_directory() == test_dir

def test_get_log_directory_default(clean_env):
    """Test get_log_directory without LOG_DIR environment variable."""
    assert get_log_directory() == "."

def test_setup_logging_file_format(temp_log_dir):
    """Test the format of the log file name."""
    log_file = setup_logging(log_dir=str(temp_log_dir))
    
    # Get current timestamp in the same format as the logging setup
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    expected_filename = f"opret_bøger_{timestamp}.log"
    
    assert log_file.name.startswith("opret_bøger_")
    assert log_file.name.endswith(".log")
    assert len(log_file.name) == len(expected_filename)

def test_setup_logging_message_format(temp_log_dir):
    """Test the format of log messages."""
    log_file = setup_logging(log_dir=str(temp_log_dir))
    test_message = "Test log message"
    
    # Write a test message
    logging.info(test_message)
    
    # Read the log file
    with open(log_file, 'r', encoding='utf-8') as f:
        log_content = f.read()
    
    # Verify message format
    assert test_message in log_content
    # Should contain timestamp, level, and message
    assert " - INFO - " in log_content

def test_setup_logging_no_directory_provided(clean_env, temp_log_dir):
    """Test setup_logging with no directory provided."""
    # Set LOG_DIR environment variable to temp directory
    os.environ["LOG_DIR"] = str(temp_log_dir)
    
    # Call setup_logging without log_dir parameter
    log_file = setup_logging(log_dir=None)
    
    # Verify the log directory comes from environment variable
    assert str(log_file).startswith(str(temp_log_dir))
    assert str(log_file).endswith(".log")
