-- Initialize database with UTF-8 encoding
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schema if needed
-- Additional initialization can be added here

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE trendhelper TO trendhelper;