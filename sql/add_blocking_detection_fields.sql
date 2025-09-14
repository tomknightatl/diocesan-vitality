-- Add blocking detection fields to DiocesesParishDirectory table
-- This tracks when dioceses are blocking automated access

-- Add new columns for blocking detection
ALTER TABLE public."DiocesesParishDirectory"
ADD COLUMN IF NOT EXISTS is_blocked BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS blocking_type TEXT,
ADD COLUMN IF NOT EXISTS blocking_evidence JSONB,
ADD COLUMN IF NOT EXISTS status_code INTEGER,
ADD COLUMN IF NOT EXISTS robots_txt_check JSONB,
ADD COLUMN IF NOT EXISTS respectful_automation_used BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS status_description TEXT;

-- Create index for blocking queries
CREATE INDEX IF NOT EXISTS idx_dioceses_parish_directory_blocked ON public."DiocesesParishDirectory"(is_blocked);
CREATE INDEX IF NOT EXISTS idx_dioceses_parish_directory_blocking_type ON public."DiocesesParishDirectory"(blocking_type);

-- Add comments for documentation
COMMENT ON COLUMN public."DiocesesParishDirectory".is_blocked IS 'Whether the diocese website is blocking automated access';
COMMENT ON COLUMN public."DiocesesParishDirectory".blocking_type IS 'Type of blocking detected (403_forbidden, cloudflare_protection, etc.)';
COMMENT ON COLUMN public."DiocesesParishDirectory".blocking_evidence IS 'JSON array of evidence for blocking detection';
COMMENT ON COLUMN public."DiocesesParishDirectory".status_code IS 'HTTP status code received';
COMMENT ON COLUMN public."DiocesesParishDirectory".robots_txt_check IS 'JSON object with robots.txt compliance check results';
COMMENT ON COLUMN public."DiocesesParishDirectory".respectful_automation_used IS 'Whether respectful automation practices were used';
COMMENT ON COLUMN public."DiocesesParishDirectory".status_description IS 'Human-readable description of blocking status';

-- Create a view for blocked dioceses
CREATE OR REPLACE VIEW public."BlockedDioceses" AS
SELECT
    d.id as diocese_id,
    d."Name" as diocese_name,
    d."Website" as diocese_url,
    dpd.parish_directory_url,
    dpd.is_blocked,
    dpd.blocking_type,
    dpd.status_code,
    dpd.status_description,
    dpd.blocking_evidence,
    dpd.updated_at
FROM public."Dioceses" d
LEFT JOIN public."DiocesesParishDirectory" dpd ON d.id = dpd.diocese_id
WHERE dpd.is_blocked = true
ORDER BY dpd.updated_at DESC;

-- Create a view for diocese accessibility summary
CREATE OR REPLACE VIEW public."DiocesesAccessibilitySummary" AS
SELECT
    COUNT(*) as total_dioceses_tested,
    COUNT(CASE WHEN dpd.is_blocked = true THEN 1 END) as blocked_dioceses,
    COUNT(CASE WHEN dpd.is_blocked = false THEN 1 END) as accessible_dioceses,
    COUNT(CASE WHEN dpd.blocking_type = '403_forbidden' THEN 1 END) as forbidden_403,
    COUNT(CASE WHEN dpd.blocking_type = 'cloudflare_protection' THEN 1 END) as cloudflare_blocked,
    COUNT(CASE WHEN dpd.blocking_type = 'rate_limited' THEN 1 END) as rate_limited,
    COUNT(CASE WHEN dpd.respectful_automation_used = true THEN 1 END) as respectful_automation_used,
    ROUND(
        (COUNT(CASE WHEN dpd.is_blocked = true THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0)), 1
    ) as blocking_percentage
FROM public."DiocesesParishDirectory" dpd;

COMMENT ON VIEW public."BlockedDioceses" IS 'List of dioceses that are blocking automated access';
COMMENT ON VIEW public."DiocesesAccessibilitySummary" IS 'Summary statistics of diocese website accessibility for automated access';

-- Sample queries to check blocking status:
/*
-- Get all blocked dioceses
SELECT * FROM public."BlockedDioceses";

-- Get accessibility summary
SELECT * FROM public."DiocesesAccessibilitySummary";

-- Get blocking breakdown by type
SELECT
    blocking_type,
    COUNT(*) as count,
    ROUND((COUNT(*) * 100.0 / SUM(COUNT(*)) OVER ()), 1) as percentage
FROM public."DiocesesParishDirectory"
WHERE is_blocked = true
GROUP BY blocking_type
ORDER BY count DESC;
*/