-- Migration: 001_extend_schedule_types.sql
-- Date: 2025-09-13
-- Purpose: Extend ScheduleKeywords table to support 'mass' and 'all' schedule types
--          to enable comprehensive keyword management for mass times extraction

-- Description:
-- This migration modifies the check constraint on the ScheduleKeywords table
-- to allow 'mass' and 'all' as valid schedule_type values, in addition to the
-- existing 'reconciliation', 'adoration', and 'both' types.

BEGIN;

-- Drop the existing check constraint
ALTER TABLE "ScheduleKeywords" 
DROP CONSTRAINT IF EXISTS "ScheduleKeywords_schedule_type_check";

-- Add the new check constraint with expanded allowed values
ALTER TABLE "ScheduleKeywords" 
ADD CONSTRAINT "ScheduleKeywords_schedule_type_check" 
CHECK (schedule_type IN ('reconciliation', 'adoration', 'both', 'mass', 'all'));

-- Add comment to document the change
COMMENT ON CONSTRAINT "ScheduleKeywords_schedule_type_check" ON "ScheduleKeywords" 
IS 'Allows schedule types: reconciliation, adoration, both (shared), mass, all (universal)';

COMMIT;

-- Verification query (uncomment to run after migration):
-- SELECT DISTINCT schedule_type FROM "ScheduleKeywords" ORDER BY schedule_type;