-- Migration: Add Nomic embeddings table
-- Created: 2025-06-27

-- Enable pgvector extension if not already enabled
CREATE EXTENSION IF NOT EXISTS vector;

-- Create chunks_nomic table for 768-dimensional embeddings
CREATE TABLE IF NOT EXISTS chunks_nomic (
    id bigint PRIMARY KEY,
    book_id integer REFERENCES books(id),
    sidenr integer NOT NULL,
    chunk text NOT NULL,
    embedding vector(768),
    provider text DEFAULT 'ollama',
    model text DEFAULT 'nomic-embed-text',
    created_datetime timestamp DEFAULT CURRENT_TIMESTAMP
);

-- Create index on the embedding vector for similarity search
-- Using HNSW for optimal query performance in read-heavy workload
CREATE INDEX IF NOT EXISTS chunks_nomic_embedding_idx ON chunks_nomic 
USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Add permissions
GRANT SELECT, INSERT, UPDATE ON chunks_nomic TO steen;

-- Add comments
COMMENT ON TABLE chunks_nomic IS 'Stores text chunks and their 768-dimensional embeddings from Nomic Embed Text V2';
COMMENT ON COLUMN chunks_nomic.embedding IS '768-dimensional embedding vector from Nomic model';
COMMENT ON COLUMN chunks_nomic.provider IS 'Embedding provider (ollama)';
COMMENT ON COLUMN chunks_nomic.model IS 'Model used for embedding (nomic-embed-text)';
