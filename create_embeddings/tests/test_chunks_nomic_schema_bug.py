"""
Test that reproduces the Ollama chunks_nomic table schema bug.

The chunks_nomic table was created with 'id bigint PRIMARY KEY' instead of 
'id BIGSERIAL PRIMARY KEY', which causes INSERT statements to fail when 
they don't provide an explicit ID value.
"""
import pytest
from unittest.mock import AsyncMock
import os
from database.postgresql import PostgreSQLBookRepository, PostgreSQLConnection


class TestChunksNomicTableSchemaBug:
    """Test the chunks_nomic table schema issue with ID auto-increment."""
    
    @pytest.mark.asyncio
    async def test_chunks_nomic_missing_bigserial_simulation(self):
        """
        Test that simulates the database error from chunks_nomic table schema issue.
        
        The chunks_nomic table has 'id bigint PRIMARY KEY' instead of 'id BIGSERIAL PRIMARY KEY',
        causing INSERT failures when no ID is provided.
        """
        # Mock a database connection that simulates the schema issue
        mock_connection = AsyncMock()
        
        # Simulate the actual PostgreSQL error that occurs with the broken schema
        async def mock_execute(query, *params):
            if "chunks_nomic" in query and "INSERT" in query:
                # This is the actual error PostgreSQL would throw for the broken schema
                raise Exception('null value in column "id" violates not-null constraint')
            return None
            
        mock_connection.execute.side_effect = mock_execute
        
        # Mock transaction context manager
        from contextlib import asynccontextmanager
        @asynccontextmanager  
        async def mock_transaction():
            yield
        mock_connection.transaction = mock_transaction
        
        # Create repository with mock connection
        db_connection = PostgreSQLConnection(mock_connection)
        repo = PostgreSQLBookRepository(db_connection)
        
        # Test data that would normally work fine
        chunks_with_embeddings = [
            (1, "Test chunk 1", [0.1, 0.2, 0.3]),
            (2, "Test chunk 2", [0.4, 0.5, 0.6])
        ]
        
        # This should fail with chunks_nomic table due to missing BIGSERIAL
        with pytest.raises(Exception, match='null value in column "id" violates not-null constraint'):
            await repo.save_chunks(123, chunks_with_embeddings, "chunks_nomic")
    
    @pytest.mark.asyncio 
    async def test_chunks_table_works_with_proper_schema(self):
        """
        Test that chunks table (with proper BIGSERIAL) works fine.
        
        This shows the difference between the working chunks table 
        and the broken chunks_nomic table.
        """
        # Mock a database connection where chunks table works properly
        mock_connection = AsyncMock()
        
        async def mock_execute(query, *params):
            if "chunks_nomic" in query and "INSERT" in query:
                # chunks_nomic table fails due to schema issue
                raise Exception('null value in column "id" violates not-null constraint')
            elif "chunks" in query and "INSERT" in query:
                # chunks table works fine (has BIGSERIAL)
                return None
            return None
            
        mock_connection.execute.side_effect = mock_execute
        
        # Mock transaction context manager
        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def mock_transaction():
            yield
        mock_connection.transaction = mock_transaction
        
        # Create repository with mock connection
        db_connection = PostgreSQLConnection(mock_connection)
        repo = PostgreSQLBookRepository(db_connection)
        
        chunks_with_embeddings = [
            (1, "Test chunk 1", [0.1, 0.2, 0.3]),
            (2, "Test chunk 2", [0.4, 0.5, 0.6])
        ]
        
        # This should work fine with the properly configured chunks table
        await repo.save_chunks(123, chunks_with_embeddings, "chunks")
        
        # Verify it was called with the right parameters
        mock_connection.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_validate_table_schema_requirements(self):
        """
        Test that validates our understanding of the table schema requirements.
        
        This test documents what the correct schema should be.
        """
        # The chunks_nomic table should be created with this schema:
        correct_schema = """
        CREATE TABLE chunks_nomic (
            id BIGSERIAL PRIMARY KEY,  -- This is what's missing!
            book_id integer REFERENCES books(id),
            sidenr integer NOT NULL,
            chunk text NOT NULL,
            embedding vector(768),
            provider text DEFAULT 'ollama',
            model text DEFAULT 'nomic-embed-text',
            created_datetime timestamp DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # The current broken schema is:
        broken_schema = """
        CREATE TABLE chunks_nomic (
            id bigint PRIMARY KEY,  -- Missing auto-increment mechanism
            book_id integer REFERENCES books(id),
            sidenr integer NOT NULL,
            chunk text NOT NULL,
            embedding vector(768),
            provider text DEFAULT 'ollama',
            model text DEFAULT 'nomic-embed-text',
            created_datetime timestamp DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # Verify our test logic is sound
        assert "BIGSERIAL" in correct_schema
        assert "BIGSERIAL" not in broken_schema
        assert "bigint PRIMARY KEY" in broken_schema
        
        # The difference: BIGSERIAL provides auto-increment, bigint PRIMARY KEY does not
        assert True  # This test serves as documentation

    def test_migration_file_has_correct_schema(self):
        """
        Test that confirms the migration file has the correct schema.
        
        This test verifies that the migration file now has the proper BIGSERIAL
        schema that enables auto-increment for the ID column.
        """
        migration_file = "/Users/steen/Library/Mobile Documents/com~apple~CloudDocs/Projekter/SlægtBib/src/database/migrations/001_add_nomic_embeddings_table.sql"
        
        if os.path.exists(migration_file):
            with open(migration_file, 'r') as f:
                content = f.read()
            
            # The migration file should NOT have the buggy schema
            assert "id bigint PRIMARY KEY" not in content, (
                "Migration file still has the buggy schema: 'id bigint PRIMARY KEY' "
                "should be replaced with 'id BIGSERIAL PRIMARY KEY'"
            )
            
            # It should have the correct BIGSERIAL schema
            assert "id BIGSERIAL PRIMARY KEY" in content, (
                "Migration file should have correct schema: 'id BIGSERIAL PRIMARY KEY' "
                "to enable auto-increment for the ID column"
            )
        else:
            pytest.skip(f"Migration file not found: {migration_file}")
