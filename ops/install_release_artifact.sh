#!/usr/bin/env bash
set -euo pipefail

ARCHIVE="${1:?Uso: install_release_artifact.sh <source.tar.gz> <commit_sha>}"
TARGET_COMMIT="${2:?Falta commit_sha}"
APP_DIR="${APP_DIR:-/opt/financial-system}"
STAGE_DIR="${APP_DIR}.next"
PREVIOUS_DIR="${APP_DIR}.previous"
FAILED_DIR="${APP_DIR}.failed"

if [[ ! -f "$ARCHIVE" ]]; then
  echo "No existe el artefacto: $ARCHIVE" >&2
  exit 2
fi

if [[ ! -f "$APP_DIR/.env.production" ]]; then
  echo "Falta $APP_DIR/.env.production; no se reemplaza producción." >&2
  exit 2
fi

if [[ -f "$APP_DIR/.release_commit" ]] \
  && [[ "$(cat "$APP_DIR/.release_commit")" == "$TARGET_COMMIT" ]] \
  && curl -fsS http://127.0.0.1/ready >/dev/null 2>&1 \
  && curl -fsS http://127.0.0.1/health >/dev/null 2>&1; then
  echo "Commit $TARGET_COMMIT ya está desplegado y saludable."
  exit 0
fi

rm -rf "$STAGE_DIR" "$FAILED_DIR"
mkdir -p "$STAGE_DIR"
tar -xzf "$ARCHIVE" -C "$STAGE_DIR"

for required in compose.production.yml ops/deploy_production.sh; do
  if [[ ! -f "$STAGE_DIR/$required" ]]; then
    echo "Artefacto inválido: falta $required." >&2
    rm -rf "$STAGE_DIR"
    exit 2
  fi
done

cp "$APP_DIR/.env.production" "$STAGE_DIR/.env.production"
chmod 600 "$STAGE_DIR/.env.production"

if [[ -d "$APP_DIR/secrets" ]]; then
  cp -a "$APP_DIR/secrets" "$STAGE_DIR/secrets"
else
  mkdir -p "$STAGE_DIR/secrets"
  printf '{}\n' > "$STAGE_DIR/secrets/google-service-account.json"
  chmod 600 "$STAGE_DIR/secrets/google-service-account.json"
fi

printf '%s\n' "$TARGET_COMMIT" > "$STAGE_DIR/.release_commit"

rm -rf "$PREVIOUS_DIR"
mv "$APP_DIR" "$PREVIOUS_DIR"
mv "$STAGE_DIR" "$APP_DIR"

if ! (
  cd "$APP_DIR"
  TARGET_COMMIT="$TARGET_COMMIT" bash ops/deploy_production.sh
); then
  echo "El deploy falló; restaurando el árbol de código anterior." >&2
  rm -rf "$FAILED_DIR"
  mv "$APP_DIR" "$FAILED_DIR"
  mv "$PREVIOUS_DIR" "$APP_DIR"

  (
    cd "$APP_DIR"
    bash ops/deploy_production.sh
  ) || true

  exit 1
fi

rm -rf "$PREVIOUS_DIR" "$FAILED_DIR"
echo "Release $TARGET_COMMIT instalada desde artefacto privado."
