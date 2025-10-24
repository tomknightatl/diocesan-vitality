-- ================================================================
-- Supabase Security Fix - Issue #180
-- ================================================================
-- This script resolves the 5 security warnings from Supabase Security Advisor
-- Created: 2025-10-24
--
-- Issues Fixed:
-- 1. DiscoveredUrls - Missing RLS policies
-- 2. ParishData - Missing RLS policies
-- 3. parishfactssuppressionurls - Missing RLS policies
-- 4. ParishesTestSet - Missing RLS policies
-- 5. diocese_work_assignments & pipeline_workers - Missing RLS
-- 6. Overly permissive "Allow notebook access" policies
-- 7. Views without proper security settings
-- ================================================================

-- ================================================================
-- STEP 1: Add RLS to tables that are missing it
-- ================================================================

-- Enable RLS on pipeline coordination tables
ALTER TABLE public.diocese_work_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pipeline_workers ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE public.diocese_work_assignments IS 'Tracks which worker is processing which diocese to prevent conflicts (RLS enabled)';
COMMENT ON TABLE public.pipeline_workers IS 'Tracks active pipeline worker pods for coordination (RLS enabled)';

-- ================================================================
-- STEP 2: Drop overly permissive policies
-- ================================================================

-- Drop the insecure "Allow notebook access" policies that use USING (true)
DROP POLICY IF EXISTS "Allow notebook access" ON public."DioceseParishDirectoryOverride";
DROP POLICY IF EXISTS "Allow notebook access" ON public."Dioceses";
DROP POLICY IF EXISTS "Allow notebook access" ON public."DiocesesParishDirectory";
DROP POLICY IF EXISTS "Allow notebook access" ON public."Parishes";

-- ================================================================
-- STEP 3: Create secure RLS policies for public read access
-- ================================================================
-- These tables contain public data that should be readable by anyone
-- but only writable by authenticated service role

-- Dioceses: Public read, authenticated write
CREATE POLICY "Public read access for dioceses"
  ON public."Dioceses"
  FOR SELECT
  TO anon, authenticated
  USING (true);

CREATE POLICY "Service role can manage dioceses"
  ON public."Dioceses"
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- DiocesesParishDirectory: Public read, authenticated write
CREATE POLICY "Public read access for parish directories"
  ON public."DiocesesParishDirectory"
  FOR SELECT
  TO anon, authenticated
  USING (true);

CREATE POLICY "Service role can manage parish directories"
  ON public."DiocesesParishDirectory"
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- DioceseParishDirectoryOverride: Service role only (admin data)
CREATE POLICY "Service role can manage directory overrides"
  ON public."DioceseParishDirectoryOverride"
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- Parishes: Public read, authenticated write
CREATE POLICY "Public read access for parishes"
  ON public."Parishes"
  FOR SELECT
  TO anon, authenticated
  USING (true);

CREATE POLICY "Service role can manage parishes"
  ON public."Parishes"
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- ParishData: Public read, authenticated write
CREATE POLICY "Public read access for parish data"
  ON public."ParishData"
  FOR SELECT
  TO anon, authenticated
  USING (true);

CREATE POLICY "Service role can manage parish data"
  ON public."ParishData"
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- DiscoveredUrls: Service role only (internal data)
CREATE POLICY "Service role can manage discovered URLs"
  ON public."DiscoveredUrls"
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- parishfactssuppressionurls: Service role only (configuration data)
CREATE POLICY "Service role can manage suppression URLs"
  ON public.parishfactssuppressionurls
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- ParishesTestSet: Service role only (test data)
CREATE POLICY "Service role can manage test parishes"
  ON public."ParishesTestSet"
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- ================================================================
-- STEP 4: Secure pipeline coordination tables
-- ================================================================
-- These tables are for internal pipeline coordination only

-- diocese_work_assignments: Service role only
CREATE POLICY "Service role can manage work assignments"
  ON public.diocese_work_assignments
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- pipeline_workers: Service role only
CREATE POLICY "Service role can manage pipeline workers"
  ON public.pipeline_workers
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- ================================================================
-- STEP 5: Update views with proper security settings
-- ================================================================

