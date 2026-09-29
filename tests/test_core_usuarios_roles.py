import os
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.empresas import Empresa
from app.core.hallazgos import Hallazgo
from app.core.usuarios import (
    ROLES,
    ROLES_PRIMERA_VERSION,
    ROL_CONCILIACION,
    ROL_COORDINACION_FINANCIERA,
    ROL_SUPER_ADMINISTRADOR,
    ROL_TI,
    RolUsuarioInvalidoError,
    Usuario,
    UsuarioEmpresa,
    crear_usuario,
)


def _engine():
    return create_engine(os.environ["DATABASE_URL"])


def _email() -> str:
    return f"usuario-{uuid.uuid4().hex[:10]}@asiati.test"


def test_first_web_version_exposes_exactly_the_three_defined_roles() -> None:
    assert ROLES_PRIMERA_VERSION == (
        ROL_SUPER_ADMINISTRADOR,
        ROL_COORDINACION_FINANCIERA,
        ROL_CONCILIACION,
    )


def test_user_with_defined_role_can_be_persisted() -> None:
    engine = _engine()
    email = _email()

    with Session(engine) as session:
        usuario = crear_usuario(
            session,
            email=email.upper(),
            nombre="Coordinación financiera",
            rol=ROL_COORDINACION_FINANCIERA,
            password_hash="$argon2id$prueba",
        )
        session.commit()
        usuario_id = usuario.id

    with Session(engine) as session:
        persisted = session.get(Usuario, usuario_id)

        assert persisted is not None
        assert persisted.email == email
        assert persisted.nombre == "Coordinación financiera"
        assert persisted.rol == ROL_COORDINACION_FINANCIERA
        assert persisted.activo is True
        assert persisted.debe_cambiar_password is True
        assert persisted.creado_at is not None


def test_unknown_role_is_rejected_before_persistence() -> None:
    engine = _engine()

    with Session(engine) as session:
        with pytest.raises(RolUsuarioInvalidoError):
            crear_usuario(
                session,
                email=_email(),
                nombre="Rol no definido",
                rol="tesoreria",
                password_hash="$argon2id$prueba",
            )

        assert not session.new


@pytest.mark.parametrize("rol", ROLES)
def test_database_check_accepts_the_five_roles(rol: str) -> None:
    with Session(_engine()) as session:
        crear_usuario(
            session,
            email=_email(),
            nombre="Rol válido",
            rol=rol,
            password_hash="$argon2id$prueba",
        )
        session.commit()


def test_database_check_rejects_unknown_role_even_bypassing_the_service() -> None:
    with Session(_engine()) as session:
        session.add(
            Usuario(
                email=_email(),
                nombre="Rol inválido",
                rol="SUPERADMIN",
                password_hash="$argon2id$prueba",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_email_is_unique() -> None:
    email = _email()
    with Session(_engine()) as session:
        crear_usuario(
            session, email=email, nombre="A", rol=ROL_TI, password_hash="h"
        )
        session.commit()
        crear_usuario(
            session, email=email, nombre="B", rol=ROL_TI, password_hash="h"
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_user_can_be_assigned_companies() -> None:
    with Session(_engine()) as session:
        empresa = Empresa(nombre="Empresa asignable")
        usuario = crear_usuario(
            session,
            email=_email(),
            nombre="Conciliador",
            rol=ROL_CONCILIACION,
            password_hash="h",
        )
        session.add(empresa)
        session.flush()
        session.add(UsuarioEmpresa(usuario_id=usuario.id, empresa_id=empresa.id))
        session.commit()

        asignada = session.get(UsuarioEmpresa, (usuario.id, empresa.id))
        assert asignada is not None
        assert asignada.asignado_at is not None


def test_findings_start_detected_and_state_is_checked() -> None:
    with Session(_engine()) as session:
        columna = session.execute(
            text(
                "SELECT column_default FROM information_schema.columns "
                "WHERE table_name = 'hallazgos' AND column_name = 'estado'"
            )
        ).scalar_one()
        assert "detectado" in columna
        assert Hallazgo.__table__.c.estado.nullable is False
