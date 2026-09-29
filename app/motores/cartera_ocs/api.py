import mimetypes
import os
from dataclasses import asdict
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth.dependencias import Acceso, requiere
from app.core.session import obtener_session
from app.motores.cartera_ocs.almacenamiento import (
    AlmacenComprobantes,
    AlmacenLocalComprobantes,
)
from app.motores.cartera_ocs.bandeja import (
    contar_comprobantes_pendientes,
    listar_comprobantes_pendientes,
)
from app.motores.cartera_ocs.comprobantes import radicar_comprobante
from app.motores.cartera_ocs.consultas import (
    FuenteOperacionesCartera,
    OperacionNoEncontradaError,
    listar_operaciones,
    obtener_detalle_operacion,
)
from app.motores.cartera_ocs.financiacion import (
    OperacionFinanciada,
    generar_condicion_pago,
)
from app.motores.cartera_ocs.google_sheets import (
    ConfiguracionGoogleSheetsIncompletaError,
    construir_fuente_google_sheets_desde_entorno,
    construir_fuente_mora_google_sheets_desde_entorno,
    construir_fuente_proyeccion_google_sheets_desde_entorno,
    diagnosticar_fuente_google_sheets_desde_entorno,
)
from app.motores.cartera_ocs.mora import (
    FuenteMoraCartera,
    listar_mora,
)
from app.motores.cartera_ocs.proyeccion import (
    FuenteProyeccionCartera,
    listar_proyeccion,
)
from app.motores.cartera_ocs.persistencia import (
    existe_comprobante_por_hash,
    guardar_comprobante,
    obtener_comprobante_por_empresa,
)


router = APIRouter(prefix="/cartera", tags=["cartera"])

TIPOS_COMPROBANTE_DEFAULT = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}
MAX_COMPROBANTE_BYTES_DEFAULT = 10 * 1024 * 1024


CENTAVO = Decimal("0.01")


def _dinero_texto(valor: Decimal) -> str:
    return format(valor.quantize(CENTAVO), "f")


def _decimal_texto(valor: Decimal) -> str:
    return format(valor, "f")


def _operacion_como_dict(operacion: object) -> dict[str, object]:
    data = asdict(operacion)
    data["valor"] = _dinero_texto(operacion.valor)
    data["valor_anticipo"] = _dinero_texto(operacion.valor_anticipo)
    data["valor_financiado"] = _dinero_texto(operacion.valor_financiado)
    data["porcentaje_anticipo"] = _decimal_texto(
        operacion.porcentaje_anticipo
    )
    return data


def _mora_como_dict(registro: object) -> dict[str, object]:
    data = asdict(registro)
    data["monto"] = _dinero_texto(registro.monto)
    return data


def _proyeccion_como_dict(registro: object) -> dict[str, object]:
    data = asdict(registro)
    data["dias"] = _decimal_texto(registro.dias)
    data["valor_oc"] = _dinero_texto(registro.valor_oc)
    data["monto"] = _dinero_texto(registro.monto)
    return data


def _empresa_de_query(empresa_id: int) -> int:
    return empresa_id


def _empresa_de_form(empresa_id: int = Form(...)) -> int:
    return empresa_id


ver_cartera = requiere("cartera.ver", empresa_de=_empresa_de_query)
subir_comprobante_permitido = requiere(
    "cartera.comprobantes.subir", empresa_de=_empresa_de_form
)


def _tipos_comprobante_permitidos() -> set[str]:
    configurados = os.getenv("CARTERA_COMPROBANTES_MIME_TYPES")
    if not configurados:
        return TIPOS_COMPROBANTE_DEFAULT
    return {
        tipo.strip()
        for tipo in configurados.split(",")
        if tipo.strip()
    }


def _max_comprobante_bytes() -> int:
    return int(
        os.getenv(
            "CARTERA_COMPROBANTES_MAX_BYTES",
            str(MAX_COMPROBANTE_BYTES_DEFAULT),
        )
    )


def obtener_fuente_operaciones() -> FuenteOperacionesCartera:
    try:
        return construir_fuente_google_sheets_desde_entorno()
    except ConfiguracionGoogleSheetsIncompletaError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc


