"""Crea un superadministrador desde la terminal. No existe endpoint público para esto.

Uso:
    python -m app.core.usuarios.crear_superadmin --email nombre@asiati.com.co --nombre "Nombre"

La contraseña se pide por teclado dos veces y no se muestra ni queda en el
historial de la terminal.
"""
import argparse
import getpass
import sys
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auditoria import registrar_auditoria
from app.core.auth.passwords import (
    PasswordDebilError,
    hashear_password,
    validar_password_nueva,
)
from app.core.session import obtener_session
from app.core.usuarios.errors import EmailInvalidoError
from app.core.usuarios.model import Usuario
from app.core.usuarios.roles import ROL_SUPER_ADMINISTRADOR
from app.core.usuarios.service import crear_usuario, normalizar_email


class SuperadminNoCreadoError(RuntimeError):
    """No se pudo crear el superadministrador; el mensaje dice por qué."""


def crear_superadmin(
    session: Session,
    *,
    email: str,
    nombre: str,
    password: str,
) -> Usuario:
    """Crea el superadministrador y su fila de auditoría. No hace commit."""
    try:
        email = normalizar_email(email)
        validar_password_nueva(password)
    except (EmailInvalidoError, PasswordDebilError) as exc:
        raise SuperadminNoCreadoError(str(exc)) from exc
    if not nombre.strip():
        raise SuperadminNoCreadoError("Escribe el nombre con --nombre.")
    if session.scalar(select(Usuario.id).where(Usuario.email == email)) is not None:
        raise SuperadminNoCreadoError(
            "Ya existe un usuario con ese correo. Si olvidaste la contraseña, "
            "pide a otro superadministrador que la restablezca."
        )

    # Quien la escribe en la terminal es el propio superadministrador: no es
    # una contraseña temporal, así que no se le obliga a cambiarla.
    usuario = crear_usuario(
        session,
        email=email,
        nombre=nombre,
        rol=ROL_SUPER_ADMINISTRADOR,
        password_hash=hashear_password(password),
        debe_cambiar_password=False,
    )
    session.flush()
    registrar_auditoria(
        session,
        usuario_id=None,
        accion="usuario.crear_superadmin_terminal",
        entidad="usuario",
        entidad_id=usuario.id,
        despues={"email": usuario.email, "nombre": usuario.nombre, "rol": usuario.rol},
    )
    return usuario


def main(
    argv: list[str] | None = None,
    pedir_password: Callable[[str], str] = getpass.getpass,
) -> int:
    parser = argparse.ArgumentParser(description="Crea un superadministrador.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--nombre", required=True)
    args = parser.parse_args(argv)

    password = pedir_password("Contraseña (mínimo 12 caracteres): ")
    if password != pedir_password("Repite la contraseña: "):
        print("Las contraseñas no coinciden. Vuelve a correr el comando.", file=sys.stderr)
        return 1

    sesiones = obtener_session()
    session = next(sesiones)
    try:
        usuario = crear_superadmin(
            session, email=args.email, nombre=args.nombre, password=password
        )
        session.commit()
    except SuperadminNoCreadoError as exc:
        session.rollback()
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        sesiones.close()

    print(f"Superadministrador creado: {usuario.email} (id {usuario.id}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
