import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auditoria import Auditoria
from app.core.usuarios import ROL_SUPER_ADMINISTRADOR, ROL_TI, Usuario
from app.core.usuarios.crear_superadmin import main
from tests.apoyo_auth import (
    SECRETO_PRUEBA,
    crear_usuario_prueba,
    email_unico,
    engine,
    iniciar_sesion,
)


PASSWORD = "clave-superadmin-larga"


def _pedir(*respuestas: str):
    pendientes = list(respuestas)
    return lambda _mensaje: pendientes.pop(0)


def test_command_creates_superadmin_who_can_log_in(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("JWT_SECRET", SECRETO_PRUEBA)
    email = email_unico()

    codigo = main(["--email", email, "--nombre", "Superadmin"], _pedir(PASSWORD, PASSWORD))

    assert codigo == 0
    assert "Superadministrador creado" in capsys.readouterr().out
    with Session(engine()) as session:
        usuario = session.scalar(select(Usuario).where(Usuario.email == email))
        assert usuario.rol == ROL_SUPER_ADMINISTRADOR
        assert usuario.debe_cambiar_password is False
        assert PASSWORD not in usuario.password_hash
        fila = session.scalar(
            select(Auditoria).where(
                Auditoria.accion == "usuario.crear_superadmin_terminal",
                Auditoria.entidad_id == usuario.id,
            )
        )
        assert fila is not None
    me = iniciar_sesion(email, PASSWORD).get("/api/v1/auth/me").json()
    assert me["usuario"]["rol"] == ROL_SUPER_ADMINISTRADOR


def test_mismatched_passwords_create_nothing(capsys: pytest.CaptureFixture[str]) -> None:
    email = email_unico()

    codigo = main(["--email", email, "--nombre", "X"], _pedir(PASSWORD, "otra-cosa-distinta"))

    assert codigo == 1
    assert "no coinciden" in capsys.readouterr().err
    with Session(engine()) as session:
        assert session.scalar(select(Usuario).where(Usuario.email == email)) is None


def test_short_password_is_rejected_with_guidance(capsys: pytest.CaptureFixture[str]) -> None:
    codigo = main(["--email", email_unico(), "--nombre", "X"], _pedir("corta", "corta"))

    assert codigo == 1
    assert "12" in capsys.readouterr().err


def test_existing_email_is_not_overwritten(capsys: pytest.CaptureFixture[str]) -> None:
    usuario_id, email = crear_usuario_prueba(ROL_TI)

    codigo = main(["--email", email, "--nombre", "X"], _pedir(PASSWORD, PASSWORD))

    assert codigo == 1
    assert "Ya existe" in capsys.readouterr().err
    with Session(engine()) as session:
        assert session.get(Usuario, usuario_id).rol == ROL_TI
