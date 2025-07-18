#!/usr/bin/env python3
"""
Script to replace the content of the chunks_nomic table with data from a pg_dump file.

This script connects to the PostgreSQL database specified in the .env file,
truncates the chunks_nomic table, and then restores data from a pg_dump file.

Usage:
    python replace_chunks_nomic_table.py <input_sql_file>

Example:
    python replace_chunks_nomic_table.py nomic_export_sentence_splitter_400.sql

The input file should be created with a command like:
    pg_dump -h localhost -p 5433 -U steen -d WW2 -t chunks_nomic > nomic_export_sentence_splitter_400.sql
"""

import os
import sys
import asyncio
import asyncpg
import logging
from pathlib import Path
from dotenv import load_dotenv


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_database_config():
    """Load database configuration from .env file."""
    # Look for .env file in parent directories
    current_dir = Path(__file__).parent
    env_file = None
    
    # Search up the directory tree for .env file
    for parent in [current_dir, current_dir.parent, current_dir.parent.parent]:
        potential_env = parent / '.env'
        if potential_env.exists():
            env_file = potential_env
            break
    
    if env_file:
        load_dotenv(env_file)
        logger.info(f"Loaded .env file from: {env_file}")
    else:
        logger.warning("No .env file found, using environment variables")
    
    # Extract database configuration
    config = {
        'host': os.getenv('POSTGRES_HOST'),
        'user': os.getenv('POSTGRES_USER'),
        'password': os.getenv('POSTGRES_PASSWORD'),
        'database': os.getenv('POSTGRES_DB'),
        'port': int(os.getenv('POSTGRES_PORT', 5432))
    }
    
    # Validate required configuration
    missing_vars = [key for key, value in config.items() if value is None]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {missing_vars}")
    
    return config


def construct_database_url(config):
    """Construct PostgreSQL connection URL from config."""
    return f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"


async def connect_to_database(database_url):
    """Connect to PostgreSQL database."""
    try:
        connection = await asyncpg.connect(database_url)
        logger.info("Successfully connected to database")
        return connection
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


async def table_exists(connection, table_name):
    """Check if a table exists in the database."""
    query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = $1
        );
    """
    result = await connection.fetchval(query, table_name)
    return result


async def truncate_table(connection, table_name):
    """Truncate the specified table."""
    try:
        logger.info(f"Truncating table: {table_name}")
        await connection.execute(f"TRUNCATE TABLE {table_name} CASCADE;")
        logger.info(f"Successfully truncated table: {table_name}")
    except Exception as e:
        logger.error(f"Failed to truncate table {table_name}: {e}")
        raise


async def execute_sql_file(connection, sql_file_path):
    """Execute SQL commands from a file."""
    try:
        logger.info(f"Reading SQL file: {sql_file_path}")
        
        with open(sql_file_path, 'r', encoding='utf-8') as file:
            sql_content = file.read()
        
        if not sql_content.strip():
            raise ValueError("SQL file is empty")
        
        logger.info(f"Executing SQL content ({len(sql_content)} characters)")
        
        # Split by statements and execute each one
        # Note: This is a simple approach - more complex parsing might be needed for complex dumps
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        for i, statement in enumerate(statements):
            if statement:
                try:
                    await connection.execute(statement)
                    if i % 100 == 0:  # Log progress every 100 statements
                        logger.info(f"Executed {i+1}/{len(statements)} statements")
                except Exception as e:
                    logger.warning(f"Failed to execute statement {i+1}: {e}")
                    logger.debug(f"Statement: {statement[:200]}...")
                    # Continue with other statements
        
        logger.info(f"Successfully executed {len(statements)} SQL statements")
        
    except Exception as e:
        logger.error(f"Failed to execute SQL file: {e}")
        raise


async def get_table_count(connection, table_name):
    """Get the number of rows in a table."""
    try:
        count = await connection.fetchval(f"SELECT COUNT(*) FROM {table_name};")
        return count
    except Exception as e:
        logger.warning(f"Failed to get count for table {table_name}: {e}")
        return None


async def main():
    """Main function to replace chunks_nomic table content."""
    if len(sys.argv) != 2:
        print("Usage: python replace_chunks_nomic_table.py <input_sql_file>")
        print("Example: python replace_chunks_nomic_table.py nomic_export_sentence_splitter_400.sql")
        sys.exit(1)
    
    sql_file_path = sys.argv[1]
    
    # Validate input file
    if not os.path.exists(sql_file_path):
        logger.error(f"Input SQL file not found: {sql_file_path}")
        sys.exit(1)
    
    try:
        # Load database configuration
        logger.info("Loading database configuration...")
        config = load_database_config()
        database_url = construct_database_url(config)
        
        # Connect to database
        logger.info("Connecting to database...")
        connection = await connect_to_database(database_url)
        
        try:
            # Check if chunks_nomic table exists
            table_name = "chunks_nomic"
            if not await table_exists(connection, table_name):
                logger.error(f"Table {table_name} does not exist in the database")
                sys.exit(1)
            
            # Get initial row count
            initial_count = await get_table_count(connection, table_name)
            if initial_count is not None:
                logger.info(f"Initial row count in {table_name}: {initial_count}")
            
            # Truncate existing table
            await truncate_table(connection, table_name)
            
            # Execute SQL file to restore data
            logger.info("Restoring data from SQL file...")
            await execute_sql_file(connection, sql_file_path)
            
            # Get final row count
            final_count = await get_table_count(connection, table_name)
            if final_count is not None:
                logger.info(f"Final row count in {table_name}: {final_count}")
            
            logger.info("Successfully replaced chunks_nomic table content!")
            
        finally:
            await connection.close()
            logger.info("Database connection closed")
            
    except Exception as e:
        logger.error(f"Script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
