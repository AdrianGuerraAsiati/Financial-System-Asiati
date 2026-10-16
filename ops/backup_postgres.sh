#!/usr/bin/env bash
# Respaldo local PostgreSQL. Conserva las copias anteriores si pg_dump falla.
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL es obligatoria}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"

if [[ ! "$BACKUP_RETENTION_DAYS" =~ ^[0-9]+$ ]] || (( BACKUP_RETENTION_DAYS < 1 )); then
  echo "BACKUP_RETENTION_DAYS debe ser un entero positivo." >&2
  exit 2
fi

mkdir -p -- "$BACKUP_DIR"
umask 077
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DESTINO="$BACKUP_DIR/financial_system_${TIMESTAMP}.sql.gz"
TEMPORAL="$(mktemp "$BACKUP_DIR/.financial_system_${TIMESTAMP}.XXXXXXXX.sql.gz")"
trap 'rm -f -- "$TEMPORAL"' EXIT

# pipefail es obligatorio: gzip puede terminar bien aunque pg_dump falle.
pg_dump --no-owner --no-privileges "$DATABASE_URL" | gzip -c > "$TEMPORAL"
[[ -s "$TEMPORAL" ]]
gzip -t "$TEMPORAL"
# Comprobar la marca final de pg_dump sin imprimir datos SQL en los logs.
gzip -cd "$TEMPORAL" | tail -n 8 | grep -Fqx -- '-- PostgreSQL database dump complete'

# Publicacion atomica sin sobrescribir copias anteriores ni archivos parciales.
ln -- "$TEMPORAL" "$DESTINO"
rm -f -- "$TEMPORAL"

# La retencion local corre solo despues de una copia completa y verificada.
find "$BACKUP_DIR" -type f -name 'financial_system_*.sql.gz' -mtime "+$BACKUP_RETENTION_DAYS" -delete
printf 'Respaldo PostgreSQL local verificado: %s\n' "$DESTINO"
