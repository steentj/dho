"""
Database factory for creating database components.

This module provides a simple factory interface for creating
database components based on configuration.
"""
import os
from typing import Dict, Type

from .interfaces import DatabaseFactory
from .postgresql import PostgreSQLDatabaseFactory


class DatabaseFactoryRegistry:
    """Registry for database factory implementations."""
    
    _factories: Dict[str, Type[DatabaseFactory]] = {
        "postgresql": PostgreSQLDatabaseFactory,
    }
    
    @classmethod
    def register_factory(cls, name: str, factory_class: Type[DatabaseFactory]) -> None:
        """Register a new database factory."""
        cls._factories[name] = factory_class
    
    @classmethod
    def create_factory(cls, database_type: str = None, **kwargs) -> DatabaseFactory:
        """Create a database factory based on configuration."""
        if database_type is None:
            database_type = os.getenv("DATABASE_TYPE", "postgresql")
        
        if database_type not in cls._factories:
            raise ValueError(f"Unknown database type: {database_type}")
        
        factory_class = cls._factories[database_type]
        return factory_class(**kwargs)
    
    @classmethod
    def get_available_types(cls) -> list:
        """Get list of available database types."""
        return list(cls._factories.keys())


# Convenience function for creating database factories
def create_database_factory(database_type: str = None, **kwargs) -> DatabaseFactory:
    """Create a database factory based on configuration."""
    return DatabaseFactoryRegistry.create_factory(database_type, **kwargs)
