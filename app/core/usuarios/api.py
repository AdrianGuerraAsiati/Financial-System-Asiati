from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auditoria import registrar_auditoria
from app.core.auth.cognito import (
    ClienteCognito,
    CognitoNoDisponible,
    CognitoPasswordInvalida,
    CognitoUsuarioExiste,
)
from app.core.auth.config import ConfiguracionAuth, PROVEEDOR_AUTH_COGNITO
from app.core.auth.dependencias import Acceso, obtener_configuracion, requiere
from app.core.auth.passwords import (
    generar_marca_sesion_externa,
    generar_password_temporal,
    hashear_password,
)
from app.core.empresas import Empresa
from app.core.session import obtener_session
from app.core.usuarios.errors import EmailInvalidoError, RolUsuarioInvalidoError
from app.core.usuarios.model import Usuario, UsuarioEmpresa
from app.core.usuarios.roles import ROL_COORDINACION_FINANCIERA, ROL_SUPER_ADMINISTRADOR
from app.core.usuarios.service import crear_usuario, normalizar_email, validar_rol


router = APIRouter(prefix="/usuarios", tags=["usuarios"])

gestionar = requiere("usuarios.gestionar")


class UsuarioCrear(BaseModel):
    email: str
    nombre: str
    rol: str
    # Omitido: el coordinador recibe todas las empresas; los demás, ninguna.
    empresas: list[int] | None = None


class UsuarioEditar(BaseModel):
    nombre: str | None = None
    rol: str | None = None
    activo: bool | None = None


class EmpresasAsignar(BaseModel):
    empresas: list[int]


def _empresas_de(session: Session, usuario_id: int) -> list[int]:
    return sorted(
        session.scalars(
            select(UsuarioEmpresa.empresa_id).where(
                UsuarioEmpresa.usuario_id == usuario_id
            )
        )
    )


def _usuario_json(session: Session, usuario: Usuario) -> dict[str, object]:
    return {
        "id": usuario.id,
        "email": usuario.email,
        "nombre": usuario.nombre,
        "rol": usuario.rol,
        "activo": usuario.activo,
        "debe_cambiar_password": usuario.debe_cambiar_password,
        "ultimo_ingreso_at": (
            usuario.ultimo_ingreso_at.isoformat() if usuario.ultimo_ingreso_at else None
        ),
        "empresas": _empresas_de(session, usuario.id),
    }


def _obtener(session: Session, usuario_id: int) -> Usuario:
    usuario = session.get(Usuario, usuario_id)
    if usuario is None:
        raise HTTPException(
            status_code=404,
            detail="No encontramos ese usuario. Revisa el identificador en la lista.",
        )
    return usuario


def _validar_empresas(session: Session, empresas: list[int]) -> list[int]:
    pedidas = sorted(set(empresas))
    existentes = set(
        session.scalars(select(Empresa.id).where(Empresa.id.in_(pedidas)))
    )
    faltantes = [empresa_id for empresa_id in pedidas if empresa_id not in existentes]
    if faltantes:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Estas empresas no existen: {faltantes}. "
                "Revisa los identificadores en la lista de empresas."
            ),
        )
    return pedidas


def _asignar(
    session: Session, usuario_id: int, empresas: list[int], asignado_por: int
) -> None:
    session.execute(
        delete(UsuarioEmpresa).where(UsuarioEmpresa.usuario_id == usuario_id)
    )
    for empresa_id in empresas:
        session.add(
            UsuarioEmpresa(
                usuario_id=usuario_id,
                empresa_id=empresa_id,
                asignado_por=asignado_por,
            )
        )


def _estado_auditable(usuario: Usuario) -> dict[str, object]:
    # Nunca incluye password_hash ni marcas de sesión.
    return {
        "email": usuario.email,
        "nombre": usuario.nombre,
        "rol": usuario.rol,
        "activo": usuario.activo,
    }


@router.get("")
def listar_usuarios(
    acceso: Acceso = Depends(gestionar),
    session: Session = Depends(obtener_session),
) -> list[dict[str, object]]:
    usuarios = session.scalars(select(Usuario).order_by(Usuario.id))
    return [_usuario_json(session, usuario) for usuario in usuarios]


