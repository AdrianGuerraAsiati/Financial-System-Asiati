#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/financial-system}"
cd "$APP_DIR"

if [[ ! -f .env.production ]]; then
  echo "Falta $APP_DIR/.env.production" >&2
  exit 2
fi

if ! docker buildx version >/dev/null 2>&1; then
  echo "Docker Buildx no está disponible." >&2
  exit 2
fi

DC=(docker compose --env-file .env.production -f compose.production.yml)

"${DC[@]}" config --services >/dev/null
"${DC[@]}" up -d db

db_ready=0
for _ in $(seq 1 45); do
  if "${DC[@]}" exec -T db pg_isready -U asiati -d financial_system >/dev/null 2>&1; then
    db_ready=1
    break
  fi
  sleep 2
done

if [[ "$db_ready" != "1" ]]; then
  echo "PostgreSQL no quedó listo." >&2
  "${DC[@]}" logs --no-color --tail=80 db >&2 || true
  exit 1
fi

"${DC[@]}" run --rm api alembic upgrade head
"${DC[@]}" up -d --build

ready=0
for _ in $(seq 1 60); do
  if curl -fsS http://127.0.0.1/ready >/tmp/financial-system-ready.json 2>/dev/null; then
    ready=1
    break
  fi
  sleep 2
done

if [[ "$ready" != "1" ]]; then
  echo "La aplicación no pasó /ready." >&2
  "${DC[@]}" ps >&2 || true
  "${DC[@]}" logs --no-color --tail=120 api caddy >&2 || true
  exit 1
fi

cat /tmp/financial-system-ready.json
echo
curl -fsS http://127.0.0.1/health
echo
"${DC[@]}" ps
