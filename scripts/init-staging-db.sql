-- Staging Database Initialization Script
-- This script sets up a minimal database schema for staging tests

-- Create basic tables for testing
CREATE TABLE IF NOT EXISTS staging_health (
    id SERIAL PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert initial health check data
INSERT INTO staging_health (service_name, status) VALUES
    ('backend', 'healthy'),
    ('frontend', 'healthy'),
    ('database', 'healthy')
ON CONFLICT DO NOTHING;

-- Create a simple test table for integration tests
CREATE TABLE IF NOT EXISTS staging_test_data (
    id SERIAL PRIMARY KEY,
    test_name VARCHAR(100),
    test_value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
