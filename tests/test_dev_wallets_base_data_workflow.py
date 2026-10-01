from pathlib import Path


WORKFLOW = Path(".github/workflows/load-development-wallets-data.yml")


def test_wallets_base_data_workflow_is_manual_and_private() -> None:
    contenido = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in contenido
    assert "push:" not in contenido
    assert "pull_request:" not in contenido
    assert "financial-system-asiati-dev-data-890876258895" in contenido
    assert "dev/wallets/config/datos_base.json" in contenido
    assert "aws s3 cp" in contenido
    assert "python -m app.core.datos_base" in contenido


def test_wallets_base_data_workflow_cleans_transient_files_and_hides_payload() -> None:
    contenido = WORKFLOW.read_text(encoding="utf-8")

    assert "rm -f /tmp/datos_base_wallets.json" in contenido
    assert "empresas_creadas" in contenido
    assert "fuentes_reutilizadas" in contenido
    assert "cat /tmp/datos_base_wallets.json" not in contenido.split("Apply Wallets base data", 1)[0]
