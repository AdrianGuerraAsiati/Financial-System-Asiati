"""Evita migrar con la imagen anterior al commit desplegado."""
from pathlib import Path


def test_deploy_compila_imagen_nueva_antes_de_alembic() -> None:
    script = (Path(__file__).resolve().parents[1] / "ops" / "deploy_production.sh").read_text()
    assert script.index('"${DC[@]}" build api') < script.index('"${DC[@]}" run --rm api alembic upgrade head')
    assert script.index('"${DC[@]}" run --rm api alembic upgrade head') < script.index('"${DC[@]}" up -d --build')
