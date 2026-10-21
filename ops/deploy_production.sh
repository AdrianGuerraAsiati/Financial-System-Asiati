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
TARGET_COMMIT="${TARGET_COMMIT:-}"
DEPLOYED_COMMIT_FILE="$APP_DIR/.last_deployed_commit"

if [[ -n "$TARGET_COMMIT" ]] \
  && [[ -f "$DEPLOYED_COMMIT_FILE" ]] \
  && [[ "$(cat "$DEPLOYED_COMMIT_FILE")" == "$TARGET_COMMIT" ]] \
  && curl -fsS http://127.0.0.1/ready >/dev/null 2>&1 \
  && curl -fsS http://127.0.0.1/health >/dev/null 2>&1; then
  echo "Commit $TARGET_COMMIT ya está desplegado y saludable."
  exit 0
fi

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

# La imagen se construye y verifica en GitHub Actions, no en Lightsail (1 GB RAM).
# Solo puede instalarse la imagen cuyo SHA coincide con el release entregado.
IMAGE_SHA="${ASIATI_IMAGE_SHA:-}"
if [[ ! "$IMAGE_SHA" =~ ^[0-9a-f]{40}$ ]]; then
  echo "Falta ASIATI_IMAGE_SHA válido en el release." >&2
  exit 2
fi
if [[ -n "$TARGET_COMMIT" && "$TARGET_COMMIT" != "$IMAGE_SHA" ]]; then
  echo "La imagen API no corresponde al commit que se quiere publicar." >&2
  exit 2
fi
if ! docker image inspect "financial-system-asiati:sha-${IMAGE_SHA}" >/dev/null 2>&1; then
  echo "No se cargó la imagen verificada financial-system-asiati:sha-${IMAGE_SHA}." >&2
  exit 2
fi

# Migración y API usan obligatoriamente el mismo artefacto, sin recompilar.
"${DC[@]}" run --rm api alembic upgrade head
"${DC[@]}" up -d --no-build

# La ruta del Caddyfile es un bind-mount. Tras intercambiar el directorio
# de release se debe recrear Caddy para montar y leer el archivo nuevo.
"${DC[@]}" run --rm --no-deps --entrypoint caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
"${DC[@]}" up -d --no-deps --force-recreate caddy

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

if [[ -n "$TARGET_COMMIT" ]]; then
  printf '%s\n' "$TARGET_COMMIT" > "$DEPLOYED_COMMIT_FILE"
fi

"${DC[@]}" ps
