"""
Unit tests for database factory.
"""
import pytest
from unittest.mock import patch, AsyncMock
from database.factory import DatabaseFactoryRegistry, create_database_factory
from database.interfaces import DatabaseFactory
from database.postgresql import PostgreSQLDatabaseFactory


class TestDatabaseFactoryRegistry:
    """Test database factory registry functionality."""
    
    def test_registry_has_postgresql_factory(self):
        """Test that registry has PostgreSQL factory registered."""
        assert "postgresql" in DatabaseFactoryRegistry._factories
        assert DatabaseFactoryRegistry._factories["postgresql"] == PostgreSQLDatabaseFactory
    
    def test_register_factory(self):
        """Test registering a new factory."""
        class MockFactory(DatabaseFactory):
            async def create_connection(self):
                pass
            def create_book_repository(self, connection):
                pass
            def create_search_repository(self, connection):
                pass
        
        # Store original state
        original_factories = DatabaseFactoryRegistry._factories.copy()
        
        try:
            DatabaseFactoryRegistry.register_factory("mock", MockFactory)
            assert "mock" in DatabaseFactoryRegistry._factories
            assert DatabaseFactoryRegistry._factories["mock"] == MockFactory
        finally:
            # Restore original state
            DatabaseFactoryRegistry._factories = original_factories
    
    @patch.dict('os.environ', {'TESTING': 'true'})
    def test_create_factory_postgresql(self):
        """Test creating PostgreSQL factory."""
        factory = DatabaseFactoryRegistry.create_factory("postgresql")
        assert isinstance(factory, PostgreSQLDatabaseFactory)
    
    @patch.dict('os.environ', {'DATABASE_TYPE': 'postgresql', 'TESTING': 'true'})
    def test_create_factory_from_env(self):
        """Test creating factory from environment variable."""
        factory = DatabaseFactoryRegistry.create_factory()
        assert isinstance(factory, PostgreSQLDatabaseFactory)
    
    @patch.dict('os.environ', {'TESTING': 'true'}, clear=True)
    def test_create_factory_default(self):
        """Test creating factory with default type."""
        factory = DatabaseFactoryRegistry.create_factory()
        assert isinstance(factory, PostgreSQLDatabaseFactory)  # Default is postgresql
    
    def test_create_factory_invalid_type(self):
        """Test creating factory with invalid type."""
        with pytest.raises(ValueError, match="Unknown database type: invalid"):
            DatabaseFactoryRegistry.create_factory("invalid")
    
    def test_get_available_types(self):
        """Test getting available database types."""
        types = DatabaseFactoryRegistry.get_available_types()
        assert isinstance(types, list)
        assert "postgresql" in types
    
    @patch.dict('os.environ', {'TESTING': 'true'})
    def test_create_factory_with_kwargs(self):
        """Test creating factory with keyword arguments."""
        factory = DatabaseFactoryRegistry.create_factory("postgresql", some_param="value")
        assert isinstance(factory, PostgreSQLDatabaseFactory)


class TestCreateDatabaseFactory:
    """Test convenience function for creating database factories."""
    
    @patch.dict('os.environ', {'TESTING': 'true'})
    def test_create_database_factory_postgresql(self):
        """Test creating PostgreSQL factory via convenience function."""
        factory = create_database_factory("postgresql")
        assert isinstance(factory, PostgreSQLDatabaseFactory)
    
    @patch.dict('os.environ', {'DATABASE_TYPE': 'postgresql', 'TESTING': 'true'})
    def test_create_database_factory_from_env(self):
        """Test creating factory from environment via convenience function."""
        factory = create_database_factory()
        assert isinstance(factory, PostgreSQLDatabaseFactory)
    
    def test_create_database_factory_invalid_type(self):
        """Test creating factory with invalid type via convenience function."""
        with pytest.raises(ValueError, match="Unknown database type: invalid"):
            create_database_factory("invalid")
    
    @patch.dict('os.environ', {'TESTING': 'true'})
    def test_create_database_factory_with_kwargs(self):
        """Test creating factory with kwargs via convenience function."""
        factory = create_database_factory("postgresql", some_param="value")
        assert isinstance(factory, PostgreSQLDatabaseFactory)