def obtener_fuente_mora() -> FuenteMoraCartera:
    try:
        return construir_fuente_mora_google_sheets_desde_entorno()
    except ConfiguracionGoogleSheetsIncompletaError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc


def obtener_fuente_proyeccion() -> FuenteProyeccionCartera:
    try:
        return construir_fuente_proyeccion_google_sheets_desde_entorno()
    except ConfiguracionGoogleSheetsIncompletaError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc


def obtener_estado_fuente(
    empresa_id: int,
) -> dict[str, object]:
    return diagnosticar_fuente_google_sheets_desde_entorno(
        empresa_id=empresa_id,
    )


def obtener_almacen_comprobantes() -> AlmacenComprobantes:
    directorio = os.getenv(
        "CARTERA_COMPROBANTES_DIR",
        "./data/comprobantes",
    )
    return AlmacenLocalComprobantes(directorio)


@router.get("/fuente/estado")
def consultar_estado_fuente(
    empresa_id: int,
    _acceso: Acceso = Depends(ver_cartera),
    estado: dict[str, object] = Depends(obtener_estado_fuente),
) -> dict[str, object]:
    return estado


@router.get("/operaciones")
def consultar_operaciones(
    empresa_id: int,
    _acceso: Acceso = Depends(ver_cartera),
    fuente: FuenteOperacionesCartera = Depends(obtener_fuente_operaciones),
) -> list[dict[str, object]]:
    return [
        _operacion_como_dict(operacion)
        for operacion in listar_operaciones(
            fuente,
            empresa_id=empresa_id,
        )
    ]


@router.get("/mora")
def consultar_mora(
    empresa_id: int,
    _acceso: Acceso = Depends(ver_cartera),
    fuente: FuenteMoraCartera = Depends(obtener_fuente_mora),
) -> list[dict[str, object]]:
    return [
        _mora_como_dict(registro)
        for registro in listar_mora(
            fuente,
            empresa_id=empresa_id,
        )
    ]


@router.get("/proyeccion")
def consultar_proyeccion(
    empresa_id: int,
    _acceso: Acceso = Depends(ver_cartera),
    fuente: FuenteProyeccionCartera = Depends(obtener_fuente_proyeccion),
) -> list[dict[str, object]]:
    return [
        _proyeccion_como_dict(registro)
        for registro in listar_proyeccion(
            fuente,
            empresa_id=empresa_id,
        )
    ]


@router.get("/operaciones/{oc}")
def consultar_detalle_operacion(
    oc: str,
    empresa_id: int,
    _acceso: Acceso = Depends(ver_cartera),
    fuente: FuenteOperacionesCartera = Depends(obtener_fuente_operaciones),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    try:
        detalle = obtener_detalle_operacion(
            fuente,
            empresa_id=empresa_id,
            oc=oc,
        )
    except OperacionNoEncontradaError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró la operación {oc}.",
        ) from exc

    respuesta = {
        "oc": detalle.oc,
        "lineas": [
            _operacion_como_dict(linea)
            for linea in detalle.lineas
        ],
    }
    respuesta["comprobantes_pendientes"] = contar_comprobantes_pendientes(
        session,
        empresa_id=empresa_id,
        oc=oc,
    )
    return respuesta


@router.get("/comprobantes/pendientes")
def consultar_comprobantes_pendientes(
    empresa_id: int,
    _acceso: Acceso = Depends(ver_cartera),
    session: Session = Depends(obtener_session),
) -> list[dict[str, object]]:
    pendientes = listar_comprobantes_pendientes(
        session,
        empresa_id=empresa_id,
    )

    return [
        {
            "id": item.id,
            "oc": item.oc,
            "cliente": item.cliente,
            "pais": item.pais,
            "comercial": item.comercial,
            "monto_esperado": _dinero_texto(item.monto_esperado),
            "nombre_archivo": item.nombre_archivo,
            "estado_auditoria": item.estado_auditoria,
            "creado_en": item.creado_en,
        }
        for item in pendientes
    ]