@router.post("", status_code=201)
def crear(
    datos: UsuarioCrear,
    acceso: Acceso = Depends(gestionar),
    session: Session = Depends(obtener_session),
    configuracion: ConfiguracionAuth = Depends(obtener_configuracion),
) -> dict[str, object]:
    try:
        email = normalizar_email(datos.email)
        validar_rol(datos.rol)
    except (EmailInvalidoError, RolUsuarioInvalidoError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not datos.nombre.strip():
        raise HTTPException(status_code=422, detail="Escribe el nombre del usuario.")
    if session.scalar(select(Usuario.id).where(Usuario.email == email)) is not None:
        raise HTTPException(
            status_code=409,
            detail="Ya existe un usuario con ese correo. Búscalo en la lista y edítalo.",
        )

    if datos.empresas is None:
        empresas = (
            list(session.scalars(select(Empresa.id)))
            if datos.rol == ROL_COORDINACION_FINANCIERA
            else []
        )
    else:
        empresas = datos.empresas
    empresas = _validar_empresas(session, empresas)

    password_temporal = generar_password_temporal()
    usa_cognito = configuracion.proveedor == PROVEEDOR_AUTH_COGNITO

    if usa_cognito:
        try:
            ClienteCognito(configuracion).registrar_usuario(
                email=email,
                nombre=datos.nombre.strip(),
                password_temporal=password_temporal,
            )
        except CognitoUsuarioExiste as exc:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Ese correo ya existe en Amazon Cognito. "
                    "Avisa a TI para vincular o limpiar la identidad antes de reintentar."
                ),
            ) from exc
        except CognitoPasswordInvalida as exc:
            raise HTTPException(
                status_code=422,
                detail="La contraseña temporal no cumple la política de Cognito.",
            ) from exc
        except CognitoNoDisponible as exc:
            raise HTTPException(
                status_code=503,
                detail="Amazon Cognito no pudo crear la identidad. Intenta de nuevo.",
            ) from exc
        password_hash = generar_marca_sesion_externa()
    else:
        password_hash = hashear_password(password_temporal)

    usuario = crear_usuario(
        session,
        email=email,
        nombre=datos.nombre,
        rol=datos.rol,
        password_hash=password_hash,
        creado_por=acceso.usuario.id,
    )
    session.flush()
    _asignar(session, usuario.id, empresas, acceso.usuario.id)
    registrar_auditoria(
        session,
        usuario_id=acceso.usuario.id,
        accion="usuario.crear",
        entidad="usuario",
        entidad_id=usuario.id,
        despues={
            **_estado_auditable(usuario),
            "empresas": empresas,
            "proveedor_auth": configuracion.proveedor,
        },
        ip=acceso.ip,
    )
    try:
        session.commit()
    except IntegrityError as exc:
        # Otro superadministrador creó el mismo correo al mismo tiempo.
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Ya existe un usuario con ese correo. Búscalo en la lista y edítalo.",
        ) from exc

    # En Cognito, el usuario también recibe un código de confirmación por correo.
    # La contraseña temporal solo se muestra en esta respuesta.
    return {
        "usuario": _usuario_json(session, usuario),
        "password_temporal": password_temporal,
        "confirmacion_requerida": usa_cognito,
    }


@router.patch("/{usuario_id}")
def editar(
    usuario_id: int,
    datos: UsuarioEditar,
    acceso: Acceso = Depends(gestionar),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    usuario = _obtener(session, usuario_id)
    if datos.rol is not None:
        try:
            validar_rol(datos.rol)
        except RolUsuarioInvalidoError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    if datos.nombre is not None and not datos.nombre.strip():
        raise HTTPException(status_code=422, detail="El nombre no puede quedar vacío.")
    if usuario.id == acceso.usuario.id and (
        datos.activo is False
        or (datos.rol is not None and datos.rol != ROL_SUPER_ADMINISTRADOR)
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "No puedes desactivarte ni quitarte el rol de superadministrador. "
                "Pídeselo a otro superadministrador."
            ),
        )

    antes = _estado_auditable(usuario)
    if datos.nombre is not None:
        usuario.nombre = datos.nombre.strip()
    if datos.rol is not None:
        usuario.rol = datos.rol
    if datos.activo is not None:
        usuario.activo = datos.activo
    registrar_auditoria(
        session,
        usuario_id=acceso.usuario.id,
        accion="usuario.editar",
        entidad="usuario",
        entidad_id=usuario.id,
        antes=antes,
        despues=_estado_auditable(usuario),
        ip=acceso.ip,
    )
    session.commit()
    return _usuario_json(session, usuario)


@router.put("/{usuario_id}/empresas")
def asignar_empresas(
    usuario_id: int,
    datos: EmpresasAsignar,
    acceso: Acceso = Depends(gestionar),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    usuario = _obtener(session, usuario_id)
    empresas = _validar_empresas(session, datos.empresas)
    antes = _empresas_de(session, usuario.id)

    _asignar(session, usuario.id, empresas, acceso.usuario.id)
    registrar_auditoria(
        session,
        usuario_id=acceso.usuario.id,
        accion="usuario.asignar_empresas",
        entidad="usuario",
        entidad_id=usuario.id,
        antes={"empresas": antes},
        despues={"empresas": empresas},
        ip=acceso.ip,
    )
    session.commit()
    return _usuario_json(session, usuario)


@router.post("/{usuario_id}/restablecer")
def restablecer_password(
    usuario_id: int,
    acceso: Acceso = Depends(gestionar),
    session: Session = Depends(obtener_session),
    configuracion: ConfiguracionAuth = Depends(obtener_configuracion),
) -> dict[str, object]:
    usuario = _obtener(session, usuario_id)

    if configuracion.proveedor == PROVEEDOR_AUTH_COGNITO:
        try:
            ClienteCognito(configuracion).solicitar_restablecimiento(
                email=usuario.email
            )
        except CognitoNoDisponible as exc:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Amazon Cognito no pudo iniciar el restablecimiento. "
                    "Intenta de nuevo."
                ),
            ) from exc

        # Invalida sesiones abiertas en la plataforma. Cognito enviará el código
        # de recuperación al correo verificado.
        usuario.password_hash = generar_marca_sesion_externa()
        usuario.debe_cambiar_password = True
        registrar_auditoria(
            session,
            usuario_id=acceso.usuario.id,
            accion="usuario.restablecer_password",
            entidad="usuario",
            entidad_id=usuario.id,
            despues={"proveedor_auth": "cognito", "correo_enviado": True},
            ip=acceso.ip,
        )
        session.commit()
        return {
            "usuario": _usuario_json(session, usuario),
            "restablecimiento": "correo_enviado",
        }

    password_temporal = generar_password_temporal()
    # Cambiar el hash invalida las sesiones abiertas del usuario.
    usuario.password_hash = hashear_password(password_temporal)
    usuario.debe_cambiar_password = True
    registrar_auditoria(
        session,
        usuario_id=acceso.usuario.id,
        accion="usuario.restablecer_password",
        entidad="usuario",
        entidad_id=usuario.id,
        ip=acceso.ip,
    )
    session.commit()
    return {
        "usuario": _usuario_json(session, usuario),
        "password_temporal": password_temporal,
    }