class TestDatabaseFactoryIntegration:
    """Integration tests for database factory system."""
    
    @pytest.mark.asyncio
    @patch('asyncpg.connect')
    @patch.dict('os.environ', {'TESTING': 'true'})
    async def test_full_factory_workflow(self, mock_connect):
        """Test complete factory workflow."""
        # Setup mocks
        mock_asyncpg_conn = AsyncMock()
        mock_connect.return_value = mock_asyncpg_conn
        
        # Create factory
        factory = create_database_factory("postgresql")
        
        # Test connection creation
        with patch.dict('os.environ', {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'test_db',
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_pass'
        }):
            conn = await factory.create_connection()
        
        # Create repositories
        book_repo = factory.create_book_repository(conn)
        search_repo = factory.create_search_repository(conn)
        
        # Verify all components are created and linked
        assert conn is not None
        assert book_repo is not None
        assert search_repo is not None
        assert book_repo._connection == conn
        assert search_repo._connection == conn
    
    @patch.dict('os.environ', {'TESTING': 'true'})
    def test_factory_consistency(self):
        """Test that factory creates consistent objects."""
        # Create two factories of the same type
        factory1 = create_database_factory("postgresql")
        factory2 = DatabaseFactoryRegistry.create_factory("postgresql")
        
        # They should be the same type
        assert type(factory1) is type(factory2)
        assert isinstance(factory1, PostgreSQLDatabaseFactory)
        assert isinstance(factory2, PostgreSQLDatabaseFactory)
    
    def test_registry_state_isolation(self):
        """Test that registry modifications don't affect other tests."""
        # Get original state
        original_count = len(DatabaseFactoryRegistry._factories)
        
        # Register a temporary factory
        class TempFactory(DatabaseFactory):
            async def create_connection(self):
                pass
            def create_book_repository(self, connection):
                pass
            def create_search_repository(self, connection):
                pass
        
        DatabaseFactoryRegistry.register_factory("temp", TempFactory)
        assert len(DatabaseFactoryRegistry._factories) == original_count + 1
        
        # Remove temporary factory
        del DatabaseFactoryRegistry._factories["temp"]
        assert len(DatabaseFactoryRegistry._factories) == original_count
    
    @patch.dict('os.environ', {'DATABASE_TYPE': 'postgresql', 'TESTING': 'true'})
    def test_environment_based_factory_creation(self):
        """Test that environment variables properly influence factory creation."""
        # Test with environment variable set
        factory = create_database_factory()
        assert isinstance(factory, PostgreSQLDatabaseFactory)
        
        # Test explicit override
        factory2 = create_database_factory("postgresql")
        assert isinstance(factory2, PostgreSQLDatabaseFactory)
        assert type(factory) is type(factory2)


class TestDatabaseFactoryErrorHandling:
    """Test error handling in database factory system."""
    
    def test_invalid_database_type_error_message(self):
        """Test that invalid database type gives clear error message."""
        with pytest.raises(ValueError) as exc_info:
            create_database_factory("nonexistent")
        
        assert "Unknown database type: nonexistent" in str(exc_info.value)
    
    def test_registry_create_factory_error_propagation(self):
        """Test that errors in factory creation are properly propagated."""
        # Store original state
        original_factories = DatabaseFactoryRegistry._factories.copy()
        
        try:
            # Register a factory that raises an error during instantiation
            class ErrorFactory(DatabaseFactory):
                def __init__(self, **kwargs):
                    raise RuntimeError("Factory initialization failed")
                
                async def create_connection(self):
                    pass
                def create_book_repository(self, connection):
                    pass
                def create_search_repository(self, connection):
                    pass
            
            DatabaseFactoryRegistry.register_factory("error", ErrorFactory)
            
            with pytest.raises(RuntimeError, match="Factory initialization failed"):
                DatabaseFactoryRegistry.create_factory("error")
        
        finally:
            # Restore original state
            DatabaseFactoryRegistry._factories = original_factories
