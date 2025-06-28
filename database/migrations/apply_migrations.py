#!/usr/bin/env python3
"""Script to apply database migrations for the embedding system."""
import asyncio
import asyncpg
import os
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def apply_migrations(conn):
    """Apply all migration files in order."""
    # Create migrations table if it doesn't exist
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS migrations (
            id serial PRIMARY KEY,
            filename text NOT NULL,
            applied_at timestamp DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Get list of applied migrations
    applied = await conn.fetch('SELECT filename FROM migrations')
    applied_files = {row['filename'] for row in applied}
    
    # Get all migration files
    migrations_dir = Path(__file__).parent
    migration_files = sorted([f for f in migrations_dir.glob('*.sql')])
    
    for migration_file in migration_files:
        if migration_file.name in applied_files:
            logger.info(f"Skipping already applied migration: {migration_file.name}")
            continue
            
        logger.info(f"Applying migration: {migration_file.name}")
        try:
            # Read and execute migration
            sql = migration_file.read_text()
            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    'INSERT INTO migrations (filename) VALUES ($1)',
                    migration_file.name
                )
            logger.info(f"Successfully applied migration: {migration_file.name}")
        except Exception as e:
            logger.error(f"Error applying migration {migration_file.name}: {e}")
            raise

async def main():
    """Main entry point for migration script."""
    # Get database connection parameters from environment
    db_host = os.getenv('POSTGRES_HOST', 'localhost')
    db_port = os.getenv('POSTGRES_PORT', '5432')
    db_name = os.getenv('POSTGRES_DB', 'slaegtbib')
    db_user = os.getenv('POSTGRES_USER', 'postgres')
    db_pass = os.getenv('POSTGRES_PASSWORD', '')
    
    try:
        # Connect to database
        conn = await asyncpg.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_pass
        )
        
        logger.info("Connected to database, applying migrations...")
        await apply_migrations(conn)
        logger.info("All migrations applied successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        if 'conn' in locals():
            await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
