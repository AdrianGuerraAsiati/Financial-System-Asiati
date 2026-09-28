from sqlalchemy.orm import Session

from app.core.usuarios.errors import RolUsuarioInvalidoError
from app.core.usuarios.model import Usuario
from app.core.usuarios.roles import ROLES_PRIMERA_VERSION


def crear_usuario(
    session: Session,
    *,
    nombre: str,
    rol: str,
) -> Usuario:
    """Registra un usuario únicamente con un rol definido para la plataforma."""
    if rol not in ROLES_PRIMERA_VERSION:
        raise RolUsuarioInvalidoError(f"Rol de usuario no definido: {rol}")

    usuario = Usuario(
        nombre=nombre,
        rol=rol,
    )
    session.add(usuario)
    return usuario
