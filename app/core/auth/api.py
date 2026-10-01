from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auditoria import registrar_auditoria
from app.core.auth.cognito import (
    ClienteCognito,
    CognitoCodigoInvalido,
    CognitoCredencialesInvalidas,
    CognitoNoDisponible,
    CognitoPasswordInvalida,
    CognitoUsuarioNoConfirmado,
)
from app.core.auth.config import (
    ConfiguracionAuth,
    PROVEEDOR_AUTH_COGNITO,
)
from app.core.auth.dependencias import (
    COOKIE_SESION,
    ip_de,
    obtener_configuracion,
    usuario_autenticado,
)
from app.core.auth.passwords import (
    PasswordDebilError,
    generar_marca_sesion_externa,
    hashear_password,
    validar_password_nueva,
    verificar_password,
)
from app.core.auth.service import (
    CredencialesInvalidasError,
    DemasiadosIntentosError,
    ProveedorAuthNoDisponibleError,
    UsuarioNoConfirmadoError,
    autenticar,
    empresas_del_usuario,
)
from app.core.auth.tokens import emitir_token
from app.core.permisos import permisos_efectivos
from app.core.session import obtener_session
from app.core.usuarios import Usuario
from app.core.usuarios.errors import EmailInvalidoError
from app.core.usuarios.service import normalizar_email


router = APIRouter(prefix="/auth", tags=["auth"])


class LoginEntrada(BaseModel):
    email: str
    password: str


class CambioPasswordEntrada(BaseModel):
    password_actual: str
    password_nueva: str


class EmailEntrada(BaseModel):
    email: str


class ConfirmacionRegistroEntrada(BaseModel):
    email: str
    codigo: str


class ConfirmacionRestablecimientoEntrada(BaseModel):
    email: str
    codigo: str
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
        secure=configuracion.cookie_secure,
        samesite="strict",
        path="/",
    )


def _exigir_cognito(configuracion: ConfiguracionAuth) -> ClienteCognito:
    if configuracion.proveedor != PROVEEDOR_AUTH_COGNITO:
        raise HTTPException(
            status_code=409,
            detail="Este entorno no usa Amazon Cognito para autenticación.",
        )
    return ClienteCognito(configuracion)


def _email_valido(email: str) -> str:
    try:
        return normalizar_email(email)
    except EmailInvalidoError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/login")
