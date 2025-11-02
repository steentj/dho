-- Migration: Add samling (collection) field to books table
-- Created: 2025-10-30
-- Purpose: Track which collection each book belongs to (ww2, slaegt, etc.)

-- Step 1: Create ENUM type for samling values
-- Using ENUM provides type safety and validates values at the database level
-- New collection types can be added later using ALTER TYPE
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'samling_type') THEN
        CREATE TYPE samling_type AS ENUM ('ww2', 'slaegt');
        RAISE NOTICE 'Created samling_type ENUM';
    ELSE
        RAISE NOTICE 'samling_type ENUM already exists - skipping creation';
    END IF;
END $$;

-- Step 2: Add samling column to books table
-- NOT NULL constraint ensures every book has a collection assignment
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'books' 
        AND column_name = 'samling'
    ) THEN
        -- Add column with temporary NULL allowance
        ALTER TABLE books ADD COLUMN samling samling_type;
        
        RAISE NOTICE 'Added samling column to books table';
        
        -- Step 3: Populate existing records based on created_datetime
        -- Books created before October 2025 -> 'ww2'
        -- Books created in/after October 2025 -> 'slaegt'
        UPDATE books 
        SET samling = CASE 
            WHEN created_datetime < '2025-10-01 00:00:00' THEN 'ww2'::samling_type
            ELSE 'slaegt'::samling_type
        END
        WHERE samling IS NULL;
        
        RAISE NOTICE 'Populated samling values for existing books';
        
        -- Step 4: Make column NOT NULL after populating existing records
        ALTER TABLE books ALTER COLUMN samling SET NOT NULL;
        
        RAISE NOTICE 'Set samling column to NOT NULL';
    ELSE
        RAISE NOTICE 'samling column already exists - skipping migration';
    END IF;
END $$;

-- Add index for efficient filtering by collection
CREATE INDEX IF NOT EXISTS books_samling_idx ON books(samling);

-- Add comment to document the field
COMMENT ON COLUMN books.samling IS 'Collection category: ww2 (books before Oct 2025), slaegt (books Oct 2025+)';

-- Note: To add new collection types in the future, use:
-- ALTER TYPE samling_type ADD VALUE 'new_collection_name';