@router.get("/comprobantes/{comprobante_id}/archivo")
def consultar_archivo_comprobante(
    comprobante_id: int,
    empresa_id: int,
    _acceso: Acceso = Depends(ver_cartera),
    session: Session = Depends(obtener_session),
    almacen: AlmacenComprobantes = Depends(obtener_almacen_comprobantes),
) -> Response:
    comprobante = obtener_comprobante_por_empresa(
        session,
        empresa_id=empresa_id,
        comprobante_id=comprobante_id,
    )
    if comprobante is None or not comprobante.ubicacion_archivo:
        raise HTTPException(
            status_code=404,
            detail="No se encontró el archivo del comprobante.",
        )

    try:
        contenido = almacen.leer(comprobante.ubicacion_archivo)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=404,
            detail="No se encontró el archivo del comprobante.",
        ) from exc

    media_type = (
        mimetypes.guess_type(comprobante.nombre_archivo)[0]
        or "application/octet-stream"
    )
    return Response(
        content=contenido,
        media_type=media_type,
        headers={
            "Content-Disposition": (
                f'inline; filename="{comprobante.nombre_archivo}"'
            )
        },
    )


@router.post("/comprobantes", status_code=201)
def subir_comprobante(
    empresa_id: int = Form(...),
    _acceso: Acceso = Depends(subir_comprobante_permitido),
    oc: str = Form(...),
    cliente: str = Form(...),
    pais: str = Form(...),
    valor_ddp: Decimal = Form(...),
    tipo_negociacion: str = Form(...),
    fecha_entrega: date = Form(...),
    comercial: str = Form(...),
    archivo: UploadFile = File(...),
    session: Session = Depends(obtener_session),
    almacen: AlmacenComprobantes = Depends(obtener_almacen_comprobantes),
) -> dict[str, object]:
    if archivo.content_type not in _tipos_comprobante_permitidos():
        raise HTTPException(
            status_code=415,
            detail="Tipo de archivo de comprobante no permitido.",
        )

    contenido = archivo.file.read()
    if not contenido:
        raise HTTPException(
            status_code=400,
            detail="El comprobante no puede estar vacío.",
        )
    if len(contenido) > _max_comprobante_bytes():
        raise HTTPException(
            status_code=413,
            detail="El comprobante supera el tamaño máximo permitido.",
        )

    operacion = OperacionFinanciada(
        oc=oc,
        cliente=cliente,
        pais=pais,
        valor_ddp=valor_ddp,
        tipo_negociacion=tipo_negociacion,
        fecha_entrega=fecha_entrega,
        comercial=comercial,
    )
    condicion = generar_condicion_pago(operacion)

    nombre_archivo = archivo.filename or "comprobante.bin"
    comprobante = radicar_comprobante(
        condicion=condicion,
        nombre_archivo=nombre_archivo,
        contenido=contenido,
    )

    if existe_comprobante_por_hash(
        session,
        empresa_id=empresa_id,
        contenido_hash=comprobante.contenido_hash,
    ):
        raise HTTPException(
            status_code=409,
            detail="Este comprobante ya fue radicado para la empresa.",
        )

    ubicacion = almacen.guardar(
        empresa_id=empresa_id,
        oc=comprobante.oc,
        nombre_archivo=comprobante.nombre_archivo,
        contenido_hash=comprobante.contenido_hash,
        contenido=contenido,
    )

    try:
        registro = guardar_comprobante(
            session,
            empresa_id=empresa_id,
            comprobante=comprobante,
            ubicacion_archivo=ubicacion,
        )
        session.commit()
        session.refresh(registro)
    except IntegrityError as exc:
        session.rollback()
        almacen.eliminar(ubicacion)
        raise HTTPException(
            status_code=409,
            detail="Este comprobante ya fue radicado para la empresa.",
        ) from exc
    except Exception:
        session.rollback()
        almacen.eliminar(ubicacion)
        raise

    return {
        "id": registro.id,
        "oc": registro.oc,
        "estado_auditoria": registro.estado_auditoria,
        "monto_esperado": _dinero_texto(registro.monto_esperado),
        "contenido_hash": registro.contenido_hash,
    }
