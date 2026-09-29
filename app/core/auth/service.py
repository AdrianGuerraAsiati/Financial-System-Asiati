from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth.config import ConfiguracionAuth
from app.core.auth.model import Ingreso
from app.core.auth.passwords import hashear_password, verificar_password
from app.core.empresas import Empresa
from app.core.usuarios import ROLES_VEN_TODAS_LAS_EMPRESAS, Usuario, UsuarioEmpresa


# Se verifica contra este hash cuando el correo no existe, para que la respuesta
# tarde lo mismo y no delate qué correos están registrados.
_HASH_SENUELO = hashear_password("usuario-inexistente-señuelo")


class DemasiadosIntentosError(Exception):
    """El correo superó el límite de intentos fallidos en la ventana."""


class CredencialesInvalidasError(Exception):
    """Correo o contraseña incorrectos, o usuario inactivo."""


def _fallos_recientes(
    session: Session,
    email: str,
    configuracion: ConfiguracionAuth,
) -> int:
    desde = datetime.now(timezone.utc) - configuracion.ventana_intentos
    return session.scalar(
        select(func.count(Ingreso.id)).where(
            Ingreso.email_intentado == email,
            Ingreso.exito.is_(False),
            Ingreso.creado_at >= desde,
        )
    )


def autenticar(
    session: Session,
    configuracion: ConfiguracionAuth,
    *,
    email: str,
    password: str,
    ip: str | None,
    user_agent: str | None,
) -> Usuario:
    """Valida el login y deja el intento en `ingresos`. No hace commit."""
    email = (email or "").strip().lower()

    def registrar(usuario_id: int | None, exito: bool) -> None:
        session.add(
            Ingreso(
                usuario_id=usuario_id,
                email_intentado=email[:255],
                exito=exito,
                ip=ip,
                user_agent=user_agent,
            )
        )

    if _fallos_recientes(session, email, configuracion) >= configuracion.max_intentos_fallidos:
        registrar(None, False)
        raise DemasiadosIntentosError()

    usuario = session.scalar(select(Usuario).where(Usuario.email == email))
    if usuario is None:
        verificar_password(_HASH_SENUELO, password)
        registrar(None, False)
        raise CredencialesInvalidasError()
    if not verificar_password(usuario.password_hash, password) or not usuario.activo:
        registrar(usuario.id, False)
        raise CredencialesInvalidasError()

    usuario.ultimo_ingreso_at = datetime.now(timezone.utc)
    registrar(usuario.id, True)
    return usuario


def empresas_del_usuario(session: Session, usuario: Usuario) -> list[Empresa]:
    """Empresas que el usuario ve en el selector (§2)."""
    consulta = select(Empresa).order_by(Empresa.id)
    if usuario.rol not in ROLES_VEN_TODAS_LAS_EMPRESAS:
        consulta = consulta.join(
            UsuarioEmpresa, UsuarioEmpresa.empresa_id == Empresa.id
        ).where(UsuarioEmpresa.usuario_id == usuario.id)
    return list(session.scalars(consulta))
