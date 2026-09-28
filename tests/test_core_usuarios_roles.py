import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.usuarios import (
    ROLES_PRIMERA_VERSION,
    ROL_CONCILIACION,
    ROL_COORDINACION_FINANCIERA,
    ROL_SUPER_ADMINISTRADOR,
    RolUsuarioInvalidoError,
    Usuario,
    crear_usuario,
)


def _engine():
    return create_engine(os.environ["DATABASE_URL"])


def test_first_web_version_exposes_exactly_the_three_defined_roles() -> None:
    assert ROLES_PRIMERA_VERSION == (
        ROL_SUPER_ADMINISTRADOR,
        ROL_COORDINACION_FINANCIERA,
        ROL_CONCILIACION,
    )


def test_user_with_defined_role_can_be_persisted() -> None:
    engine = _engine()

    with Session(engine) as session:
        usuario = crear_usuario(
            session,
            nombre="Coordinación financiera",
            rol=ROL_COORDINACION_FINANCIERA,
        )
        session.commit()
        usuario_id = usuario.id

    with Session(engine) as session:
        persisted = session.get(Usuario, usuario_id)

        assert persisted is not None
        assert persisted.nombre == "Coordinación financiera"
        assert persisted.rol == ROL_COORDINACION_FINANCIERA
        assert persisted.activo is True


def test_unknown_role_is_rejected_before_persistence() -> None:
    engine = _engine()

    with Session(engine) as session:
        with pytest.raises(RolUsuarioInvalidoError):
            crear_usuario(
                session,
                nombre="Rol no definido",
                rol="tesoreria",
            )

        assert not session.new
