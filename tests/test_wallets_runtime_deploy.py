from pathlib import Path


DOCKERFILE = Path("Dockerfile")
DEPLOY = Path(".github/workflows/deploy-development.yml")


def test_production_image_includes_wallet_runtime_json() -> None:
    contenido = DOCKERFILE.read_text(encoding="utf-8")

    assert (
        "COPY docs/motores/conciliacion_wallets/*.json "
        "./docs/motores/conciliacion_wallets/"
    ) in contenido


def test_development_deploy_retires_legacy_demo_company() -> None:
    contenido = DEPLOY.read_text(encoding="utf-8")

    assert "-e DEV_EMPRESA_NOMBRE=ASIATI" in contenido
    assert "python -m app.core.normalizar_empresas_dev </dev/null" in contenido
    assert 'set_env COMPRAS_SHEETS_EMPRESA_ID "$ASIATI_ID"' in contenido
    assert "set_env COMPRAS_SHEETS_EMPRESA_ID 1" not in contenido


def test_local_compose_passes_wiilog_identifier_from_env_file() -> None:
    contenido = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert (
        "WIILOG_WALLET_PRINCIPAL_EMAIL: ${WIILOG_WALLET_PRINCIPAL_EMAIL:-}"
        in contenido
    )


def test_production_image_includes_category_dimension_seed_json() -> None:
    contenido = DOCKERFILE.read_text(encoding="utf-8")

    assert "COPY docs/nucleo/dimensiones_iniciales.json ./docs/nucleo/" in contenido


def test_development_deploy_seeds_category_dimensions_idempotently() -> None:
    contenido = DEPLOY.read_text(encoding="utf-8")

    assert "- name: Seed categorization dimensions" in contenido
    assert "python -m app.core.dimensiones" in contenido
    assert "--archivo docs/nucleo/dimensiones_iniciales.json" in contenido
