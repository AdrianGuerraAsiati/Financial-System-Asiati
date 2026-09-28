from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auditoria import registrar_auditoria
from app.core.auth.config import ConfiguracionAuth
from app.core.auth.dependencias import (
    COOKIE_SESION,
    ip_de,
    obtener_configuracion,
    usuario_autenticado,
)
from app.core.auth.passwords import (
    PasswordDebilError,
    hashear_password,
    validar_password_nueva,
    verificar_password,
)
from app.core.auth.service import (
    CredencialesInvalidasError,
    DemasiadosIntentosError,
    autenticar,
    empresas_del_usuario,
)
from app.core.auth.tokens import emitir_token
from app.core.permisos import permisos_efectivos
from app.core.session import obtener_session
from app.core.usuarios import Usuario


router = APIRouter(prefix="/auth", tags=["auth"])


class LoginEntrada(BaseModel):
    email: str
    password: str


class CambioPasswordEntrada(BaseModel):
    password_actual: str
    password_nueva: str


def _poner_cookie(
    response: Response,
    configuracion: ConfiguracionAuth,
    usuario: Usuario,
) -> None:
    response.set_cookie(
        COOKIE_SESION,
        emitir_token(
            configuracion,
            usuario_id=usuario.id,
            password_hash=usuario.password_hash,
        ),
        max_age=int(configuracion.duracion_sesion.total_seconds()),
        httponly=True,
        secure=True,
        samesite="strict",
        path="/",
    )


@router.post("/login")
def login(
    datos: LoginEntrada,
    request: Request,
    response: Response,
    session: Session = Depends(obtener_session),
    configuracion: ConfiguracionAuth = Depends(obtener_configuracion),
) -> dict[str, bool]:
    try:
        usuario = autenticar(
            session,
            configuracion,
            email=datos.email,
            password=datos.password,
            ip=ip_de(request),
            user_agent=request.headers.get("user-agent"),
        )
    except DemasiadosIntentosError as exc:
        session.commit()
        minutos = int(configuracion.ventana_intentos.total_seconds() // 60)
        raise HTTPException(
            status_code=429,
            detail=(
                "Demasiados intentos fallidos con este correo. Espera "
                f"{minutos} minutos o pide al superadministrador que "
                "restablezca tu contraseña."
            ),
        ) from exc
    except CredencialesInvalidasError as exc:
        session.commit()
        raise HTTPException(
            status_code=401,
            detail=(
                "Correo o contraseña incorrectos. Revisa los datos o pide al "
                "superadministrador que restablezca tu contraseña."
            ),
        ) from exc

    session.commit()
    _poner_cookie(response, configuracion, usuario)
    return {"debe_cambiar_password": usuario.debe_cambiar_password}


@router.post("/logout", status_code=204)
def logout() -> Response:
    response = Response(status_code=204)
    response.delete_cookie(
        COOKIE_SESION, path="/", secure=True, httponly=True, samesite="strict"
    )
    return response


@router.get("/me")
def me(
    usuario: Usuario = Depends(usuario_autenticado),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    return {
        "usuario": {
            "id": usuario.id,
            "email": usuario.email,
            "nombre": usuario.nombre,
            "rol": usuario.rol,
            "debe_cambiar_password": usuario.debe_cambiar_password,
        },
        "permisos": {
            permiso: alcance.value
            for permiso, alcance in permisos_efectivos(usuario.rol).items()
        },
        "empresas": [
            {"id": empresa.id, "nombre": empresa.nombre}
            for empresa in empresas_del_usuario(session, usuario)
        ],
    }


@router.post("/cambiar-password")
def cambiar_password(
    datos: CambioPasswordEntrada,
    request: Request,
    response: Response,
    usuario: Usuario = Depends(usuario_autenticado),
    session: Session = Depends(obtener_session),
    configuracion: ConfiguracionAuth = Depends(obtener_configuracion),
) -> dict[str, bool]:
    if not verificar_password(usuario.password_hash, datos.password_actual):
        raise HTTPException(
            status_code=400,
            detail="La contraseña actual no es correcta. Escríbela de nuevo.",
        )
    try:
        validar_password_nueva(datos.password_nueva)
    except PasswordDebilError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if datos.password_nueva == datos.password_actual:
        raise HTTPException(
            status_code=422,
            detail="La contraseña nueva debe ser distinta de la actual.",
        )

    usuario.password_hash = hashear_password(datos.password_nueva)
    usuario.debe_cambiar_password = False
    registrar_auditoria(
        session,
        usuario_id=usuario.id,
        accion="usuario.cambiar_password",
        entidad="usuario",
        entidad_id=usuario.id,
        ip=ip_de(request),
    )
    session.commit()
    # La huella de la contraseña cambió: se emite una sesión nueva.
    _poner_cookie(response, configuracion, usuario)
    return {"debe_cambiar_password": False}
