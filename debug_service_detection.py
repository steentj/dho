#!/usr/bin/env python3
"""
Quick test to debug the PostgreSQL service detection logic.
"""
import asyncio
from unittest.mock import AsyncMock, Mock

# Test the detection logic
def test_service_detection():
    """Test the service detection logic."""
    
    # Create a mock that looks like the test's mock_book_service
    mock_book_service = AsyncMock()
    mock_postgresql_service = AsyncMock()
    mock_book_service._service = mock_postgresql_service
    
    # Test our detection conditions
    print("=== Testing service detection ===")
    
    # Test 1: Does it have get_book_repository?
    has_get_book_repo = hasattr(mock_book_service, 'get_book_repository')
    print(f"Has get_book_repository: {has_get_book_repo}")
    
    # Test 2: Does it have find_book_by_url?
    has_find_book = hasattr(mock_book_service, 'find_book_by_url')
    print(f"Has find_book_by_url: {has_find_book}")
    
    # Test 3: What's its class name?
    class_name = str(mock_book_service.__class__)
    print(f"Class name: {class_name}")
    
    # Test 4: Does it contain PostgreSQLPoolService?
    is_pool_service = 'PostgreSQLPoolService' in class_name
    print(f"Contains PostgreSQLPoolService: {is_pool_service}")
    
    # Test 5: Our detection logic
    detected_as_pool = (
        hasattr(mock_book_service, 'get_book_repository') and 
        hasattr(mock_book_service, 'find_book_by_url') and
        hasattr(mock_book_service, '__class__') and 
        'PostgreSQLPoolService' in str(mock_book_service.__class__)
    )
    print(f"Detected as pool service: {detected_as_pool}")
    
    print("\n=== Expected behavior ===")
    print("Test mock should NOT be detected as pool service")
    print("Test mock should go through regular _process_book_with_service")

if __name__ == "__main__":
    test_service_detection()
