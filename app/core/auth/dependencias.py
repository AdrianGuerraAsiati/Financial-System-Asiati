"""Dependencias de FastAPI para sesión y permisos (ROLES_Y_PERMISOS.md §7).

Uso en un endpoint:
    acceso: Acceso = Depends(requiere("hallazgos.escalar", empresa_de=empresa_de_hallazgo))

`empresa_de` es una dependencia que devuelve la empresa del recurso, o None si
el recurso no existe. Un recurso inexistente y uno de empresa no asignada
responden igual: 404.
"""
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.config import (
    ConfiguracionAuth,
    ConfiguracionAuthError,
    cargar_configuracion,
)
from app.core.auth.tokens import SesionInvalidaError, leer_token
from app.core.permisos import (
    PERMISOS,
    Alcance,
    RecursoNoVisibleError,
    SinPermisoError,
    verificar_acceso,
)
from app.core.session import obtener_session
from app.core.usuarios import Usuario, UsuarioEmpresa


COOKIE_SESION = "asiati_sesion"

MENSAJE_SIN_SESION = "Inicia sesión para continuar. Si ya la tenías abierta, expiró."
MENSAJE_NO_ENCONTRADO = "No encontramos ese recurso. Revisa el identificador."


@dataclass(frozen=True)
class Acceso:
    usuario: Usuario
    alcance: Alcance
    # None = todas las empresas; si no, solo estas.
    empresas_visibles: frozenset[int] | None
    ip: str | None


def ip_de(request: Request) -> str | None:
    return request.client.host if request.client else None


def obtener_configuracion() -> ConfiguracionAuth:
    try:
        return cargar_configuracion()
    except ConfiguracionAuthError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"La autenticación no está configurada. Avisa a TI: {exc}",
        ) from exc


def usuario_autenticado(
    request: Request,
    session: Session = Depends(obtener_session),
    configuracion: ConfiguracionAuth = Depends(obtener_configuracion),
) -> Usuario:
    """Usuario de la sesión, aunque todavía deba cambiar su contraseña."""
    token = request.cookies.get(COOKIE_SESION)
    if not token:
        raise HTTPException(status_code=401, detail=MENSAJE_SIN_SESION)
    try:
        contenido = leer_token(configuracion, token)
    except SesionInvalidaError as exc:
        raise HTTPException(status_code=401, detail=MENSAJE_SIN_SESION) from exc

    usuario = session.get(Usuario, contenido.usuario_id)
    if (
        usuario is None
        or not usuario.activo
        or not contenido.coincide_con(usuario.password_hash)
    ):
        raise HTTPException(status_code=401, detail=MENSAJE_SIN_SESION)
    return usuario


def usuario_vigente(usuario: Usuario = Depends(usuario_autenticado)) -> Usuario:
    """Usuario de la sesión que ya cambió su contraseña temporal."""
    if usuario.debe_cambiar_password:
        raise HTTPException(
            status_code=403,
            detail=(
                "Debes cambiar tu contraseña antes de continuar. "
                "Usa la opción «Cambiar contraseña»."
            ),
        )
    return usuario


def empresas_asignadas(session: Session, usuario_id: int) -> frozenset[int]:
    return frozenset(
        session.scalars(
            select(UsuarioEmpresa.empresa_id).where(
                UsuarioEmpresa.usuario_id == usuario_id
            )
        )
    )


def _resolver_acceso(
    session: Session,
    usuario: Usuario,
    permiso: str,
    *,
    request: Request,
    con_recurso: bool,
    empresa_id: int | None,
) -> Acceso:
    asignadas = empresas_asignadas(session, usuario.id)
    try:
        alcance = verificar_acceso(
            usuario.rol,
            permiso,
            empresa_id=empresa_id,
            asignadas=asignadas,
        )
    except SinPermisoError as exc:
        raise HTTPException(
            status_code=403,
            detail=(
                f"No tienes permiso para esta acción ({permiso}). "
                "Pídeselo al superadministrador."
            ),
        ) from exc
    except RecursoNoVisibleError as exc:
        raise HTTPException(status_code=404, detail=MENSAJE_NO_ENCONTRADO) from exc

    # El permiso se revisa antes que la existencia: sin permiso no se confirma nada.
    if con_recurso and empresa_id is None:
        raise HTTPException(status_code=404, detail=MENSAJE_NO_ENCONTRADO)

    return Acceso(
        usuario=usuario,
        alcance=alcance,
        empresas_visibles=None if alcance is Alcance.TODAS else asignadas,
        ip=ip_de(request),
    )


def requiere(
    permiso: str,
    empresa_de: Callable[..., int | None] | None = None,
) -> Callable[..., Acceso]:
    if permiso not in PERMISOS:
        raise KeyError(f"Permiso no definido en la matriz: {permiso}")

    if empresa_de is None:

        def dependencia(
            request: Request,
            usuario: Usuario = Depends(usuario_vigente),
            session: Session = Depends(obtener_session),
        ) -> Acceso:
            return _resolver_acceso(
                session,
                usuario,
                permiso,
                request=request,
                con_recurso=False,
                empresa_id=None,
            )

        return dependencia

    def dependencia_con_recurso(
        request: Request,
        usuario: Usuario = Depends(usuario_vigente),
        session: Session = Depends(obtener_session),
        empresa_id: int | None = Depends(empresa_de),
    ) -> Acceso:
        return _resolver_acceso(
            session,
            usuario,
            permiso,
            request=request,
            con_recurso=True,
            empresa_id=empresa_id,
        )

    return dependencia_con_recurso
