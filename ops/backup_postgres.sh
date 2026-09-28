#!/bin/sh
set -eu

: "${DATABASE_URL:?DATABASE_URL es obligatoria}"

BACKUP_DIR="${BACKUP_DIR:-/backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DESTINO="${BACKUP_DIR}/financial_system_${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"
umask 077

pg_dump --no-owner --no-privileges "${DATABASE_URL}" | gzip > "${DESTINO}"

find "${BACKUP_DIR}"   -type f   -name 'financial_system_*.sql.gz'   -mtime "+${BACKUP_RETENTION_DAYS}"   -delete

printf '%s\n' "${DESTINO}"
