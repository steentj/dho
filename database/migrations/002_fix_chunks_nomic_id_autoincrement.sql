-- Migration: Fix chunks_nomic table ID column to enable auto-increment
-- Created: 2025-07-06
-- Purpose: Fix the schema bug where id was 'bigint PRIMARY KEY' instead of 'BIGSERIAL PRIMARY KEY'

-- This migration fixes the chunks_nomic table that was created with the wrong schema
-- The original migration used 'id bigint PRIMARY KEY' which doesn't auto-increment
-- This caused INSERT failures when saving book chunks with Ollama provider

-- Check if chunks_nomic table exists and has the buggy schema
-- If the column is already BIGSERIAL, this migration can be safely skipped

DO $$
BEGIN
    -- Check if chunks_nomic table exists and has wrong schema
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'chunks_nomic'
    ) THEN
        -- Check if the id column lacks auto-increment (not SERIAL/BIGSERIAL)
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'chunks_nomic' 
            AND column_name = 'id' 
            AND column_default IS NULL  -- SERIAL columns have a default
        ) THEN
            RAISE NOTICE 'Fixing chunks_nomic table schema - adding auto-increment to id column';
            
            -- Step 1: Create a sequence for the id column
            CREATE SEQUENCE IF NOT EXISTS chunks_nomic_id_seq;
            
            -- Step 2: Set the sequence ownership to the id column
            ALTER SEQUENCE chunks_nomic_id_seq OWNED BY chunks_nomic.id;
            
            -- Step 3: Set the default value for id column to use the sequence
            ALTER TABLE chunks_nomic ALTER COLUMN id SET DEFAULT nextval('chunks_nomic_id_seq');
            
            -- Step 4: If there are existing rows, set the sequence to the max id + 1
            PERFORM setval('chunks_nomic_id_seq', COALESCE((SELECT MAX(id) FROM chunks_nomic), 0) + 1, false);
            
            RAISE NOTICE 'chunks_nomic table id column fixed - now has auto-increment capability';
        ELSE
            RAISE NOTICE 'chunks_nomic table id column already has auto-increment - no fix needed';
        END IF;
    ELSE
        RAISE NOTICE 'chunks_nomic table does not exist - no fix needed';
    END IF;
END $$;

-- Add comment to document the fix
COMMENT ON COLUMN chunks_nomic.id IS 'Auto-incrementing primary key (fixed from bigint to BIGSERIAL behavior)';
