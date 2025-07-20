"""
Comprehensive validation script for Refactoring 1: Extract Service Interface

This script validates that:
1. Magic string detection has been eliminated from opret_bøger.py
2. PostgreSQLService classes can be instantiated (not abstract)
3. Service interface is working correctly
4. All key refactoring goals have been achieved

Run with: python comprehensive_interface_validation.py
"""
import sys
import traceback
import inspect
from pathlib import Path

# Add parent directory to path for absolute imports
sys.path.insert(0, str(Path(__file__).parent))

def test_magic_string_elimination():
    """Test that magic string detection (hasattr) has been eliminated."""
    print("🧪 Testing magic string elimination...")
    
    try:
        from create_embeddings.opret_bøger import save_book, process_book
        
        # Get source code of key functions
        save_book_source = inspect.getsource(save_book)
        process_book_source = inspect.getsource(process_book)
        
        # Check that hasattr() calls are gone
        hasattr_count_save = save_book_source.count("hasattr(")
        hasattr_count_process = process_book_source.count("hasattr(")
        
        if hasattr_count_save > 0:
            print(f"❌ Found {hasattr_count_save} hasattr() calls in save_book - magic strings not eliminated")
            return False
        
        if hasattr_count_process > 0:
            print(f"❌ Found {hasattr_count_process} hasattr() calls in process_book - magic strings not eliminated")
            return False
            
        print("✅ Magic string detection (hasattr) successfully eliminated from core functions")
        return True
        
    except Exception as e:
        print(f"❌ Failed to test magic string elimination: {e}")
        traceback.print_exc()
        return False

def test_interface_creation():
    """Test that IBookService interface exists and is properly defined."""
    print("\n🧪 Testing interface creation...")
    
    try:
        from create_embeddings.book_service_interface import IBookService
        
        # Verify it's an abstract base class
        from abc import ABC
        if not issubclass(IBookService, ABC):
            print("❌ IBookService is not an ABC - interface incorrectly defined")
            return False
            
        # Verify required abstract methods exist
        abstract_methods = IBookService.__abstractmethods__
        expected_methods = {'save_book_with_chunks', 'book_exists_with_provider'}
        
        if abstract_methods != expected_methods:
            print(f"❌ Interface has wrong abstract methods. Expected: {expected_methods}, Got: {abstract_methods}")
            return False
            
        print("✅ IBookService interface correctly defined with proper abstract methods")
        return True
        
    except Exception as e:
        print(f"❌ Failed to test interface creation: {e}")
        traceback.print_exc()
        return False

def test_service_implementation():
    """Test that PostgreSQL services implement the interface and are instantiable."""
    print("\n🧪 Testing service implementation...")
    
    try:
        from database.postgresql_service import PostgreSQLService, PostgreSQLPoolService
        from create_embeddings.book_service_interface import IBookService
        
        # Check inheritance
        if not issubclass(PostgreSQLService, IBookService):
            print("❌ PostgreSQLService does not implement IBookService")
            return False
            
        if not issubclass(PostgreSQLPoolService, IBookService):
            print("❌ PostgreSQLPoolService does not implement IBookService")
            return False
        
        # Test instantiation - this was the core failing test
        try:
            service = PostgreSQLService()
            print("✅ PostgreSQLService() instantiated successfully")
        except TypeError as e:
            if "abstract" in str(e).lower():
                print(f"❌ PostgreSQLService still abstract: {e}")
                return False
            else:
                print(f"❌ PostgreSQLService instantiation failed: {e}")
                return False
        
        try:
            pool_service = PostgreSQLPoolService()
            print("✅ PostgreSQLPoolService() instantiated successfully")
        except TypeError as e:
            if "abstract" in str(e).lower():
                print(f"❌ PostgreSQLPoolService still abstract: {e}")
                return False
            else:
                print(f"❌ PostgreSQLPoolService instantiation failed: {e}")
                return False
        
        # Verify required methods exist
        required_methods = ['save_book_with_chunks', 'book_exists_with_provider']
        for method in required_methods:
            if not hasattr(service, method):
                print(f"❌ PostgreSQLService missing required method: {method}")
                return False
            if not inspect.iscoroutinefunction(getattr(service, method)):
                print(f"❌ PostgreSQLService.{method} is not async")
                return False
        
        print("✅ All PostgreSQL services implement interface correctly and are instantiable")
        return True
        
    except Exception as e:
        print(f"❌ Failed to test service implementation: {e}")
        traceback.print_exc()
        return False

def test_interface_usage():
    """Test that opret_bøger.py uses the new interface correctly."""
    print("\n🧪 Testing interface usage...")
    
    try:
        from create_embeddings.opret_bøger import save_book, process_book
        
        # Get source code
        save_book_source = inspect.getsource(save_book)
        process_book_source = inspect.getsource(process_book)
        
        # Check for interface method usage
        if 'save_book_with_chunks' not in save_book_source:
            print("❌ save_book() not using save_book_with_chunks interface method")
            return False
            
        if 'book_exists_with_provider' not in process_book_source:
            print("❌ process_book() not using book_exists_with_provider interface method")
            return False
        
        # Check that _save_book_with_repository is gone (simplified architecture)
        if '_save_book_with_repository' in save_book_source:
            print("❌ _save_book_with_repository still exists - architecture not simplified")
            return False
        
        print("✅ opret_bøger.py correctly uses new interface methods")
        return True
        
    except Exception as e:
        print(f"❌ Failed to test interface usage: {e}")
        traceback.print_exc()
        return False

def test_backward_compatibility():
    """Test that BookService wrapper maintains backward compatibility."""
    print("\n🧪 Testing backward compatibility...")
    
    try:
        from database.postgresql_service import BookService, PostgreSQLService
        
        # Test wrapper instantiation
        mock_service = PostgreSQLService()
        wrapper = BookService(mock_service)
        
        # Verify wrapper has expected methods
        if not hasattr(wrapper, 'save_book'):
            print("❌ BookService wrapper missing save_book method")
            return False
        
        print("✅ BookService wrapper maintains backward compatibility")
        return True
        
    except Exception as e:
        print(f"❌ Failed to test backward compatibility: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all validation tests."""
    print("🔍 COMPREHENSIVE INTERFACE REFACTORING VALIDATION")
    print("=" * 60)
    
    tests = [
        test_magic_string_elimination,
        test_interface_creation,
        test_service_implementation,
        test_interface_usage,
        test_backward_compatibility
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - REFACTORING 1 COMPLETED SUCCESSFULLY!")
        print("\nRefactoring 1 achievements:")
        print("✅ Magic string detection eliminated")
        print("✅ Clean service interface created")
        print("✅ PostgreSQL services implement interface")
        print("✅ Services are instantiable (not abstract)")
        print("✅ Backward compatibility maintained")
        print("✅ Code architecture simplified")
        return 0
    else:
        print(f"❌ {total - passed} tests failed - refactoring incomplete")
        return 1

if __name__ == "__main__":
    sys.exit(main())
