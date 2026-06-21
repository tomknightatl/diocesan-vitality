-- E2E Test Migration: Add column to existing table
-- This migration tests the schema change workflow

BEGIN;

-- Add a new column to the e2e_test_original table
ALTER TABLE e2e_test_original ADD COLUMN IF NOT EXISTS test_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Add a comment for documentation
COMMENT ON COLUMN e2e_test_original.test_timestamp IS 'Timestamp for E2E testing workflow';

COMMIT;