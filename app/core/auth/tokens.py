import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timezone

import jwt

from app.core.auth.config import ConfiguracionAuth


ALGORITMO = "HS256"


class SesionInvalidaError(Exception):
    """El token no existe, expiró o no es válido."""


def _huella_password(password_hash: str) -> str:
    # Cambiar o restablecer la contraseña invalida las sesiones anteriores.
    return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class ContenidoToken:
    usuario_id: int
    huella_password: str

    def coincide_con(self, password_hash: str) -> bool:
        return hmac.compare_digest(
            self.huella_password, _huella_password(password_hash)
        )


def emitir_token(
    configuracion: ConfiguracionAuth,
    *,
    usuario_id: int,
    password_hash: str,
    ahora: datetime | None = None,
) -> str:
    emitido = ahora or datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(usuario_id),
            "pwd": _huella_password(password_hash),
            "iat": emitido,
            "exp": emitido + configuracion.duracion_sesion,
        },
        configuracion.jwt_secret,
        algorithm=ALGORITMO,
    )


def leer_token(configuracion: ConfiguracionAuth, token: str) -> ContenidoToken:
    try:
        datos = jwt.decode(
            token,
            configuracion.jwt_secret,
            algorithms=[ALGORITMO],
            options={"require": ["sub", "pwd", "exp"]},
        )
        return ContenidoToken(
            usuario_id=int(datos["sub"]),
            huella_password=str(datos["pwd"]),
        )
    except (jwt.PyJWTError, ValueError) as exc:
        raise SesionInvalidaError() from exc
