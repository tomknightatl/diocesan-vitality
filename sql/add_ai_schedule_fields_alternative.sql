-- Alternative approach: Add AI schedule fields without relying on enum constraints
-- This approach uses existing fact_type values with AI indicators in other fields

-- Add new columns for AI extraction metadata
ALTER TABLE public."ParishData" 
ADD COLUMN IF NOT EXISTS confidence_score integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS extraction_method text DEFAULT 'keyword_based',
ADD COLUMN IF NOT EXISTS ai_structured_data jsonb;

-- Create indexes for the new fields
CREATE INDEX IF NOT EXISTS idx_parish_data_confidence ON public."ParishData"(confidence_score);
CREATE INDEX IF NOT EXISTS idx_parish_data_extraction_method ON public."ParishData"(extraction_method);
CREATE INDEX IF NOT EXISTS idx_parish_data_ai_structured_data ON public."ParishData" USING GIN (ai_structured_data);

-- Create a view for high-quality AI-extracted schedules (using existing fact_type values)
CREATE OR REPLACE VIEW public."HighQualitySchedules" AS
SELECT 
    pd.id,
    pd.parish_id,
    pd.fact_type,
    pd.fact_value,
    pd.fact_source_url,
    pd.confidence_score,
    pd.extraction_method,
    pd.ai_structured_data,
    pd.created_at,
    p."Name" as parish_name,
    p."Web" as parish_website
FROM public."ParishData" pd
LEFT JOIN public."Parishes" p ON pd.parish_id = p.id
WHERE pd.extraction_method = 'ai_gemini' 
AND pd.confidence_score >= 70
AND pd.fact_type IN ('AdorationSchedule', 'ReconciliationSchedule')
ORDER BY pd.confidence_score DESC, pd.created_at DESC;

-- Create a summary view for schedule availability
CREATE OR REPLACE VIEW public."ParishScheduleSummary" AS
SELECT 
    p.id as parish_id,
    p."Name" as parish_name,
    p."Web" as parish_website,
    p.diocese_id as diocese_id,
    
    -- Adoration schedule info (AI and keyword-based)
    BOOL_OR(CASE 
        WHEN pd.fact_type::text LIKE '%Adoration%' AND pd.extraction_method = 'ai_gemini' AND pd.confidence_score >= 70 
        THEN (pd.ai_structured_data->>'has_weekly_schedule')::boolean 
        WHEN pd.fact_type::text LIKE '%Adoration%' AND pd.extraction_method != 'ai_gemini'
        THEN (pd.fact_value IS NOT NULL AND pd.fact_value != 'Information not found')
        ELSE false
    END) as has_weekly_adoration,
    
    MAX(CASE 
        WHEN pd.fact_type::text LIKE '%Adoration%' AND pd.extraction_method = 'ai_gemini'
        THEN pd.confidence_score 
        WHEN pd.fact_type::text LIKE '%Adoration%' AND pd.extraction_method != 'ai_gemini'
        THEN 50  -- Assign moderate confidence to keyword-based results
    END) as adoration_confidence,
    
    MAX(CASE 
        WHEN pd.fact_type::text LIKE '%Adoration%' AND pd.extraction_method = 'ai_gemini'
        THEN pd.ai_structured_data->>'frequency'
        ELSE 'unknown'
    END) as adoration_frequency,
    
    -- Reconciliation schedule info (AI and keyword-based)
    BOOL_OR(CASE 
        WHEN pd.fact_type::text LIKE '%Reconciliation%' AND pd.extraction_method = 'ai_gemini' AND pd.confidence_score >= 70 
        THEN (pd.ai_structured_data->>'has_weekly_schedule')::boolean 
        WHEN pd.fact_type::text LIKE '%Reconciliation%' AND pd.extraction_method != 'ai_gemini'
        THEN (pd.fact_value IS NOT NULL AND pd.fact_value != 'Information not found')
        ELSE false
    END) as has_weekly_reconciliation,
    
    MAX(CASE 
        WHEN pd.fact_type::text LIKE '%Reconciliation%' AND pd.extraction_method = 'ai_gemini'
        THEN pd.confidence_score 
        WHEN pd.fact_type::text LIKE '%Reconciliation%' AND pd.extraction_method != 'ai_gemini'
        THEN 50  -- Assign moderate confidence to keyword-based results
    END) as reconciliation_confidence,
    
    MAX(CASE 
        WHEN pd.fact_type::text LIKE '%Reconciliation%' AND pd.extraction_method = 'ai_gemini'
        THEN pd.ai_structured_data->>'frequency'
        ELSE 'unknown'
    END) as reconciliation_frequency,
    
    -- Data quality metrics
    COUNT(CASE WHEN pd.extraction_method = 'ai_gemini' THEN 1 END) as ai_extractions,
    COUNT(CASE WHEN pd.extraction_method != 'ai_gemini' THEN 1 END) as keyword_extractions,
    MAX(pd.created_at) as last_updated

FROM public."Parishes" p
LEFT JOIN public."ParishData" pd ON p.id = pd.parish_id 
WHERE pd.fact_type IN ('AdorationSchedule', 'ReconciliationSchedule')
GROUP BY p.id, p."Name", p."Web", p.diocese_id
ORDER BY ai_extractions DESC, last_updated DESC;

-- Add comments for documentation
COMMENT ON COLUMN public."ParishData".confidence_score IS 'AI confidence score (0-100) for extracted information';
COMMENT ON COLUMN public."ParishData".extraction_method IS 'Method used: keyword_based, ai_gemini, manual, etc.';
COMMENT ON COLUMN public."ParishData".ai_structured_data IS 'JSON structure with detailed AI extraction results';

COMMENT ON VIEW public."HighQualitySchedules" IS 'High-confidence AI-extracted schedule information for parishes';
COMMENT ON VIEW public."ParishScheduleSummary" IS 'Summary view showing schedule availability for all parishes';

-- Sample query to find parishes with weekly adoration and reconciliation
/*
SELECT 
    parish_name,
    parish_website,
    has_weekly_adoration,
    adoration_confidence,
    has_weekly_reconciliation,
    reconciliation_confidence,
    ai_extractions,
    keyword_extractions,
    last_updated
FROM public."ParishScheduleSummary"
WHERE has_weekly_adoration = true 
AND has_weekly_reconciliation = true
AND (adoration_confidence >= 70 OR reconciliation_confidence >= 70)
ORDER BY ai_extractions DESC, adoration_confidence DESC, reconciliation_confidence DESC;
*/

-- Sample query to see AI extraction results
/*
SELECT 
    parish_name,
    fact_type,
    extraction_method,
    confidence_score,
    ai_structured_data->>'schedule_details' as schedule_details,
    ai_structured_data->>'days_offered' as days_offered,
    ai_structured_data->>'has_weekly_schedule' as has_weekly_schedule
FROM public."HighQualitySchedules"
WHERE confidence_score >= 70
ORDER BY confidence_score DESC;
*/