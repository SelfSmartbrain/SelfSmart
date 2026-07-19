#!/bin/bash
set -euo pipefail

# Run database migrations

echo "Running database migrations..."

# Wait for database to be ready
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q'; do
  echo "Waiting for database to be ready..."
  sleep 2
done

echo "Database is ready. Running migrations..."

# Run migrations
alembic upgrade head

echo "Migrations completed successfully."