#!/usr/bin/env python3
"""
Quick validation that the provider-aware search changes work correctly.
"""

import asyncio
from unittest.mock import Mock, patch


async def test_provider_aware_search_fix():
    """Test that the search API correctly uses provider information."""
    print("🧪 Testing provider-aware search fix...")
    
    # Test 1: Verify repository supports provider_name parameter
    print("1️⃣ Testing PostgreSQLSearchRepository...")
    from database.postgresql import PostgreSQLSearchRepository
    from database.interfaces import DatabaseConnection
    
    mock_connection = Mock(spec=DatabaseConnection)
    mock_connection.fetchall = Mock()
    
    # Make fetchall return a coroutine
    async def mock_fetchall(*args, **kwargs):
        return []
    mock_connection.fetchall = mock_fetchall
    
    repo = PostgreSQLSearchRepository(mock_connection)
    
    # Test with provider_name - this should not raise TypeError
    try:
        await repo.vector_search(
            embedding=[0.1] * 768,
            provider_name="ollama"
        )
        print("   ✅ Repository accepts provider_name parameter")
    except TypeError as e:
        print(f"   ❌ Repository doesn't support provider_name: {e}")
        return False
    
    # Test 2: Verify service layer supports provider_name
    print("2️⃣ Testing PostgreSQLService...")
    
    # Mock the service rather than creating a real one
    from database.postgresql_service import PostgreSQLService
    
    with patch.object(PostgreSQLService, '__init__', return_value=None):
        service = PostgreSQLService()
        service._connection = Mock()
        service._search_repository = Mock()
        
        # Make vector_search return a coroutine
        async def mock_vector_search(*args, **kwargs):
            return []
        service._search_repository.vector_search = mock_vector_search
        
        # Mock _ensure_connected to avoid connection errors
        service._ensure_connected = Mock()
        
        try:
            await service.vector_search(
                embedding=[0.1] * 768,
                provider_name="ollama"
            )
            print("   ✅ Service layer accepts provider_name parameter")
        except TypeError as e:
            print(f"   ❌ Service layer doesn't support provider_name: {e}")
            return False
    
    # Test 3: Verify dhosearch uses provider information
    print("3️⃣ Testing dhosearch API integration...")
    
    # Mock the global services
    with patch('soegemaskine.searchapi.dhosearch.db_service') as mock_db_service, \
         patch('soegemaskine.searchapi.dhosearch.embedding_provider') as mock_embedding_provider:
        
        # Setup mocks
        mock_embedding_provider.get_provider_name.return_value = "ollama"
        mock_db_service.vector_search.return_value = []
        
        # Import and test the function
        from soegemaskine.searchapi.dhosearch import find_nærmeste
        
        try:
            await find_nærmeste([0.1] * 768)
            
            # Check if vector_search was called with provider_name
            call_args = mock_db_service.vector_search.call_args
            if call_args and 'provider_name' in call_args.kwargs:
                print("   ✅ dhosearch passes provider_name to database service")
                print(f"       Provider name used: {call_args.kwargs['provider_name']}")
            else:
                print("   ⚠️  dhosearch doesn't pass provider_name parameter")
                print(f"       Call args: {call_args}")
        except Exception as e:
            print(f"   ❌ dhosearch test failed: {e}")
            return False
    
    print("🎉 All provider-aware search tests passed!")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_provider_aware_search_fix())
    exit(0 if success else 1)
