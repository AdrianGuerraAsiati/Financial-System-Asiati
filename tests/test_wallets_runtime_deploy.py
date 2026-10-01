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
    assert "python -m app.core.normalizar_empresas_dev" in contenido
    assert 'set_env COMPRAS_SHEETS_EMPRESA_ID "$ASIATI_ID"' in contenido
    assert "set_env COMPRAS_SHEETS_EMPRESA_ID 1" not in contenido