-- Recreate ParishScheduleSummary view with security_invoker (already has it, but ensuring it's correct)
DROP VIEW IF EXISTS public."ParishScheduleSummary";
CREATE VIEW public."ParishScheduleSummary"
WITH (security_invoker='true')
AS
SELECT p.id AS parish_id,
    p."Name" AS parish_name,
    p."Web" AS parish_website,
    p.diocese_id,
    bool_or(
        CASE
            WHEN (((pd.fact_type)::text ~~ '%Adoration%'::text) AND (pd.extraction_method = 'ai_gemini'::text) AND (pd.confidence_score >= 70)) THEN ((pd.ai_structured_data ->> 'has_weekly_schedule'::text))::boolean
            WHEN (((pd.fact_type)::text ~~ '%Adoration%'::text) AND (pd.extraction_method <> 'ai_gemini'::text)) THEN ((pd.fact_value IS NOT NULL) AND (pd.fact_value <> 'Information not found'::text))
            ELSE false
        END) AS has_weekly_adoration,
    max(
        CASE
            WHEN (((pd.fact_type)::text ~~ '%Adoration%'::text) AND (pd.extraction_method = 'ai_gemini'::text)) THEN pd.confidence_score
            WHEN (((pd.fact_type)::text ~~ '%Adoration%'::text) AND (pd.extraction_method <> 'ai_gemini'::text)) THEN 50
            ELSE NULL::integer
        END) AS adoration_confidence,
    max(
        CASE
            WHEN (((pd.fact_type)::text ~~ '%Adoration%'::text) AND (pd.extraction_method = 'ai_gemini'::text)) THEN (pd.ai_structured_data ->> 'frequency'::text)
            ELSE 'unknown'::text
        END) AS adoration_frequency,
    bool_or(
        CASE
            WHEN (((pd.fact_type)::text ~~ '%Reconciliation%'::text) AND (pd.extraction_method = 'ai_gemini'::text) AND (pd.confidence_score >= 70)) THEN ((pd.ai_structured_data ->> 'has_weekly_schedule'::text))::boolean
            WHEN (((pd.fact_type)::text ~~ '%Reconciliation%'::text) AND (pd.extraction_method <> 'ai_gemini'::text)) THEN ((pd.fact_value IS NOT NULL) AND (pd.fact_value <> 'Information not found'::text))
            ELSE false
        END) AS has_weekly_reconciliation,
    max(
        CASE
            WHEN (((pd.fact_type)::text ~~ '%Reconciliation%'::text) AND (pd.extraction_method = 'ai_gemini'::text)) THEN pd.confidence_score
            WHEN (((pd.fact_type)::text ~~ '%Reconciliation%'::text) AND (pd.extraction_method <> 'ai_gemini'::text)) THEN 50
            ELSE NULL::integer
        END) AS reconciliation_confidence,
    max(
        CASE
            WHEN (((pd.fact_type)::text ~~ '%Reconciliation%'::text) AND (pd.extraction_method = 'ai_gemini'::text)) THEN (pd.ai_structured_data ->> 'frequency'::text)
            ELSE 'unknown'::text
        END) AS reconciliation_frequency,
    count(
        CASE
            WHEN (pd.extraction_method = 'ai_gemini'::text) THEN 1
            ELSE NULL::integer
        END) AS ai_extractions,
    count(
        CASE
            WHEN (pd.extraction_method <> 'ai_gemini'::text) THEN 1
            ELSE NULL::integer
        END) AS keyword_extractions,
    max(pd.created_at) AS last_updated
FROM (public."Parishes" p
    LEFT JOIN public."ParishData" pd ON ((p.id = pd.parish_id)))
WHERE (pd.fact_type = ANY (ARRAY['AdorationSchedule'::public.fact_type_enum, 'ReconciliationSchedule'::public.fact_type_enum]))
GROUP BY p.id, p."Name", p."Web", p.diocese_id
ORDER BY (count(
        CASE
            WHEN (pd.extraction_method = 'ai_gemini'::text) THEN 1
            ELSE NULL::integer
        END)) DESC, (max(pd.created_at)) DESC;

COMMENT ON VIEW public."ParishScheduleSummary" IS 'Summary view showing schedule availability for all parishes (security_invoker enabled)';

-- Recreate HighQualitySchedules view with security_invoker
DROP VIEW IF EXISTS public."HighQualitySchedules";
CREATE VIEW public."HighQualitySchedules"
WITH (security_invoker='true')
AS
SELECT pd.id,
    pd.parish_id,
    pd.fact_type,
    pd.fact_value,
    pd.fact_source_url,
    pd.confidence_score,
    pd.extraction_method,
    pd.ai_structured_data,
    pd.created_at,
    p."Name" AS parish_name,
    p."Web" AS parish_website
FROM (public."ParishData" pd
    LEFT JOIN public."Parishes" p ON ((pd.parish_id = p.id)))
WHERE ((pd.extraction_method = 'ai_gemini'::text)
    AND (pd.confidence_score >= 70)
    AND (pd.fact_type = ANY (ARRAY['AdorationSchedule'::public.fact_type_enum, 'ReconciliationSchedule'::public.fact_type_enum])))
ORDER BY pd.confidence_score DESC, pd.created_at DESC;

COMMENT ON VIEW public."HighQualitySchedules" IS 'High-confidence AI-extracted schedule information for parishes (security_invoker enabled)';

-- Recreate ActiveScheduleKeywords view with security_invoker
DROP VIEW IF EXISTS public."ActiveScheduleKeywords";
CREATE VIEW public."ActiveScheduleKeywords"
WITH (security_invoker='true')
AS
SELECT id,
    keyword,
    schedule_type,
    weight,
    is_negative,
    description,
    created_at,
    updated_at
FROM public."ScheduleKeywords"
WHERE (is_active = true)
ORDER BY schedule_type, weight DESC, keyword;

COMMENT ON VIEW public."ActiveScheduleKeywords" IS 'Currently active schedule keywords (security_invoker enabled)';

-- Recreate parishes_with_diocese_name view with security_invoker
DROP VIEW IF EXISTS public.parishes_with_diocese_name;
CREATE VIEW public.parishes_with_diocese_name
WITH (security_invoker='true')
AS
SELECT p.id,
    p.created_at,
    p."Name",
    p."Status",
    p."Deanery",
    p."Street Address",
    p."City",
    p."State",
    p."Zip Code",
    p."Phone Number",
    p."Web",
    p.diocese_url,
    p.parish_directory_url,
    p.extraction_method,
    p.confidence_score,
    p.extracted_at,
    p.parish_detail_url,
    p.full_address,
    p.clergy_info,
    p.service_times,
    p.detail_extraction_success,
    p.detail_extraction_error,
    p.latitude,
    p.longitude,
    p.diocese_id,
    p.is_blocked,
    p.blocking_type,
    p.blocking_evidence,
    p.status_code,
    p.robots_txt_check,
    p.respectful_automation_used,
    p.status_description,
    d."Name" AS diocese_name
FROM (public."Parishes" p
    JOIN public."Dioceses" d ON ((p.diocese_id = d.id)));

COMMENT ON VIEW public.parishes_with_diocese_name IS 'Parishes joined with diocese names (security_invoker enabled)';

-- ================================================================
-- STEP 6: Verify security configuration
-- ================================================================

-- Display security status for review
DO $$
DECLARE
    v_table_name text;
    v_rls_enabled boolean;
    v_policy_count integer;
BEGIN
    RAISE NOTICE '================================================================';
    RAISE NOTICE 'Security Configuration Summary';
    RAISE NOTICE '================================================================';

    FOR v_table_name IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename
    LOOP
        -- Check if RLS is enabled
        SELECT relrowsecurity INTO v_rls_enabled
        FROM pg_class
        WHERE relname = v_table_name
        AND relnamespace = 'public'::regnamespace;

        -- Count policies
        SELECT COUNT(*) INTO v_policy_count
        FROM pg_policies
        WHERE schemaname = 'public'
        AND tablename = v_table_name;

        RAISE NOTICE 'Table: % | RLS: % | Policies: %',
            v_table_name,
            CASE WHEN v_rls_enabled THEN 'ENABLED' ELSE 'DISABLED' END,
            v_policy_count;
    END LOOP;

    RAISE NOTICE '================================================================';
    RAISE NOTICE 'Security fix completed successfully!';
    RAISE NOTICE '================================================================';
END $$;
