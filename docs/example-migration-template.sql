-- Migration: 20260621150000_add_parish_contact_preferences.sql
-- Description: Add contact preferences table for parishes with RLS policies
-- Author: Development Team
-- Date: 2026-06-21
-- JIRA Ticket: DV-123

-- ============================================================================
-- SCHEMA CHANGES
-- ============================================================================

-- Create parish contact preferences table
CREATE TABLE IF NOT EXISTS public.parish_contact_preferences (
    id UUID DEFAULT extensions.uuid_generate_v4() NOT NULL PRIMARY KEY,
    parish_id BIGINT NOT NULL,
    preferred_contact_method TEXT NOT NULL DEFAULT 'email',
    email_notifications BOOLEAN DEFAULT true,
    sms_notifications BOOLEAN DEFAULT false,
    phone_notifications BOOLEAN DEFAULT false,
    preferred_contact_times TEXT[] DEFAULT ARRAY['9:00-17:00']::TEXT[],
    do_not_contact BOOLEAN DEFAULT false,
    contact_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    -- Constraints
    CONSTRAINT parish_contact_preferences_parish_id_fkey 
        FOREIGN KEY (parish_id) REFERENCES public."Parishes"(id) ON DELETE CASCADE,
    CONSTRAINT check_preferred_contact_method 
        CHECK (preferred_contact_method IN ('email', 'sms', 'phone', 'mail')),
    CONSTRAINT check_at_least_one_notification 
        CHECK (email_notifications OR sms_notifications OR phone_notifications OR do_not_contact)
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Primary index for parish lookups
CREATE INDEX idx_parish_contact_preferences_parish_id 
    ON public.parish_contact_preferences(parish_id);

-- Index for contact method filtering
CREATE INDEX idx_parish_contact_preferences_method 
    ON public.parish_contact_preferences(preferred_contact_method);

-- Index for do_not_contact filtering
CREATE INDEX idx_parish_contact_preferences_do_not_contact 
    ON public.parish_contact_preferences(do_not_contact) 
    WHERE do_not_contact = false;

-- Composite index for notification queries
CREATE INDEX idx_parish_contact_preferences_notifications 
    ON public.parish_contact_preferences(email_notifications, sms_notifications, phone_notifications);

-- GIN index for array searches
CREATE INDEX idx_parish_contact_preferences_times 
    ON public.parish_contact_preferences USING GIN (preferred_contact_times);

-- ============================================================================
-- COMMENTS
-- ============================================================================

-- Table comment
COMMENT ON TABLE public.parish_contact_preferences IS 
    'Stores contact preferences for each parish to manage communication channels and timing';

-- Column comments
COMMENT ON COLUMN public.parish_contact_preferences.id IS 
    'Unique identifier for the contact preference record';

COMMENT ON COLUMN public.parish_contact_preferences.parish_id IS 
    'Foreign key reference to the Parishes table';

COMMENT ON COLUMN public.parish_contact_preferences.preferred_contact_method IS 
    'Primary method for contacting the parish: email, sms, phone, or mail';

COMMENT ON COLUMN public.parish_contact_preferences.email_notifications IS 
    'Whether the parish accepts email notifications';

COMMENT ON COLUMN public.parish_contact_preferences.sms_notifications IS 
    'Whether the parish accepts SMS notifications';

COMMENT ON COLUMN public.parish_contact_preferences.phone_notifications IS 
    'Whether the parish accepts phone notifications';

COMMENT ON COLUMN public.parish_contact_preferences.preferred_contact_times IS 
    'Array of preferred time ranges for contact (e.g., ["9:00-12:00", "14:00-17:00"])';

COMMENT ON COLUMN public.parish_contact_preferences.do_not_contact IS 
    'If true, parish has opted out of all communications';

COMMENT ON COLUMN public.parish_contact_preferences.contact_notes IS 
    'Additional notes about contact preferences or special instructions';

-- Index comments
COMMENT ON INDEX idx_parish_contact_preferences_parish_id IS 
    'Index for efficient parish lookups';

COMMENT ON INDEX idx_parish_contact_preferences_do_not_contact IS 
    'Partial index for active contacts only';

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Create trigger function for updated_at
CREATE OR REPLACE FUNCTION public.update_parish_contact_preferences_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add trigger to table
CREATE TRIGGER update_parish_contact_preferences_updated_at_trigger
    BEFORE UPDATE ON public.parish_contact_preferences
    FOR EACH ROW
    EXECUTE FUNCTION public.update_parish_contact_preferences_updated_at();

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

-- Enable RLS on the table
ALTER TABLE public.parish_contact_preferences ENABLE ROW LEVEL SECURITY;

-- Policy: Allow read access for authenticated users
CREATE POLICY "Enable read access for authenticated users on parish_contact_preferences"
    ON public.parish_contact_preferences
    FOR SELECT
    TO authenticated
    USING (true);

-- Policy: Allow insert for authenticated users
CREATE POLICY "Enable insert for authenticated users on parish_contact_preferences"
    ON public.parish_contact_preferences
    FOR INSERT
    TO authenticated
    WITH CHECK (true);

-- Policy: Allow update for authenticated users
CREATE POLICY "Enable update for authenticated users on parish_contact_preferences"
    ON public.parish_contact_preferences
    FOR UPDATE
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Policy: Allow delete for service role only
CREATE POLICY "Enable delete for service role on parish_contact_preferences"
    ON public.parish_contact_preferences
    FOR DELETE
    TO service_role
    USING (true);

-- ============================================================================
-- DATA MIGRATION (if applicable)
-- ============================================================================

-- Note: This is a new table, so no data migration is needed.
-- If migrating existing data, use the following pattern:

-- Step 1: Add nullable column
-- ALTER TABLE existing_table ADD COLUMN new_column TEXT;

-- Step 2: Migrate existing data
-- UPDATE existing_table 
-- SET new_column = 
--     CASE 
--         WHEN old_condition THEN 'value1'
--         ELSE 'value2'
--     END;

-- Step 3: Add constraints after data migration
-- ALTER TABLE existing_table 
-- ALTER COLUMN new_column SET NOT NULL,
-- ADD CONSTRAINT check_new_column CHECK (new_column IN ('value1', 'value2'));

-- ============================================================================
-- VIEWS (if applicable)
-- ============================================================================

-- Create view for active contact preferences
CREATE OR REPLACE VIEW public.active_parish_contact_preferences AS
SELECT 
    pcp.id,
    pcp.parish_id,
    p."Name" AS parish_name,
    p."Web" AS parish_website,
    pcp.preferred_contact_method,
    pcp.email_notifications,
    pcp.sms_notifications,
    pcp.phone_notifications,
    pcp.preferred_contact_times,
    pcp.contact_notes,
    pcp.created_at,
    pcp.updated_at
FROM public.parish_contact_preferences pcp
INNER JOIN public."Parishes" p ON pcp.parish_id = p.id
WHERE pcp.do_not_contact = false;

-- Add comment to view
COMMENT ON VIEW public.active_parish_contact_preferences IS 
    'View showing contact preferences for parishes that have not opted out';

-- ============================================================================
-- GRANTS (if needed)
-- ============================================================================

-- Grant usage on schema (if not already granted)
-- GRANT USAGE ON SCHEMA public TO authenticated, anon;

-- Grant select on view
-- GRANT SELECT ON public.active_parish_contact_preferences TO authenticated, anon;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Run these queries after migration to verify success:

-- Check table exists
-- SELECT EXISTS (
--     SELECT FROM information_schema.tables 
--     WHERE table_schema = 'public' 
--     AND table_name = 'parish_contact_preferences'
-- );

-- Check indexes exist
-- SELECT indexname, indexdef 
-- FROM pg_indexes 
-- WHERE tablename = 'parish_contact_preferences';

-- Check RLS is enabled
-- SELECT relname, relrowsecurity 
-- FROM pg_class 
-- WHERE relname = 'parish_contact_preferences';

-- Check policies exist
-- SELECT policyname, permissive, roles, cmd, qual 
-- FROM pg_policies 
-- WHERE tablename = 'parish_contact_preferences';

-- Check row count (should be 0 for new table)
-- SELECT COUNT(*) FROM parish_contact_preferences;

-- ============================================================================
-- ROLLBACK SCRIPT
-- ============================================================================

-- To rollback this migration, execute:

-- DROP VIEW IF EXISTS public.active_parish_contact_preferences CASCADE;
-- DROP TRIGGER IF EXISTS update_parish_contact_preferences_updated_at_trigger ON public.parish_contact_preferences;
-- DROP FUNCTION IF EXISTS public.update_parish_contact_preferences_updated_at();
-- DROP TABLE IF EXISTS public.parish_contact_preferences CASCADE;

-- ============================================================================
-- TESTING NOTES
-- ============================================================================

-- Manual Testing Steps:
-- 1. Insert test record:
--    INSERT INTO parish_contact_preferences (parish_id, preferred_contact_method)
--    VALUES (1, 'email');
--
-- 2. Verify trigger works:
--    UPDATE parish_contact_preferences SET contact_notes = 'Test note' WHERE parish_id = 1;
--    SELECT updated_at FROM parish_contact_preferences WHERE parish_id = 1;
--
-- 3. Test constraints:
--    INSERT INTO parish_contact_preferences (parish_id, preferred_contact_method, email_notifications, sms_notifications, phone_notifications, do_not_contact)
--    VALUES (2, 'invalid', false, false, false, false);
--    -- Should fail: violates check_preferred_contact_method constraint
--
-- 4. Test RLS policies:
--    -- Connect as authenticated user and try operations
--    SELECT * FROM parish_contact_preferences;
--    INSERT INTO parish_contact_preferences (parish_id, preferred_contact_method) VALUES (3, 'phone');
--
-- 5. Test view:
--    SELECT * FROM active_parish_contact_preferences;
--
-- 6. Test cascade delete:
--    DELETE FROM "Parishes" WHERE id = 1;
--    SELECT * FROM parish_contact_preferences WHERE parish_id = 1;
--    -- Should return 0 rows

-- Automated Testing:
-- Run pytest tests/test_migration_parish_contact_preferences.py

-- ============================================================================
-- PERFORMANCE CONSIDERATIONS
-- ============================================================================

-- 1. Indexes are created for common query patterns
-- 2. Partial index on do_not_contact reduces index size
-- 3. GIN index for array searches on preferred_contact_times
-- 4. Foreign key has ON DELETE CASCADE for automatic cleanup
-- 5. Consider adding composite indexes based on actual query patterns

-- ============================================================================
-- DEPLOYMENT NOTES
-- ============================================================================

-- 1. This migration is backward compatible (new table only)
-- 2. No application changes required immediately
-- 3. Can be deployed during business hours
-- 4. Monitor table size and query performance after deployment
-- 5. Consider adding data validation in application layer

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================