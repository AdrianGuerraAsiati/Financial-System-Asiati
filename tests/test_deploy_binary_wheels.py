"""La compilación en Lightsail micro debe usar wheels binarios precompilados."""

from pathlib import Path


def test_dockerfile_evita_compilar_sqlalchemy_desde_fuente():
    dockerfile = (Path(__file__).resolve().parents[1] / "Dockerfile").read_text(
        encoding="utf-8"
    )
    assert "--only-binary=:all:" in dockerfile
    assert '"SQLAlchemy>=2.0,<3.0"' in dockerfile
    assert "--prefer-binary ." in dockerfile
    assert "pip install --no-cache-dir ." not in dockerfile
