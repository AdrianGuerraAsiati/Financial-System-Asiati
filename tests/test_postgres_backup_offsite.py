"""Regresión sintética de persistencia: nunca lee ni escribe datos reales de ASIATI."""
import gzip
import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "ops/backup_postgres.sh"
WORKFLOW = ROOT / ".github/workflows/backup-postgres-offsite.yml"
POLICY = ROOT / "ops/aws/postgres-dev-backup-role-policy.json"


def _simular(tmp_path: Path, *, falla: bool, preexistente: bool = False):
    bin_path = tmp_path / "bin"
    bin_path.mkdir()
    fake = bin_path / "pg_dump"
    fake.write_text(
        '#!/bin/sh\n'
        'printf "%s\\n" "--" "-- PostgreSQL database dump" "--"\n'
        + ('exit 17\n' if falla else 'printf "%s\\n" "SELECT 1;" "-- PostgreSQL database dump complete" "--"\n')
    )
    fake.chmod(0o755)
    output = tmp_path / "local"
    output.mkdir()
    old = output / "financial_system_20200101T000000Z.sql.gz"
    if preexistente:
        old.write_bytes(b"backup previo no sobreescribir")
    env = {**os.environ, "PATH": f"{bin_path}:{os.environ['PATH']}",
           "DATABASE_URL": "postgresql://falso/pruebas", "BACKUP_DIR": str(output),
           "BACKUP_RETENTION_DAYS": "99999"}
    res = subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True)
    return res, output, old


def test_copia_local_valida_comprimida_y_sin_temporales(tmp_path):
    res, output, _ = _simular(tmp_path, falla=False)
    assert res.returncode == 0, res.stderr
    backups = list(output.glob("financial_system_*.sql.gz"))
    assert len(backups) == 1
    with gzip.open(backups[0], "rt") as f:
        assert "-- PostgreSQL database dump complete" in f.read()
    assert backups[0].stat().st_mode & 0o777 == 0o600
    assert not list(output.glob(".financial_system_*"))


def test_falla_pg_dump_no_publica_backup_ni_borra_el_anterior(tmp_path):
    res, output, old = _simular(tmp_path, falla=True, preexistente=True)
    assert res.returncode != 0
    assert old.read_bytes() == b"backup previo no sobreescribir"
    assert list(output.glob("financial_system_*.sql.gz")) == [old]
    assert not list(output.glob(".financial_system_*"))


def test_ciclo_de_respaldo_usa_bash_para_pipefail():
    loop = (ROOT / "ops/backup_loop.sh").read_text()
    assert "/bin/bash /ops/backup_postgres.sh" in loop
    source = SCRIPT.read_text()
    assert "set -euo pipefail" in source
    assert "gzip -t" in source
    assert "ln --" in source


def test_workflow_aisla_base_y_credenciales_sin_artefactos_publicos():
    w = WORKFLOW.read_text()
    assert "workflow_dispatch:" in w and "schedule:" in w
    assert "pull_request:" not in w and "push:" not in w
    assert "aws-actions/configure-aws-credentials@v4" in w
    assert "accessDetails.certKey" in w
    assert "docker compose --env-file .env.production -f compose.production.yml" in w
    assert "exec -T db sh -c" in w
    assert "set -euo pipefail" in w
    assert "gzip -t" in w
    assert "sha256sum" in w
    assert "--sse AES256" in w
    assert "dev/postgres/backups" in w
    assert "head-object" in w
    assert "actions/upload-artifact" not in w
    assert "--debug" not in w
    assert "Remove temporary SSH credentials" in w


def test_iam_minimo_y_sin_borrado():
    data = json.loads(POLICY.read_text())
    assert len(data["Statement"]) == 1
    s = data["Statement"][0]
    assert s["Effect"] == "Allow"
    assert s["Resource"] == (
        "arn:aws:s3:::financial-system-asiati-dev-data-890876258895/dev/postgres/backups/*"
    )
    assert set(s["Action"]) == {"s3:PutObject", "s3:GetObject", "s3:AbortMultipartUpload", "s3:ListMultipartUploadParts"}
