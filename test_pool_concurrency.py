#!/usr/bin/env python3
"""
Test script to verify that PostgreSQLPoolService resolves the concurrency issue.

This test simulates the concurrent database access pattern that was causing the
"cannot perform operation: another operation is in progress" error.
"""
import asyncio
import os
import logging
from unittest.mock import patch

# Configure basic logging
logging.basicConfig(level=logging.INFO)

async def test_concurrent_book_lookups():
    """Test concurrent database operations using PostgreSQLPoolService."""
    # Mock environment variables for testing
    test_env = {
        'POSTGRES_HOST': 'localhost',
        'POSTGRES_PORT': '5432', 
        'POSTGRES_DB': 'test_db',
        'POSTGRES_USER': 'test_user',
        'POSTGRES_PASSWORD': 'test_password',
        'TESTING': 'true'
    }
    
    with patch.dict(os.environ, test_env, clear=True):
        try:
            from database.postgresql_service import create_postgresql_pool_service
            
            # Create pool service
            pool_service = await create_postgresql_pool_service()
            print("✓ Pool service created successfully")
            
            # Test concurrent operations
            async def lookup_book(book_url, task_id):
                """Simulate book lookup operation."""
                try:
                    print(f"Task {task_id}: Starting lookup for {book_url}")
                    book_id = await pool_service.find_book_by_url(book_url)
                    print(f"Task {task_id}: Found book_id={book_id} for {book_url}")
                    return book_id
                except Exception as e:
                    print(f"Task {task_id}: Error looking up {book_url}: {e}")
                    raise
            
            # Create multiple concurrent tasks
            book_urls = [
                "https://example.com/book1.pdf",
                "https://example.com/book2.pdf", 
                "https://example.com/book3.pdf",
                "https://example.com/book4.pdf",
                "https://example.com/book5.pdf"
            ]
            
            tasks = [
                lookup_book(url, i+1) 
                for i, url in enumerate(book_urls)
            ]
            
            print("Starting 5 concurrent book lookups...")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check results
            success_count = 0
            error_count = 0
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"Task {i+1}: Failed with {type(result).__name__}: {result}")
                    error_count += 1
                else:
                    print(f"Task {i+1}: Success - result={result}")
                    success_count += 1
            
            print(f"\nResults: {success_count} successful, {error_count} failed")
            
            # Cleanup
            await pool_service.disconnect()
            print("✓ Pool service disconnected")
            
            if error_count == 0:
                print("🎉 SUCCESS: No concurrency errors detected!")
                return True
            else:
                print("❌ FAILURE: Concurrency errors still present")
                return False
                
        except ImportError as e:
            print(f"Import error: {e}")
            print("The pool service implementation may not be available")
            return False
        except Exception as e:
            print(f"Test failed with error: {e}")
            return False

if __name__ == "__main__":
    print("Testing PostgreSQLPoolService concurrency fix...")
    success = asyncio.run(test_concurrent_book_lookups())
    exit(0 if success else 1)
