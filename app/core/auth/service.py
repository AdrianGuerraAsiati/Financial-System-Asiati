from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth.cognito import (
    ClienteCognito,
    CognitoCredencialesInvalidas,
    CognitoNoDisponible,
    CognitoUsuarioNoConfirmado,
)
from app.core.auth.config import (
    ConfiguracionAuth,
    PROVEEDOR_AUTH_COGNITO,
)
from app.core.auth.model import Ingreso
from app.core.auth.passwords import hashear_password, verificar_password
from app.core.empresas import Empresa
from app.core.usuarios import ROLES_VEN_TODAS_LAS_EMPRESAS, Usuario, UsuarioEmpresa


# Se verifica contra este hash cuando el correo no existe en modo local, para
# que la respuesta tarde lo mismo y no delate qué correos están registrados.
_HASH_SENUELO = hashear_password("usuario-inexistente-señuelo")


class DemasiadosIntentosError(Exception):
    """El correo superó el límite de intentos fallidos en la ventana."""


class CredencialesInvalidasError(Exception):
    """Correo o contraseña incorrectos, o usuario inactivo."""


class UsuarioNoConfirmadoError(Exception):
    """Cognito conoce el usuario, pero todavía debe confirmar su correo."""


class ProveedorAuthNoDisponibleError(Exception):
    """El proveedor externo no pudo completar la autenticación."""


@dataclass(frozen=True)
class ResultadoAutenticacion:
    usuario: Usuario
    debe_cambiar_password: bool


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


def _registrar_ingreso(
    session: Session,
    *,
    email: str,
    usuario_id: int | None,
    exito: bool,
    ip: str | None,
    user_agent: str | None,
) -> None:
    session.add(
        Ingreso(
            usuario_id=usuario_id,
            email_intentado=email[:255],
            exito=exito,
            ip=ip,
            user_agent=user_agent,
        )
    )


def _autenticar_local(
    session: Session,
    configuracion: ConfiguracionAuth,
    *,
    email: str,
    password: str,
    ip: str | None,
    user_agent: str | None,
) -> ResultadoAutenticacion:
    usuario = session.scalar(select(Usuario).where(Usuario.email == email))
    if usuario is None:
        verificar_password(_HASH_SENUELO, password)
        _registrar_ingreso(
            session,
            email=email,
            usuario_id=None,
            exito=False,
            ip=ip,
            user_agent=user_agent,
        )
        raise CredencialesInvalidasError()

    if not verificar_password(usuario.password_hash, password) or not usuario.activo:
        _registrar_ingreso(
            session,
            email=email,
            usuario_id=usuario.id,
            exito=False,
            ip=ip,
            user_agent=user_agent,
        )
        raise CredencialesInvalidasError()

    usuario.ultimo_ingreso_at = datetime.now(timezone.utc)
    _registrar_ingreso(
        session,
        email=email,
        usuario_id=usuario.id,
        exito=True,
        ip=ip,
        user_agent=user_agent,
    )
    return ResultadoAutenticacion(
        usuario=usuario,
        debe_cambiar_password=usuario.debe_cambiar_password,
    )


def _autenticar_cognito(
    session: Session,
    configuracion: ConfiguracionAuth,
    *,
    email: str,
    password: str,
    ip: str | None,
    user_agent: str | None,
) -> ResultadoAutenticacion:
    usuario = session.scalar(select(Usuario).where(Usuario.email == email))
    try:
        resultado = ClienteCognito(configuracion).autenticar(email, password)
    except CognitoUsuarioNoConfirmado as exc:
        _registrar_ingreso(
            session,
            email=email,
            usuario_id=usuario.id if usuario else None,
            exito=False,
            ip=ip,
            user_agent=user_agent,
        )
        # Solo una identidad que además existe en el directorio local puede
        # recibir orientación de confirmación. Así Cognito no se convierte en
        # un canal de enumeración de cuentas ajenas a la plataforma.
        if usuario is None:
            raise CredencialesInvalidasError() from exc
        raise UsuarioNoConfirmadoError() from exc
    except CognitoCredencialesInvalidas as exc:
        _registrar_ingreso(
            session,
            email=email,
            usuario_id=usuario.id if usuario else None,
            exito=False,
            ip=ip,
            user_agent=user_agent,
        )
        raise CredencialesInvalidasError() from exc
    except CognitoNoDisponible as exc:
        raise ProveedorAuthNoDisponibleError() from exc

    # Cognito autentica la identidad; PostgreSQL conserva autorización y estado
    # operativo. Una identidad sin usuario local nunca obtiene acceso.
    if usuario is None or not usuario.activo:
        _registrar_ingreso(
            session,
            email=email,
            usuario_id=usuario.id if usuario else None,
            exito=False,
            ip=ip,
            user_agent=user_agent,
        )
        raise CredencialesInvalidasError()

    if resultado.requiere_nueva_password:
        usuario.debe_cambiar_password = True

    usuario.ultimo_ingreso_at = datetime.now(timezone.utc)
    _registrar_ingreso(
        session,
        email=email,
        usuario_id=usuario.id,
        exito=True,
        ip=ip,
        user_agent=user_agent,
    )
    return ResultadoAutenticacion(
        usuario=usuario,
        debe_cambiar_password=(
            usuario.debe_cambiar_password or resultado.requiere_nueva_password
        ),
    )


def autenticar(
    session: Session,
    configuracion: ConfiguracionAuth,
    *,
    email: str,
    password: str,
    ip: str | None,
    user_agent: str | None,
) -> ResultadoAutenticacion:
    """Valida el login y deja el intento en ingresos. No hace commit."""
    email = (email or "").strip().lower()

    if _fallos_recientes(session, email, configuracion) >= configuracion.max_intentos_fallidos:
        _registrar_ingreso(
            session,
            email=email,
            usuario_id=None,
            exito=False,
            ip=ip,
            user_agent=user_agent,
        )
        raise DemasiadosIntentosError()

    if configuracion.proveedor == PROVEEDOR_AUTH_COGNITO:
        return _autenticar_cognito(
            session,
            configuracion,
            email=email,
            password=password,
            ip=ip,
            user_agent=user_agent,
        )
    return _autenticar_local(
        session,
        configuracion,
        email=email,
        password=password,
        ip=ip,
        user_agent=user_agent,
    )


def empresas_del_usuario(session: Session, usuario: Usuario) -> list[Empresa]:
    """Empresas que el usuario ve en el selector (§2)."""
    consulta = select(Empresa).order_by(Empresa.id)
    if usuario.rol not in ROLES_VEN_TODAS_LAS_EMPRESAS:
        consulta = consulta.join(
            UsuarioEmpresa, UsuarioEmpresa.empresa_id == Empresa.id
        ).where(UsuarioEmpresa.usuario_id == usuario.id)
    return list(session.scalars(consulta))
