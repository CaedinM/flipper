#!/bin/bash
set -e

echo "Initializing Flipper database..."

# Execute schema.sql to create tables
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f /sql/schema.sql
echo "Created core tables"

# Execute releases.sql to create agent_runs and releases tables
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f /sql/releases.sql
echo "Created agent_runs and releases tables"

# Execute triggers.sql to set up triggers
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f /sql/triggers.sql
echo "Created triggers"

echo "Database initialization complete!"
