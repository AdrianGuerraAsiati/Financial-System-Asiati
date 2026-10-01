import pytest

from app.core.normalizar_empresas_dev import normalizar


def test_normalizacion_empresas_refuses_non_development(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")

    with pytest.raises(RuntimeError, match="solo puede ejecutarse en development"):
        normalizar()
