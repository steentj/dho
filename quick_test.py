"""
Simple test script to validate that our PostgreSQL services can be imported and instantiated.
This addresses the core issue from the test failures.
"""

def test_basic_imports():
    """Test basic imports work."""
    try:
        from database.postgresql_service import PostgreSQLService, PostgreSQLPoolService, BookService
        print("SUCCESS: All PostgreSQL services imported successfully")
        return True
    except Exception as e:
        print(f"FAILED: Import error: {e}")
        return False

def test_instantiation():
    """Test that services can be instantiated (the core failing test)."""
    try:
        from database.postgresql_service import PostgreSQLService
        
        # This was failing before - PostgreSQL being abstract
        service = PostgreSQLService()
        print("SUCCESS: PostgreSQLService instantiated successfully")
        return True
    except Exception as e:
        print(f"FAILED: Instantiation error: {e}")
        return False

if __name__ == "__main__":
    print("=== Basic Interface Validation ===")
    
    success = True
    success &= test_basic_imports() 
    success &= test_instantiation()
    
    if success:
        print("✅ Basic validation PASSED - Interface refactoring looks good!")
    else:
        print("❌ Basic validation FAILED - Still have issues")
