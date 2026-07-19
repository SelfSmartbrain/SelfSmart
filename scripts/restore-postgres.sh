#!/bin/bash
set -euo pipefail

# Configuration
BACKUP_FILE="${1:-}"
LOG_FILE="/var/log/postgres-restore.log"

if [ -z "${BACKUP_FILE}" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

# Get database credentials from environment
DB_HOST="${POSTGRES_HOST:-postgres}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-selfsmart}"
DB_USER="${POSTGRES_USER:-selfsmart}"
DB_PASSWORD="${POSTGRES_PASSWORD}"

# Decompress if needed
if [[ "${BACKUP_FILE}" == *.gz ]]; then
    TEMP_FILE=$(mktemp)
    gunzip -c "${BACKUP_FILE}" > "${TEMP_FILE}"
    BACKUP_FILE="${TEMP_FILE}"
fi

log "Starting PostgreSQL restore from ${BACKUP_FILE}"

# Drop existing database
log "Dropping existing database ${DB_NAME}"
PGPASSWORD="${DB_PASSWORD}" dropdb \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    "${DB_NAME}" \
    2>&1 | tee -a "${LOG_FILE}" || true

# Create new database
log "Creating new database ${DB_NAME}"
PGPASSWORD="${DB_PASSWORD}" createdb \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    "${DB_NAME}" \
    2>&1 | tee -a "${LOG_FILE}"

# Restore backup
log "Restoring database from backup"
PGPASSWORD="${DB_PASSWORD}" pg_restore \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    -v \
    "${BACKUP_FILE}" \
    2>&1 | tee -a "${LOG_FILE}"

# Cleanup
if [ -n "${TEMP_FILE}" ]; then
    rm -f "${TEMP_FILE}"
fi

log "Restore completed successfully"