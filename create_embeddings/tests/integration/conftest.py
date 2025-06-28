"""
Test fixtures for integration tests.
"""
import os
import sys
from pathlib import Path

import asyncpg
import pytest
import pytest_asyncio

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from create_embeddings.providers import EmbeddingProviderFactory

# Load test environment variables
def load_test_env():
    """Load environment variables from .env.test file if it exists."""
    env_test_path = Path(__file__).parent.parent.parent / '.env.test'
    if env_test_path.exists():
        with open(env_test_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    if key not in os.environ:
                        os.environ[key] = value

# Load test environment first
load_test_env()

# Set default environment variables for integration tests, forcing test values
TEST_ENV = {
    'POSTGRES_USER': 'postgres',
    'POSTGRES_PASSWORD': 'postgres', 
    'POSTGRES_HOST': 'localhost',
    'POSTGRES_PORT': '5432',
    'POSTGRES_DB': 'test_db'
}

# Force test environment variables for integration tests
for key, value in TEST_ENV.items():
    os.environ[key] = value

# Debug function to help troubleshoot VS Code test runner issues
def debug_environment():
    """Print environment info for debugging VS Code test issues."""
    print(f"Current working directory: {os.getcwd()}")
    print(f"POSTGRES_HOST: {os.getenv('POSTGRES_HOST')}")
    print(f"POSTGRES_PORT: {os.getenv('POSTGRES_PORT')}")
    print(f"POSTGRES_USER: {os.getenv('POSTGRES_USER')}")
    print(f"POSTGRES_DB: {os.getenv('POSTGRES_DB')}")

# Uncomment the next line if you need to debug environment issues in VS Code
# debug_environment()

@pytest_asyncio.fixture(scope="function")
async def test_db():
    """Create test database and return connection."""
    import uuid
    
    # Use environment variables with fallback to default localhost
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    dbname = os.getenv("POSTGRES_DB", "test_db")
    
    # Create a unique database name for each test to avoid conflicts
    unique_dbname = f"{dbname}_{uuid.uuid4().hex[:8]}"
    unique_conn_str = f"postgresql://{user}:{password}@{host}:{port}/{unique_dbname}"
    
    sys_conn = None
    conn = None
    
    try:
        # Connect to postgres system database first
        sys_conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database="postgres"
        )
        
        # Create unique test database
        await sys_conn.execute(f'CREATE DATABASE {unique_dbname}')
        
    except Exception as e:
        if sys_conn:
            await sys_conn.close()
        error_msg = (f"PostgreSQL not available at {host}:{port}: {e}. "
                    f"Integration tests require PostgreSQL to be running. "
                    f"Settings: POSTGRES_USER={user} POSTGRES_HOST={host} POSTGRES_PORT={port}. "
                    f"VS Code users: Check that environment variables are properly set in VS Code settings.")
        pytest.skip(error_msg)
    
    try:
        # Connect to the unique test database
        conn = await asyncpg.connect(unique_conn_str)
        
        # Create schema
        await conn.execute('''
            CREATE EXTENSION IF NOT EXISTS vector;
            
            CREATE TABLE IF NOT EXISTS books (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS chunks_nomic (
                id BIGINT PRIMARY KEY,
                book_id INTEGER REFERENCES books(id),
                sidenr INTEGER NOT NULL,
                chunk TEXT NOT NULL,
                embedding TEXT,
                provider VARCHAR(50) DEFAULT 'ollama',
                model VARCHAR(50) DEFAULT 'nomic-embed-text',
                created_datetime TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        
        yield conn
        
    except Exception as e:
        if conn:
            await conn.close()
        if sys_conn:
            await sys_conn.close()
        pytest.skip(f"Cannot connect to test database: {e}")
    
    finally:
        # Cleanup: close connection and drop test database
        if conn:
            try:
                await conn.close()
            except Exception as e:
                print(f"Error closing connection: {e}")
        
        if sys_conn:
            try:
                # Terminate connections to the test database
                await sys_conn.execute(f'''
                    SELECT pg_terminate_backend(pg_stat_activity.pid)
                    FROM pg_stat_activity
                    WHERE pg_stat_activity.datname = '{unique_dbname}'
                    AND pid <> pg_backend_pid();
                ''')
                # Drop the test database
                await sys_conn.execute(f'DROP DATABASE IF EXISTS {unique_dbname}')
                await sys_conn.close()
            except Exception as e:
                print(f"Error during cleanup: {e}")

def check_postgres_available():
    """Check if PostgreSQL is available with current configuration."""
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    
    import socket
    try:
        # Test basic connectivity
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False

@pytest_asyncio.fixture
async def test_book_chunks():
    """Sample book chunks for testing."""
    return [
        "This is the first chapter of the test book.",
        "Here is the second chapter with different content.",
        "Finally, this is the conclusion of our test book."
    ]

@pytest_asyncio.fixture(scope="function")
async def ollama_provider():
    """Create an Ollama embedding provider for testing."""
    # For integration tests, use dummy provider to avoid connection issues
    # unless OLLAMA_BASE_URL is explicitly set to a working instance
    ollama_url = os.getenv("OLLAMA_BASE_URL")
    if ollama_url and ollama_url != "http://localhost:11434":
        # Use real Ollama provider if URL is explicitly set to non-localhost
        provider = EmbeddingProviderFactory.create_provider('ollama')
        provider.base_url = ollama_url
        async with provider:
            yield provider
    else:
        # Use dummy provider for testing when Ollama is not available
        provider = EmbeddingProviderFactory.create_provider('dummy')
        yield provider

@pytest_asyncio.fixture(scope="function")
async def dummy_provider():
    """Create a dummy embedding provider for testing."""
    provider = EmbeddingProviderFactory.create_provider('dummy')
    yield provider
