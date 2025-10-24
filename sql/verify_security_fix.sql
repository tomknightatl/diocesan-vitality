-- ================================================================
-- Security Fix Verification Script - Issue #180
-- ================================================================
-- Run this script AFTER applying fix_security_issues.sql
-- to verify all security controls are properly configured
-- ================================================================

-- Show all tables with their RLS status and policy count
SELECT
    t.tablename,
    CASE WHEN c.relrowsecurity THEN '✅ ENABLED' ELSE '❌ DISABLED' END as rls_status,
    COALESCE(COUNT(DISTINCT pol.polname), 0) as policy_count,
    STRING_AGG(DISTINCT pol.polname, ', ' ORDER BY pol.polname) as policies
FROM pg_tables t
LEFT JOIN pg_class c ON c.relname = t.tablename AND c.relnamespace = 'public'::regnamespace
LEFT JOIN pg_policies pol ON pol.tablename = t.tablename AND pol.schemaname = 'public'
WHERE t.schemaname = 'public'
GROUP BY t.tablename, c.relrowsecurity
ORDER BY t.tablename;

-- Show detailed policy information
SELECT
    schemaname,
    tablename,
    policyname,
    CASE
        WHEN roles::text = '{public}' THEN 'Public'
        WHEN roles::text LIKE '%anon%' THEN 'Anonymous'
        WHEN roles::text LIKE '%authenticated%' THEN 'Authenticated'
        WHEN roles::text LIKE '%service_role%' THEN 'Service Role'
        ELSE roles::text
    END as applies_to,
    cmd as operation,
    qual as using_expression,
    with_check as check_expression
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;

-- Check for any tables missing policies
SELECT
    'SECURITY ISSUE' as alert_type,
    t.tablename,
    'RLS enabled but no policies defined - table is inaccessible' as issue
FROM pg_tables t
LEFT JOIN pg_class c ON c.relname = t.tablename AND c.relnamespace = 'public'::regnamespace
LEFT JOIN (
    SELECT tablename, COUNT(*) as policy_count
    FROM pg_policies
    WHERE schemaname = 'public'
    GROUP BY tablename
) p ON p.tablename = t.tablename
WHERE t.schemaname = 'public'
AND c.relrowsecurity = true
AND COALESCE(p.policy_count, 0) = 0;

-- Check for any tables without RLS
SELECT
    'SECURITY WARNING' as alert_type,
    t.tablename,
    'RLS is disabled - table is publicly accessible' as issue
FROM pg_tables t
LEFT JOIN pg_class c ON c.relname = t.tablename AND c.relnamespace = 'public'::regnamespace
WHERE t.schemaname = 'public'
AND (c.relrowsecurity IS NULL OR c.relrowsecurity = false);

-- Check for overly permissive policies
SELECT
    'SECURITY WARNING' as alert_type,
    tablename,
    policyname,
    'Overly permissive policy - allows unrestricted access' as issue
FROM pg_policies
WHERE schemaname = 'public'
AND (
    policyname ILIKE '%allow%access%'
    OR (qual = 'true' AND with_check = 'true' AND cmd = '*')
);

-- Show view security settings
SELECT
    viewname,
    CASE
        WHEN viewname IN (
            SELECT viewname FROM pg_views
            WHERE schemaname = 'public'
            AND definition LIKE '%security_invoker%true%'
        )
        THEN '✅ security_invoker=true'
        ELSE '⚠️ No security_invoker set'
    END as security_setting
FROM pg_views
WHERE schemaname = 'public'
ORDER BY viewname;

-- Final summary
DO $$
DECLARE
    v_tables_count integer;
    v_rls_enabled_count integer;
    v_policies_count integer;
    v_issues_count integer;
BEGIN
    RAISE NOTICE '================================================================';
    RAISE NOTICE 'SECURITY CONFIGURATION SUMMARY';
    RAISE NOTICE '================================================================';

    -- Count total tables
    SELECT COUNT(*) INTO v_tables_count
    FROM pg_tables
    WHERE schemaname = 'public';

    -- Count tables with RLS enabled
    SELECT COUNT(*) INTO v_rls_enabled_count
    FROM pg_tables t
    LEFT JOIN pg_class c ON c.relname = t.tablename AND c.relnamespace = 'public'::regnamespace
    WHERE t.schemaname = 'public'
    AND c.relrowsecurity = true;

    -- Count total policies
    SELECT COUNT(*) INTO v_policies_count
    FROM pg_policies
    WHERE schemaname = 'public';

    -- Count tables with issues
    SELECT COUNT(*) INTO v_issues_count
    FROM pg_tables t
    LEFT JOIN pg_class c ON c.relname = t.tablename AND c.relnamespace = 'public'::regnamespace
    LEFT JOIN (
        SELECT tablename, COUNT(*) as policy_count
        FROM pg_policies
        WHERE schemaname = 'public'
        GROUP BY tablename
    ) p ON p.tablename = t.tablename
    WHERE t.schemaname = 'public'
    AND (
        (c.relrowsecurity = true AND COALESCE(p.policy_count, 0) = 0)
        OR c.relrowsecurity = false
    );

    RAISE NOTICE 'Total Tables: %', v_tables_count;
    RAISE NOTICE 'Tables with RLS Enabled: %', v_rls_enabled_count;
    RAISE NOTICE 'Total Security Policies: %', v_policies_count;
    RAISE NOTICE 'Tables with Security Issues: %', v_issues_count;
    RAISE NOTICE '';

    IF v_issues_count = 0 THEN
        RAISE NOTICE '✅ SECURITY STATUS: SECURE';
        RAISE NOTICE 'All tables have proper RLS configuration and policies.';
    ELSE
        RAISE NOTICE '❌ SECURITY STATUS: ISSUES FOUND';
        RAISE NOTICE 'Please review the security warnings above.';
    END IF;

    RAISE NOTICE '================================================================';
END $$;
