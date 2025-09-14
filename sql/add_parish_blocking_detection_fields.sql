-- Add blocking detection fields to Parishes table
-- This tracks when parishes are blocking automated access

-- Add new columns for blocking detection
ALTER TABLE public."Parishes"
ADD COLUMN IF NOT EXISTS is_blocked BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS blocking_type TEXT,
ADD COLUMN IF NOT EXISTS blocking_evidence JSONB,
ADD COLUMN IF NOT EXISTS status_code INTEGER,
ADD COLUMN IF NOT EXISTS robots_txt_check JSONB,
ADD COLUMN IF NOT EXISTS respectful_automation_used BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS status_description TEXT;

-- Create indexes for blocking queries
CREATE INDEX IF NOT EXISTS idx_parishes_blocked ON public."Parishes"(is_blocked);
CREATE INDEX IF NOT EXISTS idx_parishes_blocking_type ON public."Parishes"(blocking_type);
CREATE INDEX IF NOT EXISTS idx_parishes_respectful_automation ON public."Parishes"(respectful_automation_used);

-- Add comments for documentation
COMMENT ON COLUMN public."Parishes".is_blocked IS 'Whether the parish website is blocking automated access';
COMMENT ON COLUMN public."Parishes".blocking_type IS 'Type of blocking detected (403_forbidden, cloudflare_protection, etc.)';
COMMENT ON COLUMN public."Parishes".blocking_evidence IS 'JSON object with evidence for blocking detection';
COMMENT ON COLUMN public."Parishes".status_code IS 'HTTP status code received';
COMMENT ON COLUMN public."Parishes".robots_txt_check IS 'JSON object with robots.txt compliance check results';
COMMENT ON COLUMN public."Parishes".respectful_automation_used IS 'Whether respectful automation practices were used';
COMMENT ON COLUMN public."Parishes".status_description IS 'Human-readable description of blocking status';

-- Create a view for blocked parishes
CREATE OR REPLACE VIEW public."BlockedParishes" AS
SELECT
    p.id as parish_id,
    p."Name" as parish_name,
    p."Web" as parish_url,
    p.diocese_url,
    p.is_blocked,
    p.blocking_type,
    p.status_code,
    p.status_description,
    p.blocking_evidence,
    p.extracted_at as last_tested
FROM public."Parishes" p
WHERE p.is_blocked = true AND p.respectful_automation_used = true
ORDER BY p.extracted_at DESC;

-- Create a view for parish accessibility summary
CREATE OR REPLACE VIEW public."ParishesAccessibilitySummary" AS
SELECT
    COUNT(*) as total_parishes_tested,
    COUNT(CASE WHEN p.is_blocked = true THEN 1 END) as blocked_parishes,
    COUNT(CASE WHEN p.is_blocked = false THEN 1 END) as accessible_parishes,
    COUNT(CASE WHEN p.blocking_type = '403_forbidden' THEN 1 END) as forbidden_403,
    COUNT(CASE WHEN p.blocking_type = 'cloudflare_protection' THEN 1 END) as cloudflare_blocked,
    COUNT(CASE WHEN p.blocking_type = 'rate_limited' THEN 1 END) as rate_limited,
    COUNT(CASE WHEN p.blocking_type = 'robots_txt_disallowed' THEN 1 END) as robots_txt_blocked,
    COUNT(CASE WHEN p.respectful_automation_used = true THEN 1 END) as respectful_automation_used,
    ROUND(
        (COUNT(CASE WHEN p.is_blocked = true THEN 1 END) * 100.0 / NULLIF(COUNT(CASE WHEN p.respectful_automation_used = true THEN 1 END), 0)), 1
    ) as blocking_percentage
FROM public."Parishes" p
WHERE p.respectful_automation_used = true;

COMMENT ON VIEW public."BlockedParishes" IS 'List of parishes that are blocking automated access';
COMMENT ON VIEW public."ParishesAccessibilitySummary" IS 'Summary statistics of parish website accessibility for automated access';

-- Sample queries to check blocking status:
/*
-- Get all blocked parishes
SELECT * FROM public."BlockedParishes";

-- Get accessibility summary
SELECT * FROM public."ParishesAccessibilitySummary";

-- Get blocking breakdown by type
SELECT
    blocking_type,
    COUNT(*) as count,
    ROUND((COUNT(*) * 100.0 / SUM(COUNT(*)) OVER ()), 1) as percentage
FROM public."Parishes"
WHERE is_blocked = true AND respectful_automation_used = true
GROUP BY blocking_type
ORDER BY count DESC;

-- Get parishes by diocese blocking status
SELECT
    diocese_url,
    COUNT(*) as total_parishes,
    COUNT(CASE WHEN is_blocked = true THEN 1 END) as blocked_count,
    ROUND((COUNT(CASE WHEN is_blocked = true THEN 1 END) * 100.0 / COUNT(*)), 1) as blocking_percentage
FROM public."Parishes"
WHERE respectful_automation_used = true
GROUP BY diocese_url
ORDER BY blocking_percentage DESC;
*/