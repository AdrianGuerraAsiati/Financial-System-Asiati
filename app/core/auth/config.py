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

PROVEEDOR_AUTH_LOCAL = "local"
PROVEEDOR_AUTH_COGNITO = "cognito"
PROVEEDORES_AUTH = {PROVEEDOR_AUTH_LOCAL, PROVEEDOR_AUTH_COGNITO}


class ConfiguracionAuthError(RuntimeError):
    """Falta o es inválida una variable de entorno de autenticación."""


@dataclass(frozen=True)
class ConfiguracionAuth:
    jwt_secret: str
    max_intentos_fallidos: int
    ventana_intentos: timedelta
    duracion_sesion: timedelta
    cookie_secure: bool
    proveedor: str
    cognito_region: str | None = None
    cognito_client_id: str | None = None
    cognito_client_secret: str | None = None


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


def _booleano(nombre: str, *, defecto: bool) -> bool:
    crudo = os.environ.get(nombre)
    if crudo is None or crudo.strip() == "":
        return defecto
    valor = crudo.strip().lower()
    if valor in {"1", "true", "yes", "si", "sí"}:
        return True
    if valor in {"0", "false", "no"}:
        return False
    raise ConfiguracionAuthError(
        f"{nombre} debe ser true o false. Valor recibido: {crudo!r}."
    )


def _requerida(nombre: str) -> str:
    valor = os.environ.get(nombre, "").strip()
    if not valor:
        raise ConfiguracionAuthError(
            f"Falta {nombre}. Es obligatorio cuando AUTH_PROVIDER=cognito."
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

    proveedor = os.environ.get("AUTH_PROVIDER", PROVEEDOR_AUTH_LOCAL).strip().lower()
    if proveedor not in PROVEEDORES_AUTH:
        raise ConfiguracionAuthError(
            "AUTH_PROVIDER debe ser 'local' o 'cognito'."
        )

    cognito_region = None
    cognito_client_id = None
    cognito_client_secret = None
    if proveedor == PROVEEDOR_AUTH_COGNITO:
        cognito_region = _requerida("COGNITO_REGION")
        cognito_client_id = _requerida("COGNITO_CLIENT_ID")
        cognito_client_secret = _requerida("COGNITO_CLIENT_SECRET")

    return ConfiguracionAuth(
        jwt_secret=secreto,
        max_intentos_fallidos=_entero_positivo("LOGIN_MAX_INTENTOS_FALLIDOS"),
        ventana_intentos=timedelta(minutes=_entero_positivo("LOGIN_VENTANA_MINUTOS")),
        duracion_sesion=timedelta(hours=_entero_positivo("SESION_DURACION_HORAS")),
        cookie_secure=_booleano(
            "SESSION_COOKIE_SECURE",
            defecto=os.environ.get("APP_ENV", "development").lower() == "production",
        ),
        proveedor=proveedor,
        cognito_region=cognito_region,
        cognito_client_id=cognito_client_id,
        cognito_client_secret=cognito_client_secret,
    )
