"""
Database package for DHO Semantic Search System.

This package provides database interfaces and implementations
with dependency injection support.
"""
from .interfaces import (
    DatabaseConnection,
    BookRepository, 
    SearchRepository,
    DatabaseFactory
)
from .factory import create_database_factory, DatabaseFactoryRegistry
from .postgresql import (
    PostgreSQLConnection,
    PostgreSQLBookRepository,
    PostgreSQLSearchRepository,
    PostgreSQLDatabaseFactory
)

__all__ = [
    # Interfaces
    "DatabaseConnection",
    "BookRepository", 
    "SearchRepository", 
    "DatabaseFactory",
    
    # Factory
    "create_database_factory",
    "DatabaseFactoryRegistry",
    
    # PostgreSQL implementations
    "PostgreSQLConnection",
    "PostgreSQLBookRepository", 
    "PostgreSQLSearchRepository",
    "PostgreSQLDatabaseFactory",
]
