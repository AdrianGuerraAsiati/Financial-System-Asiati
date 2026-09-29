"""Bootstrap idempotente para desarrollo local.

Crea una empresa de demo si la base está vacía y asegura un superadministrador
local. Se niega a correr fuera de APP_ENV=development.
"""

from __future__ import annotations

import os

from sqlalchemy import select

from app.core.empresas import Empresa
from app.core.session import obtener_session
from app.core.usuarios import Usuario
from app.core.usuarios.crear_superadmin import crear_superadmin
from app.core.usuarios.roles import ROL_SUPER_ADMINISTRADOR


def _requerida(nombre: str, defecto: str | None = None) -> str:
    valor = os.getenv(nombre, defecto or "").strip()
    if not valor:
        raise RuntimeError(f"Falta configurar {nombre}.")
    return valor


def main() -> int:
    if os.getenv("APP_ENV", "development").strip().lower() != "development":
        raise RuntimeError(
            "El bootstrap local solo puede ejecutarse con APP_ENV=development."
        )

    email = _requerida("DEV_ADMIN_EMAIL", "admin@asiati.local").lower()
    nombre = _requerida("DEV_ADMIN_NAME", "Administrador local")
    password = _requerida("DEV_ADMIN_PASSWORD", "AsiatiDev2026!")
    empresa_nombre = _requerida("DEV_EMPRESA_NOMBRE", "ASIATI Demo")

    sesiones = obtener_session()
    session = next(sesiones)
    try:
        empresa = session.scalar(select(Empresa).order_by(Empresa.id).limit(1))
        if empresa is None:
            empresa = Empresa(nombre=empresa_nombre)
            session.add(empresa)
            session.flush()
            print(
                f"Empresa local creada: {empresa.nombre} (id {empresa.id}).",
                flush=True,
            )
        else:
            print(
                f"Empresa local disponible: {empresa.nombre} (id {empresa.id}).",
                flush=True,
            )

        usuario = session.scalar(select(Usuario).where(Usuario.email == email))
        if usuario is None:
            usuario = crear_superadmin(
                session,
                email=email,
                nombre=nombre,
                password=password,
            )
            session.flush()
            print(
                f"Superadministrador local creado: {usuario.email}.",
                flush=True,
            )
        elif usuario.rol != ROL_SUPER_ADMINISTRADOR:
            raise RuntimeError(
                f"Ya existe {email}, pero su rol es {usuario.rol!r}; "
                "no se modifica automáticamente."
            )
        else:
            print(
                f"Superadministrador local ya existe: {usuario.email}.",
                flush=True,
            )

        session.commit()
        print(
            "Bootstrap local listo. "
            f"Empresa inicial: id {empresa.id}. "
            "Consulta DEV_ADMIN_EMAIL/DEV_ADMIN_PASSWORD para ingresar.",
            flush=True,
        )
        return 0
    except Exception:
        session.rollback()
        raise
    finally:
        sesiones.close()


if __name__ == "__main__":
    raise SystemExit(main())
