import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError


LARGO_MINIMO_PASSWORD = 12

_hasher = PasswordHasher()


class PasswordDebilError(ValueError):
    """La contraseña nueva no cumple el mínimo."""


def hashear_password(password: str) -> str:
    return _hasher.hash(password)


def verificar_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def validar_password_nueva(password: str) -> None:
    if len(password) < LARGO_MINIMO_PASSWORD:
        raise PasswordDebilError(
            f"La contraseña debe tener al menos {LARGO_MINIMO_PASSWORD} caracteres. "
            "Usa una frase larga que no uses en otro servicio."
        )


def generar_password_temporal() -> str:
    """Contraseña de un solo uso; el usuario debe cambiarla al primer ingreso."""
    return secrets.token_urlsafe(15)
