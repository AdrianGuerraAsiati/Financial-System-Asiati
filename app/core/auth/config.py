import os
from dataclasses import dataclass
from datetime import timedelta


# Valores por defecto de .env.example. Se cambian por entorno, no en el código.
_DEFECTOS = {
    "LOGIN_MAX_INTENTOS_FALLIDOS": 5,
    "LOGIN_VENTANA_MINUTOS": 15,
    "SESION_DURACION_HORAS": 8,
}
LARGO_MINIMO_SECRETO = 32


class ConfiguracionAuthError(RuntimeError):
    """Falta o es inválida una variable de entorno de autenticación."""


@dataclass(frozen=True)
class ConfiguracionAuth:
    jwt_secret: str
    max_intentos_fallidos: int
    ventana_intentos: timedelta
    duracion_sesion: timedelta


def _entero_positivo(nombre: str) -> int:
    crudo = os.environ.get(nombre)
    if crudo is None or crudo.strip() == "":
        return _DEFECTOS[nombre]
    try:
        valor = int(crudo)
    except ValueError:
        valor = 0
    if valor <= 0:
        raise ConfiguracionAuthError(
            f"{nombre} debe ser un número entero mayor que cero. "
            f"Corrige la variable de entorno (valor por defecto: {_DEFECTOS[nombre]})."
        )
    return valor


def cargar_configuracion() -> ConfiguracionAuth:
    secreto = os.environ.get("JWT_SECRET", "")
    if not secreto:
        raise ConfiguracionAuthError(
            "Falta JWT_SECRET. Define la variable de entorno con un valor "
            f"aleatorio de al menos {LARGO_MINIMO_SECRETO} caracteres."
        )
    if len(secreto) < LARGO_MINIMO_SECRETO:
        raise ConfiguracionAuthError(
            f"JWT_SECRET debe tener al menos {LARGO_MINIMO_SECRETO} caracteres. "
            "Genera uno nuevo, por ejemplo con: python -c "
            "\"import secrets; print(secrets.token_urlsafe(48))\""
        )
    return ConfiguracionAuth(
        jwt_secret=secreto,
        max_intentos_fallidos=_entero_positivo("LOGIN_MAX_INTENTOS_FALLIDOS"),
        ventana_intentos=timedelta(minutes=_entero_positivo("LOGIN_VENTANA_MINUTOS")),
        duracion_sesion=timedelta(hours=_entero_positivo("SESION_DURACION_HORAS")),
    )
