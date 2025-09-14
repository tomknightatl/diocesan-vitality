-- Migration: Enhance DiscoveredUrls table with comprehensive visit tracking
-- Created: 2025-09-13 23:25:00
-- Purpose: Add detailed visit result tracking for URL extraction optimization

-- Add visit tracking columns to DiscoveredUrls table
ALTER TABLE "public"."DiscoveredUrls"
ADD COLUMN IF NOT EXISTS "visited_at" timestamp with time zone DEFAULT NULL,
ADD COLUMN IF NOT EXISTS "http_status" integer DEFAULT NULL,
ADD COLUMN IF NOT EXISTS "response_time_ms" integer DEFAULT NULL,
ADD COLUMN IF NOT EXISTS "content_type" text DEFAULT NULL,
ADD COLUMN IF NOT EXISTS "content_size_bytes" integer DEFAULT NULL,
ADD COLUMN IF NOT EXISTS "extraction_success" boolean DEFAULT NULL,
ADD COLUMN IF NOT EXISTS "schedule_data_found" boolean DEFAULT NULL,
ADD COLUMN IF NOT EXISTS "schedule_keywords_count" integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS "error_type" text DEFAULT NULL,
ADD COLUMN IF NOT EXISTS "error_message" text DEFAULT NULL,
ADD COLUMN IF NOT EXISTS "quality_score" decimal(3,2) DEFAULT NULL,
ADD COLUMN IF NOT EXISTS "visit_count" integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS "last_successful_visit" timestamp with time zone DEFAULT NULL;

-- Create indexes for performance optimization
CREATE INDEX IF NOT EXISTS "idx_discoveredurls_visited_at" ON "public"."DiscoveredUrls" USING "btree" ("visited_at");
CREATE INDEX IF NOT EXISTS "idx_discoveredurls_extraction_success" ON "public"."DiscoveredUrls" USING "btree" ("extraction_success");
CREATE INDEX IF NOT EXISTS "idx_discoveredurls_schedule_data_found" ON "public"."DiscoveredUrls" USING "btree" ("schedule_data_found");
CREATE INDEX IF NOT EXISTS "idx_discoveredurls_quality_score" ON "public"."DiscoveredUrls" USING "btree" ("quality_score");
CREATE INDEX IF NOT EXISTS "idx_discoveredurls_http_status" ON "public"."DiscoveredUrls" USING "btree" ("http_status");

-- Add comments for documentation
COMMENT ON COLUMN "public"."DiscoveredUrls"."visited_at" IS 'Timestamp when URL was last visited during extraction';
COMMENT ON COLUMN "public"."DiscoveredUrls"."http_status" IS 'HTTP status code from last visit (200, 404, 500, etc.)';
COMMENT ON COLUMN "public"."DiscoveredUrls"."response_time_ms" IS 'Response time in milliseconds for performance tracking';
COMMENT ON COLUMN "public"."DiscoveredUrls"."content_type" IS 'MIME type of the response content';
COMMENT ON COLUMN "public"."DiscoveredUrls"."content_size_bytes" IS 'Size of response content in bytes';
COMMENT ON COLUMN "public"."DiscoveredUrls"."extraction_success" IS 'Whether extraction completed without errors';
COMMENT ON COLUMN "public"."DiscoveredUrls"."schedule_data_found" IS 'Whether schedule information was found in content';
COMMENT ON COLUMN "public"."DiscoveredUrls"."schedule_keywords_count" IS 'Number of schedule-related keywords found';
COMMENT ON COLUMN "public"."DiscoveredUrls"."error_type" IS 'Type of error encountered (timeout, dns, http, parsing)';
COMMENT ON COLUMN "public"."DiscoveredUrls"."error_message" IS 'Detailed error message for debugging';
COMMENT ON COLUMN "public"."DiscoveredUrls"."quality_score" IS 'Content quality score (0.00-1.00) for ML training';
COMMENT ON COLUMN "public"."DiscoveredUrls"."visit_count" IS 'Number of times this URL has been visited';
COMMENT ON COLUMN "public"."DiscoveredUrls"."last_successful_visit" IS 'Timestamp of last successful extraction';

-- Grant permissions
GRANT ALL ON TABLE "public"."DiscoveredUrls" TO "anon";
GRANT ALL ON TABLE "public"."DiscoveredUrls" TO "authenticated";
GRANT ALL ON TABLE "public"."DiscoveredUrls" TO "service_role";