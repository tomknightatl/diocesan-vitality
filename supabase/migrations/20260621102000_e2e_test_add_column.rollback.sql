-- Rollback for E2E Test Migration: Add column to existing table
-- This migration rolls back the schema change

BEGIN;

-- Remove the test_timestamp column from e2e_test_original table
ALTER TABLE e2e_test_original DROP COLUMN IF EXISTS test_timestamp;

COMMIT;