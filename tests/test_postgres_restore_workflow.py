"""Contratos sinteticos de restauracion aislada, sin leer backups financieros."""
from pathlib import Path

WORKFLOW = Path(".github/workflows/verify-postgres-restore.yml")


def test_restauracion_solamente_main_y_con_almacenamiento_temporal():
    texto = WORKFLOW.read_text(encoding="utf-8")
    assert "branches: [main]" in texto
    assert "github.ref == 'refs/heads/main'" in texto
    assert ".github/workflows/verify-postgres-restore.yml" in texto
    assert "workflow_dispatch:" in texto
    assert "services:" in texto and "image: postgres:16" in texto
    assert "PG_CONTAINER:" in texto and "job.services.isolated_postgres.id" in texto
    assert "docker exec -i" in texto
    assert "pg_restore" not in texto  # dump SQL plain; se usa psql con ON_ERROR_STOP
    assert "-v ON_ERROR_STOP=1" in texto


def test_check_s3_integridad_cifrado_y_esquema():
    texto = WORKFLOW.read_text(encoding="utf-8")
    assert "dev/postgres/backups/" in texto
    assert "aws s3 cp" in texto
    assert "sha256sum" in texto and "MANIFEST_HASH" in texto
    assert "gzip -t" in texto
    assert "PostgreSQL database dump complete" in texto
    assert "head-object" in texto
    assert '\"AES256\"' in texto
    assert "to_regclass('public.tesoreria_facturas')" in texto
    assert "to_regclass('public.tesoreria_pagos')" in texto
    assert "EXISTS (SELECT 1 FROM public.empresas)" in texto


def test_no_publica_dump_y_no_toca_db_activa():
    texto = WORKFLOW.read_text(encoding="utf-8")
    assert "actions/upload-artifact" not in texto
    assert "docker compose" not in texto
    assert "ssh " not in texto
    assert "psql -X -q -v ON_ERROR_STOP=1" in texto
    assert "salida SQL sensible suprimida" in texto
    assert "trap 'rm -f" in texto
    assert "ACTIONS_STEP_DEBUG" not in texto
