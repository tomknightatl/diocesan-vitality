-- Migration: 003_add_last_extraction_attempt_at.sql
-- Date: 2025-09-13
-- Purpose: Add last_extraction_attempt_at column to DiocesesParishDirectory table
--          to track when parish extraction was last attempted for each diocese

-- Description:
-- This migration adds a timestamp column to track when Step 3 parish extraction
-- was last attempted for each diocese's parish directory. This enables proper
-- prioritization of diocese processing based on extraction recency rather than
-- individual parish timestamps.

BEGIN;

-- Add the new timestamp column
ALTER TABLE "public"."DiocesesParishDirectory"
ADD COLUMN "last_extraction_attempt_at" TIMESTAMP WITH TIME ZONE DEFAULT NULL;

-- Add comment to document the column purpose
COMMENT ON COLUMN "public"."DiocesesParishDirectory"."last_extraction_attempt_at"
IS 'Timestamp of when parish extraction was last attempted for this diocese parish directory';

-- Create index for efficient sorting by extraction attempt date
CREATE INDEX "idx_dioceses_parish_directory_last_extraction_attempt"
ON "public"."DiocesesParishDirectory" ("last_extraction_attempt_at");

-- Add comment to document the index purpose
COMMENT ON INDEX "public"."idx_dioceses_parish_directory_last_extraction_attempt"
IS 'Index for efficient sorting and filtering by last extraction attempt timestamp';

COMMIT;

-- Verification queries (uncomment to run after migration):
-- SELECT column_name, data_type, is_nullable, column_default
-- FROM information_schema.columns
-- WHERE table_name = 'DiocesesParishDirectory' AND column_name = 'last_extraction_attempt_at';
--
-- SELECT indexname, indexdef
-- FROM pg_indexes
-- WHERE tablename = 'DiocesesParishDirectory' AND indexname LIKE '%last_extraction%';