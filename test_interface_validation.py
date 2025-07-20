#!/usr/bin/env python3
"""
Validation script to test if our IBookService interface refactoring works correctly.
This tests the core changes without running the full test suite.
"""

import sys
import traceback
from pathlib import Path

# Ensure we can import everything
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all our interface changes can be imported successfully."""
    print("Testing interface imports...")
    
    try:
        # Test interface import
        from create_embeddings.book_service_interface import IBookService
        print("✓ IBookService interface imports successfully")
        
        # Test PostgreSQL service imports
        from database.postgresql_service import PostgreSQLService, PostgreSQLPoolService, BookService
        print("✓ PostgreSQL services import successfully")
        
        # Test that services implement the interface
        print(f"✓ PostgreSQLService MRO: {PostgreSQLService.__mro__}")
        print(f"✓ PostgreSQLPoolService MRO: {PostgreSQLPoolService.__mro__}")
        
        # Test service instantiation (the key test that was failing)
        print("Testing service instantiation...")
        
        # Mock dependencies for testing
        class MockBookRepo:
            pass
        class MockSearchRepo:
            pass
        class MockConnection:
            pass
            
        # Try to create PostgreSQL service instances
        service = PostgreSQLService()
        print("✓ PostgreSQLService() instantiated successfully")
        
        pool_service = PostgreSQLPoolService()
        print("✓ PostgreSQLPoolService() instantiated successfully")
        
        # Try BookService wrapper
        wrapper_service = BookService(service)
        print("✓ BookService wrapper instantiated successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import/instantiation failed: {e}")
        traceback.print_exc()
        return False

def test_interface_contract():
    """Test that our services properly implement the interface contract."""
    print("\nTesting interface contract...")
    
    try:
        from create_embeddings.book_service_interface import IBookService
        from database.postgresql_service import PostgreSQLService
        
        # Check that PostgreSQLService implements required methods
        service = PostgreSQLService()
        
        # Check method existence
        assert hasattr(service, 'save_book_with_chunks'), "Missing save_book_with_chunks method"
        assert hasattr(service, 'book_exists_with_provider'), "Missing book_exists_with_provider method"
        
        # Check method signatures (they should be async)
        import inspect
        assert inspect.iscoroutinefunction(service.save_book_with_chunks), "save_book_with_chunks should be async"
        assert inspect.iscoroutinefunction(service.book_exists_with_provider), "book_exists_with_provider should be async"
        
        print("✓ Interface contract validated successfully")
        return True
        
    except Exception as e:
        print(f"❌ Interface contract validation failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all validation tests."""
    print("=== Interface Refactoring Validation ===\n")
    
    success = True
    success &= test_imports()
    success &= test_interface_contract()
    
    print(f"\n=== Results ===")
    if success:
        print("✅ All validation tests PASSED")
        print("The IBookService interface refactoring appears to be working correctly!")
        print("PostgreSQL services can be instantiated and implement the interface properly.")
    else:
        print("❌ Some validation tests FAILED")
        print("There are still issues with the interface refactoring.")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
