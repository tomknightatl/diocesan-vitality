-- Initialize development database for Diocesan Vitality
-- This script sets up basic tables for development and testing

-- Create basic test tables for CI
CREATE TABLE IF NOT EXISTS dev_test_data (
    id SERIAL PRIMARY KEY,
    test_name VARCHAR(100) NOT NULL,
    test_value VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert initial test data
INSERT INTO dev_test_data (test_name, test_value)
VALUES ('dev_init', 'database_initialized')
ON CONFLICT DO NOTHING;

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;

-- Log initialization
INSERT INTO dev_test_data (test_name, test_value)
VALUES ('init_complete', CURRENT_TIMESTAMP::text);