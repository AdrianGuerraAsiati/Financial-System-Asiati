import pytest

from app.core.usuarios.asegurar_superadmin_dev import main


def test_local_bootstrap_refuses_non_development_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")

    with pytest.raises(RuntimeError, match="solo puede ejecutarse"):
        main()
