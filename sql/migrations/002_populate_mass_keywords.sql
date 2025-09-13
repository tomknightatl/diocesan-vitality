-- Migration: 002_populate_mass_keywords.sql
-- Date: 2025-09-13
-- Purpose: Populate ScheduleKeywords table with comprehensive mass-related keywords
--          and ensure all fallback keywords are properly stored in database

-- Description:
-- This migration adds all mass-related keywords from the fallback system to the database,
-- ensuring comprehensive coverage for mass times extraction. It also adds any missing
-- reconciliation and adoration keywords to centralize all keyword management.

-- Prerequisites: 
-- - Migration 001_extend_schedule_types.sql must be run first
-- - ScheduleKeywords table must support 'mass' schedule_type

BEGIN;

-- Insert Mass Schedule Keywords (Positive)
-- Note: Using WHERE NOT EXISTS to avoid duplicates since there's no unique constraint
INSERT INTO "ScheduleKeywords" (keyword, schedule_type, weight, is_negative, is_active, description, created_at, updated_at)
SELECT keyword, schedule_type, weight, is_negative, is_active, description, created_at, updated_at
FROM (VALUES 
    -- Core mass keywords
    ('mass', 'mass', 8, false, true, 'Primary keyword for Mass schedules', NOW(), NOW()),
    ('masses', 'mass', 8, false, true, 'Plural form of mass', NOW(), NOW()),
    ('liturgy', 'mass', 5, false, true, 'Liturgical celebrations', NOW(), NOW()),
    ('eucharist', 'mass', 3, false, true, 'Eucharistic celebrations', NOW(), NOW()),
    
    -- Day-specific keywords
    ('sunday', 'mass', 6, false, true, 'Sunday Mass identification', NOW(), NOW()),
    ('saturday', 'mass', 4, false, true, 'Saturday schedules and vigil masses', NOW(), NOW()),
    ('weekday', 'mass', 4, false, true, 'Weekday mass schedules', NOW(), NOW()),
    
    -- Schedule-related keywords
    ('schedule', 'mass', 5, false, true, 'General schedule keyword for masses', NOW(), NOW()),
    ('times', 'mass', 4, false, true, 'Schedule timing keywords', NOW(), NOW())
) AS new_keywords(keyword, schedule_type, weight, is_negative, is_active, description, created_at, updated_at)
WHERE NOT EXISTS (
    SELECT 1 FROM "ScheduleKeywords" sk 
    WHERE sk.keyword = new_keywords.keyword 
    AND sk.schedule_type = new_keywords.schedule_type 
    AND sk.is_negative = new_keywords.is_negative
);

-- Insert Mass Schedule Keywords (Negative - exclusions)
INSERT INTO "ScheduleKeywords" (keyword, schedule_type, weight, is_negative, is_active, description, created_at, updated_at)
SELECT keyword, schedule_type, weight, is_negative, is_active, description, created_at, updated_at
FROM (VALUES 
    ('adoration', 'mass', 1, true, true, 'Exclude adoration events from mass schedules', NOW(), NOW()),
    ('reconciliation', 'mass', 1, true, true, 'Exclude reconciliation events from mass schedules', NOW(), NOW()),
    ('confession', 'mass', 1, true, true, 'Exclude confession events from mass schedules', NOW(), NOW()),
    ('baptism', 'mass', 1, true, true, 'Exclude baptism events from mass schedules', NOW(), NOW()),
    ('donate', 'mass', 1, true, true, 'Exclude donation events from mass schedules', NOW(), NOW()),
    ('giving', 'mass', 1, true, true, 'Exclude giving/fundraising events from mass schedules', NOW(), NOW()),
    ('meeting', 'mass', 1, true, true, 'Exclude meeting schedules from mass schedules', NOW(), NOW())
) AS new_keywords(keyword, schedule_type, weight, is_negative, is_active, description, created_at, updated_at)
WHERE NOT EXISTS (
    SELECT 1 FROM "ScheduleKeywords" sk 
    WHERE sk.keyword = new_keywords.keyword 
    AND sk.schedule_type = new_keywords.schedule_type 
    AND sk.is_negative = new_keywords.is_negative
);

-- Add some high-value shared keywords for better URL prioritization
INSERT INTO "ScheduleKeywords" (keyword, schedule_type, weight, is_negative, is_active, description, created_at, updated_at)
SELECT keyword, schedule_type, weight, is_negative, is_active, description, created_at, updated_at
FROM (VALUES 
    -- Universal schedule keywords that benefit all types
    ('parish', 'all', 3, false, true, 'Parish-related content indicator', NOW(), NOW()),
    ('church', 'all', 3, false, true, 'Church-related content indicator', NOW(), NOW()),
    ('catholic', 'all', 2, false, true, 'Catholic church identifier', NOW(), NOW()),
    ('worship', 'all', 4, false, true, 'Worship and liturgical content', NOW(), NOW()),
    ('service', 'all', 3, false, true, 'Religious service schedules', NOW(), NOW())
) AS new_keywords(keyword, schedule_type, weight, is_negative, is_active, description, created_at, updated_at)
WHERE NOT EXISTS (
    SELECT 1 FROM "ScheduleKeywords" sk 
    WHERE sk.keyword = new_keywords.keyword 
    AND sk.schedule_type = new_keywords.schedule_type 
    AND sk.is_negative = new_keywords.is_negative
);

-- Add negative keywords that should be excluded from all schedule types
INSERT INTO "ScheduleKeywords" (keyword, schedule_type, weight, is_negative, is_active, description, created_at, updated_at)
SELECT keyword, schedule_type, weight, is_negative, is_active, description, created_at, updated_at
FROM (VALUES 
    ('calendar', 'all', 1, true, true, 'Exclude generic calendar pages', NOW(), NOW()),
    ('event', 'all', 1, true, true, 'Exclude generic event listings', NOW(), NOW()),
    ('bulletin', 'all', 1, true, true, 'Exclude bulletin/newsletter content', NOW(), NOW()),
    ('contact', 'all', 1, true, true, 'Exclude contact pages', NOW(), NOW()),
    ('about', 'all', 1, true, true, 'Exclude about pages', NOW(), NOW())
) AS new_keywords(keyword, schedule_type, weight, is_negative, is_active, description, created_at, updated_at)
WHERE NOT EXISTS (
    SELECT 1 FROM "ScheduleKeywords" sk 
    WHERE sk.keyword = new_keywords.keyword 
    AND sk.schedule_type = new_keywords.schedule_type 
    AND sk.is_negative = new_keywords.is_negative
);

COMMIT;

-- Verification queries (uncomment to run after migration):
-- 
-- -- Check total keywords by type
-- SELECT 
--     schedule_type,
--     COUNT(*) FILTER (WHERE NOT is_negative) as positive_keywords,
--     COUNT(*) FILTER (WHERE is_negative) as negative_keywords,
--     COUNT(*) as total_keywords
-- FROM "ScheduleKeywords" 
-- WHERE is_active = true
-- GROUP BY schedule_type
-- ORDER BY schedule_type;
--
-- -- Show all mass keywords
-- SELECT keyword, weight, is_negative, description 
-- FROM "ScheduleKeywords" 
-- WHERE schedule_type = 'mass' AND is_active = true
-- ORDER BY is_negative, weight DESC, keyword;
--
-- -- Show total keyword count
-- SELECT COUNT(*) as total_active_keywords FROM "ScheduleKeywords" WHERE is_active = true;