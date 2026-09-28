#!/bin/sh
set -eu

: "${DATABASE_URL:?DATABASE_URL es obligatoria}"

if [ "$#" -ne 1 ]; then
  echo "Uso: restore_postgres.sh <backup.sql.gz>" >&2
  exit 2
fi

BACKUP_FILE="$1"

if [ ! -f "${BACKUP_FILE}" ]; then
  echo "No existe el backup: ${BACKUP_FILE}" >&2
  exit 2
fi

gzip -dc "${BACKUP_FILE}" | psql "${DATABASE_URL}"
