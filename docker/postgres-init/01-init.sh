#!/bin/bash
set -e

# This script runs automatically on PostgreSQL container startup
# It ensures the agent user and database are properly configured

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Grant all privileges on the database to the agent user
    GRANT ALL PRIVILEGES ON DATABASE agent_platform TO agent;
EOSQL