def login(
    datos: LoginEntrada,
    request: Request,
    response: Response,
    session: Session = Depends(obtener_session),
    configuracion: ConfiguracionAuth = Depends(obtener_configuracion),
) -> dict[str, bool]:
    try:
        resultado = autenticar(
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
    except UsuarioNoConfirmadoError as exc:
        session.commit()
        raise HTTPException(
            status_code=409,
            detail=(
                "Tu cuenta de Cognito todavía no está confirmada. "
                "Usa «Verificar cuenta» con el código que llegó a tu correo."
            ),
        ) from exc
    except ProveedorAuthNoDisponibleError as exc:
        session.rollback()
        raise HTTPException(
            status_code=503,
            detail=(
                "Amazon Cognito no está disponible en este momento. "
                "Intenta de nuevo o avisa a TI."
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
    _poner_cookie(response, configuracion, resultado.usuario)
    return {"debe_cambiar_password": resultado.debe_cambiar_password}


@router.post("/logout", status_code=204)
def logout(
    configuracion: ConfiguracionAuth = Depends(obtener_configuracion),
) -> Response:
    response = Response(status_code=204)
    response.delete_cookie(
        COOKIE_SESION,
        path="/",
        secure=configuracion.cookie_secure,
        httponly=True,
        samesite="strict",
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
    try:
        validar_password_nueva(datos.password_nueva)
    except PasswordDebilError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if datos.password_nueva == datos.password_actual:
        raise HTTPException(
            status_code=422,
            detail="La contraseña nueva debe ser distinta de la actual.",
        )

    if configuracion.proveedor == PROVEEDOR_AUTH_COGNITO:
        try:
            ClienteCognito(configuracion).cambiar_password(
                usuario.email,
                datos.password_actual,
                datos.password_nueva,
            )
        except CognitoCredencialesInvalidas as exc:
            raise HTTPException(
                status_code=400,
                detail="La contraseña actual no es correcta. Escríbela de nuevo.",
            ) from exc
        except CognitoUsuarioNoConfirmado as exc:
            raise HTTPException(
                status_code=409,
                detail="Confirma primero tu cuenta con el código enviado por Cognito.",
            ) from exc
        except CognitoPasswordInvalida as exc:
            raise HTTPException(
                status_code=422,
                detail="La nueva contraseña no cumple la política de Cognito.",
            ) from exc
        except CognitoNoDisponible as exc:
            raise HTTPException(
                status_code=503,
                detail="Amazon Cognito no pudo cambiar la contraseña. Intenta de nuevo.",
            ) from exc
        # PostgreSQL no almacena la contraseña de Cognito. Esta marca aleatoria
        # existe solo para invalidar las sesiones web emitidas antes del cambio.
        usuario.password_hash = generar_marca_sesion_externa()
    else:
        if not verificar_password(usuario.password_hash, datos.password_actual):
            raise HTTPException(
                status_code=400,
                detail="La contraseña actual no es correcta. Escríbela de nuevo.",
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
    # La marca de sesión cambió: se emite una sesión nueva.
    _poner_cookie(response, configuracion, usuario)
    return {"debe_cambiar_password": False}


@router.post("/confirmar-registro")
def confirmar_registro(
    datos: ConfirmacionRegistroEntrada,
    configuracion: ConfiguracionAuth = Depends(obtener_configuracion),
) -> dict[str, bool]:
    cliente = _exigir_cognito(configuracion)
    email = _email_valido(datos.email)
    if not datos.codigo.strip():
        raise HTTPException(status_code=422, detail="Escribe el código de confirmación.")
    try:
        cliente.confirmar_registro(email=email, codigo=datos.codigo.strip())
    except CognitoCodigoInvalido as exc:
        raise HTTPException(
            status_code=422,
            detail="El código de confirmación es incorrecto o expiró.",
        ) from exc
    except CognitoNoDisponible as exc:
        raise HTTPException(
            status_code=503,
            detail="Amazon Cognito no pudo confirmar la cuenta. Intenta de nuevo.",
        ) from exc
    return {"confirmado": True}


@router.post("/reenviar-confirmacion")
def reenviar_confirmacion(
    datos: EmailEntrada,
    configuracion: ConfiguracionAuth = Depends(obtener_configuracion),
) -> dict[str, bool]:
    cliente = _exigir_cognito(configuracion)
    email = _email_valido(datos.email)
    try:
        cliente.reenviar_confirmacion(email=email)
    except CognitoNoDisponible as exc:
        raise HTTPException(
            status_code=503,
            detail="Amazon Cognito no pudo reenviar el código. Intenta de nuevo.",
        ) from exc
    return {"enviado": True}


@router.post("/solicitar-restablecimiento")
def solicitar_restablecimiento(
    datos: EmailEntrada,
    configuracion: ConfiguracionAuth = Depends(obtener_configuracion),
) -> dict[str, bool]:
    cliente = _exigir_cognito(configuracion)
    email = _email_valido(datos.email)
    try:
        cliente.solicitar_restablecimiento(email=email)
    except CognitoNoDisponible as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Amazon Cognito no pudo iniciar el restablecimiento. "
                "Intenta de nuevo."
            ),
        ) from exc
    # Siempre es genérico para no revelar si el correo existe.
    return {"enviado": True}


@router.post("/confirmar-restablecimiento")
def confirmar_restablecimiento(
    datos: ConfirmacionRestablecimientoEntrada,
    request: Request,
    configuracion: ConfiguracionAuth = Depends(obtener_configuracion),
    session: Session = Depends(obtener_session),
) -> dict[str, bool]:
    cliente = _exigir_cognito(configuracion)
    email = _email_valido(datos.email)
    try:
        validar_password_nueva(datos.password_nueva)
    except PasswordDebilError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not datos.codigo.strip():
        raise HTTPException(status_code=422, detail="Escribe el código recibido.")

    try:
        cliente.confirmar_restablecimiento(
            email=email,
            codigo=datos.codigo.strip(),
            password_nueva=datos.password_nueva,
        )
    except CognitoCodigoInvalido as exc:
        raise HTTPException(
            status_code=422,
            detail="El código de restablecimiento es incorrecto o expiró.",
        ) from exc
    except CognitoPasswordInvalida as exc:
        raise HTTPException(
            status_code=422,
            detail="La nueva contraseña no cumple la política de Cognito.",
        ) from exc
    except CognitoNoDisponible as exc:
        raise HTTPException(
            status_code=503,
            detail="Amazon Cognito no pudo completar el restablecimiento.",
        ) from exc

    usuario = session.scalar(select(Usuario).where(Usuario.email == email))
    if usuario is not None:
        usuario.password_hash = generar_marca_sesion_externa()
        usuario.debe_cambiar_password = False
        registrar_auditoria(
            session,
            usuario_id=usuario.id,
            accion="usuario.restablecer_password_cognito",
            entidad="usuario",
            entidad_id=usuario.id,
            ip=ip_de(request),
        )
        session.commit()

    return {"restablecido": True}
