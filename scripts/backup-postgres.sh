#!/bin/bash
set -euo pipefail

# Configuration
BACKUP_DIR="/backups/postgres"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/selfsmart_${TIMESTAMP}.dump"
LOG_FILE="/var/log/postgres-backup.log"

# Create backup directory
mkdir -p "${BACKUP_DIR}"

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

log "Starting PostgreSQL backup for ${DB_NAME}"

# Perform backup
PGPASSWORD="${DB_PASSWORD}" pg_dump \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    -F c \
    -f "${BACKUP_FILE}" \
    -v \
    2>&1 | tee -a "${LOG_FILE}"

# Compress backup
gzip "${BACKUP_FILE}"
BACKUP_FILE="${BACKUP_FILE}.gz"

# Get file size
BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
log "Backup completed: ${BACKUP_FILE} (${BACKUP_SIZE})"

# Upload to S3 (if configured)
if [ -n "${AWS_S3_BUCKET}" ]; then
    log "Uploading backup to S3: ${AWS_S3_BUCKET}"
    aws s3 cp "${BACKUP_FILE}" "s3://${AWS_S3_BUCKET}/postgres/${TIMESTAMP}.dump.gz" \
        --storage-class STANDARD_IA \
        2>&1 | tee -a "${LOG_FILE}"
    log "S3 upload completed"
fi

# Clean old backups
log "Cleaning backups older than ${RETENTION_DAYS} days"
find "${BACKUP_DIR}" -name "selfsmart_*.dump.gz" -mtime +${RETENTION_DAYS} -delete
find "${BACKUP_DIR}" -name "selfsmart_*.dump.gz" -mtime +${RETENTION_DAYS} | wc -l | \
    xargs -I {} log "Deleted {} old backups"

# Clean S3 backups (if configured)
if [ -n "${AWS_S3_BUCKET}" ]; then
    log "Cleaning S3 backups older than ${RETENTION_DAYS} days"
    aws s3 ls "s3://${AWS_S3_BUCKET}/postgres/" | \
        while read -r line; do
            file_date=$(echo "$line" | awk '{print $1}')
            file_name=$(echo "$line" | awk '{print $4}')
            file_timestamp=$(date -d "$file_date" +%s)
            cutoff_timestamp=$(date -d "${RETENTION_DAYS} days ago" +%s)
            
            if [ "$file_timestamp" -lt "$cutoff_timestamp" ]; then
                log "Deleting old S3 backup: ${file_name}"
                aws s3 rm "s3://${AWS_S3_BUCKET}/postgres/${file_name}"
            fi
        done
fi

log "Backup process completed successfully"