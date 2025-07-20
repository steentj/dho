#!/usr/bin/env python3
"""
Test to validate Refactoring 4: Eliminate Service Type Detection

This test verifies that the service type detection has been properly eliminated
from opret_bøger.py and that the code now uses a unified service interface.
"""

import ast
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

def test_service_type_detection_eliminated():
    """Test that service type detection has been removed from opret_bøger.py"""
    
    # Read the refactored file
    script_path = os.path.join(os.path.dirname(__file__), 'create_embeddings', 'opret_bøger.py')
    with open(script_path, 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    # Parse the AST to analyze the code structure
    tree = ast.parse(source_code)
    
    # Find the main function (it's async)
    main_function = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == 'main':
            main_function = node
            break
    
    assert main_function is not None, "main() function not found"
    
    # Check that the problematic service type detection patterns are gone
    main_source = ast.unparse(main_function)
    
    # 1. No USE_POOL_SERVICE environment variable checking
    assert 'USE_POOL_SERVICE' not in main_source, \
        "USE_POOL_SERVICE environment variable detection should be removed"
    
    # 2. No use_pool_service variable
    assert 'use_pool_service' not in main_source, \
        "use_pool_service variable should be eliminated"
    
    # 3. No service_to_use variable (unified interface)
    assert 'service_to_use' not in main_source, \
        "service_to_use variable should be eliminated - use unified interface"
    
    # 4. No pool_service as a separate variable (but comments/function names are ok)
    lines = main_source.split('\n')
    pool_service_lines = [line for line in lines if 'pool_service' in line and not line.strip().startswith('#')]
    pool_service_assignments = [line for line in pool_service_lines if '=' in line and 'pool_service' in line.split('=')[0]]
    assert len(pool_service_assignments) == 0, \
        f"pool_service should not be used as a separate variable, found: {pool_service_assignments}"
    
    # 5. Verify unified service usage
    assert 'book_service' in main_source, \
        "Should use unified book_service variable"
    
    # 6. Verify it uses the pool service (which implements IBookService)
    assert 'create_postgresql_pool_service' in main_source, \
        "Should use PostgreSQL pool service as the unified implementation"
    
    # 7. No conditional database factory creation logic
    assert 'create_database_factory' not in main_source, \
        "Should not have conditional database factory creation"
    
    print("✅ Service type detection successfully eliminated!")
    print("✅ Unified service interface is being used!")
    print("✅ PostgreSQL pool service is the default implementation!")
    

def test_process_book_interface_consistency():
    """Test that process_book function uses the unified interface"""
    
    script_path = os.path.join(os.path.dirname(__file__), 'create_embeddings', 'opret_bøger.py')
    with open(script_path, 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    tree = ast.parse(source_code)
    
    # Find the process_book function (it's async)
    process_book_function = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == 'process_book':
            process_book_function = node
            break
    
    assert process_book_function is not None, "process_book() function not found"
    
    # Verify it takes book_service parameter (not pool_or_service)
    param_names = [arg.arg for arg in process_book_function.args.args]
    assert 'book_service' in param_names, \
        "process_book should take book_service parameter"
    
    # Verify it doesn't have the old complex service detection logic
    process_book_source = ast.unparse(process_book_function)
    assert 'hasattr' not in process_book_source, \
        "process_book should not use hasattr() for service detection"
    
    print("✅ process_book function uses unified interface!")


def test_import_and_basic_functionality():
    """Test that the refactored module can be imported and basic functions work"""
    
    try:
        # Test import
        from create_embeddings.opret_bøger import main, process_book, parse_book, save_book
        
        # Test that functions are callable
        assert callable(main), "main should be callable"
        assert callable(process_book), "process_book should be callable" 
        assert callable(parse_book), "parse_book should be callable"
        assert callable(save_book), "save_book should be callable"
        
        print("✅ All functions are importable and callable!")
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        raise
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        raise


if __name__ == '__main__':
    test_service_type_detection_eliminated()
    test_process_book_interface_consistency()
    test_import_and_basic_functionality()
    print("\n🎉 Refactoring 4: Eliminate Service Type Detection - COMPLETED SUCCESSFULLY! 🎉")
    print("\nChanges made:")
    print("- ❌ Removed USE_POOL_SERVICE environment variable detection")
    print("- ❌ Eliminated use_pool_service conditional logic") 
    print("- ❌ Removed service_to_use variable and complex service type detection")
    print("- ❌ Eliminated separate pool_service and book_service variables")
    print("- ❌ Removed conditional database factory creation logic")
    print("- ✅ Unified to use PostgreSQL pool service as the single implementation")
    print("- ✅ All services now use the same IBookService interface")
    print("- ✅ Polymorphism is properly utilized - no runtime type checking needed")
