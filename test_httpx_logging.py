#!/usr/bin/env python3
"""
Quick test to verify that httpx logging is suppressed.
This demonstrates that the fix for Ollama HTTP request log spam works.
"""

import logging
import tempfile
from create_embeddings.logging_config import setup_logging

def test_httpx_logging_suppression():
    """Test that httpx logs are suppressed to WARNING level."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Setup logging with our configuration
        log_file = setup_logging(log_dir=temp_dir)
        
        # Get the httpx logger and test different log levels
        httpx_logger = logging.getLogger("httpx")
        
        print(f"httpx logger level: {httpx_logger.level}")
        print(f"Expected level (WARNING): {logging.WARNING}")
        
        # Test logging at different levels
        httpx_logger.info("This INFO message should be suppressed")
        httpx_logger.warning("This WARNING message should appear")
        httpx_logger.error("This ERROR message should appear")
        
        # Read the log file to verify what was actually logged
        with open(log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()
        
        print("\n--- Log file content ---")
        print(log_content)
        print("--- End log content ---\n")
        
        # Verify that only WARNING and ERROR messages appear
        assert "This INFO message should be suppressed" not in log_content
        assert "This WARNING message should appear" in log_content
        assert "This ERROR message should appear" in log_content
        
        print("✅ SUCCESS: httpx INFO logs are properly suppressed!")
        print("Only WARNING and ERROR messages from httpx will appear in your book processing logs.")

if __name__ == "__main__":
    test_httpx_logging_suppression()
