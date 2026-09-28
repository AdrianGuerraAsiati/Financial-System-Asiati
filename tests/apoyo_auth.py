"""Datos y clientes de prueba para los tests de integración de usuarios y permisos."""
import itertools
import os
import uuid
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.auth.passwords import hashear_password
from app.core.empresas import Empresa
from app.core.hallazgos import Hallazgo
from app.core.periodos import Periodo
from app.core.usuarios import UsuarioEmpresa, crear_usuario
from app.core.usuarios.roles import ROL_SUPER_ADMINISTRADOR
from app.main import app


SECRETO_PRUEBA = "secreto-de-prueba-" + "x" * 40
PASSWORD_PRUEBA = "clave-de-prueba-larga"
_HASH_PRUEBA = hashear_password(PASSWORD_PRUEBA)
_dias = itertools.count()


def engine():
    return create_engine(os.environ["DATABASE_URL"])


def email_unico() -> str:
    return f"prueba-{uuid.uuid4().hex[:12]}@asiati.test"


def crear_empresa(nombre: str = "Empresa de prueba") -> int:
    with Session(engine()) as session:
        empresa = Empresa(nombre=f"{nombre} {uuid.uuid4().hex[:6]}")
        session.add(empresa)
        session.commit()
        return empresa.id


def crear_periodo(empresa_id: int, *, cerrado: bool = False) -> int:
    inicio = date(2031, 1, 1) + timedelta(days=next(_dias) * 2)
    with Session(engine()) as session:
        periodo = Periodo(
            empresa_id=empresa_id,
            fecha_inicio=inicio,
            fecha_fin=inicio + timedelta(days=1),
            cerrado=cerrado,
        )
        session.add(periodo)
        session.commit()
        return periodo.id


def crear_hallazgo(periodo_id: int, *, estado: str = "detectado") -> int:
    with Session(engine()) as session:
        hallazgo = Hallazgo(
            periodo_id=periodo_id,
            motor_slug="conciliacion_wallets",
            codigo_regla="PRUEBA",
            descripcion="Hallazgo de prueba",
            evidencia={},
            critico=True,
            resuelto=estado == "resuelto",
            estado=estado,
        )
        session.add(hallazgo)
        session.commit()
        return hallazgo.id


def crear_usuario_prueba(
    rol: str,
    *,
    empresas: tuple[int, ...] = (),
    debe_cambiar_password: bool = False,
    activo: bool = True,
) -> tuple[int, str]:
    email = email_unico()
    with Session(engine()) as session:
        usuario = crear_usuario(
            session,
            email=email,
            nombre=f"Usuario {rol}",
            rol=rol,
            password_hash=_HASH_PRUEBA,
            debe_cambiar_password=debe_cambiar_password,
        )
        usuario.activo = activo
        session.flush()
        for empresa_id in empresas:
            session.add(UsuarioEmpresa(usuario_id=usuario.id, empresa_id=empresa_id))
        session.commit()
        return usuario.id, email


def cliente() -> TestClient:
    os.environ.setdefault("JWT_SECRET", SECRETO_PRUEBA)
    # https funciona tanto con cookie Secure como con la configuración local no-Secure.
    return TestClient(app, base_url="https://testserver")


def iniciar_sesion(email: str, password: str = PASSWORD_PRUEBA) -> TestClient:
    client = cliente()
    respuesta = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert respuesta.status_code == 200, respuesta.text
    return client


def cliente_con_rol(rol: str, *, empresas: tuple[int, ...] = ()) -> tuple[TestClient, int]:
    usuario_id, email = crear_usuario_prueba(rol, empresas=empresas)
    return iniciar_sesion(email), usuario_id


def cliente_superadmin() -> TestClient:
    return cliente_con_rol(ROL_SUPER_ADMINISTRADOR)[0]
