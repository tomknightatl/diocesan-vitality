-- Test migration for deployment script validation
-- This is a simple migration that adds a test table

BEGIN;

-- Create a test table
CREATE TABLE IF NOT EXISTS deployment_test (
    id SERIAL PRIMARY KEY,
    test_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add a comment
COMMENT ON TABLE deployment_test IS 'Test table for deployment validation';

COMMIT;