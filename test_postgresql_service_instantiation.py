#!/usr/bin/env python3
"""
Quick test to check if PostgreSQLService can be instantiated
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from database.postgresql_service import PostgreSQLService
    print("✅ Successfully imported PostgreSQLService")
    
    # Try to instantiate
    service = PostgreSQLService()
    print("✅ Successfully instantiated PostgreSQLService")
    print(f"Service type: {type(service)}")
    
    # Check if it has the required methods
    has_save_method = hasattr(service, 'save_book_with_chunks')
    has_exists_method = hasattr(service, 'book_exists_with_provider')
    
    print(f"✅ Has save_book_with_chunks: {has_save_method}")
    print(f"✅ Has book_exists_with_provider: {has_exists_method}")
    
    if has_save_method and has_exists_method:
        print("✅ SUCCESS: PostgreSQLService implements interface correctly")
    else:
        print("❌ FAILURE: Missing interface methods")
        
except Exception as e:
    print(f"❌ FAILURE: {e}")
    import traceback
    traceback.print_exc()
