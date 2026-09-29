from sqlalchemy.orm import Session

from app.core.usuarios.errors import EmailInvalidoError, RolUsuarioInvalidoError
from app.core.usuarios.model import Usuario
from app.core.usuarios.roles import ROLES


def normalizar_email(email: str) -> str:
    limpio = (email or "").strip().lower()
    local, arroba, dominio = limpio.partition("@")
    if not local or not arroba or "." not in dominio or " " in limpio:
        raise EmailInvalidoError(
            "El correo no es válido. Escríbelo completo, por ejemplo "
            "nombre@asiati.com.co."
        )
    return limpio


def validar_rol(rol: str) -> str:
    if rol not in ROLES:
        raise RolUsuarioInvalidoError(
            f"Rol de usuario no definido: {rol}. Usa uno de: {', '.join(ROLES)}."
        )
    return rol


def crear_usuario(
    session: Session,
    *,
    email: str,
    nombre: str,
    rol: str,
    password_hash: str,
    creado_por: int | None = None,
    debe_cambiar_password: bool = True,
) -> Usuario:
    """Registra un usuario únicamente con un rol definido para la plataforma."""
    validar_rol(rol)

    usuario = Usuario(
        email=normalizar_email(email),
        nombre=nombre.strip(),
        rol=rol,
        password_hash=password_hash,
        creado_por=creado_por,
        debe_cambiar_password=debe_cambiar_password,
    )
    session.add(usuario)
    return usuario
