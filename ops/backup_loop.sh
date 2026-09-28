#!/bin/sh
set -eu

INTERVALO="${BACKUP_INTERVAL_SECONDS:-86400}"

while true; do
  /bin/sh /ops/backup_postgres.sh
  sleep "${INTERVALO}"
done
