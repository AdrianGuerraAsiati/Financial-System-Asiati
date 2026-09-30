from pathlib import Path
import subprocess

from fastapi.testclient import TestClient

from app.main import app


ROOT = Path(__file__).parents[1]


def test_application_exposes_readiness_endpoint() -> None:
    response = TestClient(app).get("/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_production_compose_has_tls_proxy_and_backup_service() -> None:
    compose = (ROOT / "compose.production.yml").read_text()

    assert "caddy:" in compose
    assert "backup:" in compose
    assert "80:80" in compose
    assert "443:443" in compose
    assert "BACKUP_INTERVAL_SECONDS" in compose


def test_caddy_routes_configured_asiati_domain_to_api() -> None:
    caddy = (ROOT / "ops" / "Caddyfile").read_text()

    assert "{$ASIATI_DOMAIN}" in caddy
    assert "reverse_proxy api:8000" in caddy


def test_database_backup_and_restore_scripts_exist() -> None:
    backup = (ROOT / "ops" / "backup_postgres.sh").read_text()
    restore = (ROOT / "ops" / "restore_postgres.sh").read_text()

    assert "pg_dump" in backup
    assert "BACKUP_RETENTION_DAYS" in backup
    assert "psql" in restore


def test_private_repo_deploy_uses_temporary_lightsail_ssh() -> None:
    workflow = (ROOT / ".github" / "workflows" / "deploy-development.yml").read_text()

    assert "actions/checkout@v4" in workflow
    assert "get-instance-access-details" in workflow
    assert "scp" in workflow
    assert "install_release_artifact.sh" in workflow
    assert "sha256sum -c -" in workflow
    assert "StrictHostKeyChecking=accept-new" in workflow
    assert "git fetch origin main" not in workflow
    assert "git reset --hard origin/main" not in workflow
    assert "ssm send-command" not in workflow
    assert "INSTANCE_ID" not in workflow


def test_production_deploy_scripts_have_valid_bash_syntax() -> None:
    for relative_path in (
        "ops/deploy_production.sh",
        "ops/install_release_artifact.sh",
    ):
        subprocess.run(
            ["bash", "-n", str(ROOT / relative_path)],
            check=True,
            capture_output=True,
            text=True,
        )
