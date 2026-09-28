import os
from dataclasses import asdict
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.session import obtener_session
from app.motores.cartera_ocs.almacenamiento import (
    AlmacenComprobantes,
    AlmacenLocalComprobantes,
)
from app.motores.cartera_ocs.bandeja import listar_comprobantes_pendientes
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
from app.motores.cartera_ocs.persistencia import guardar_comprobante


router = APIRouter(prefix="/cartera", tags=["cartera"])


def obtener_fuente_operaciones() -> FuenteOperacionesCartera:
    raise HTTPException(
        status_code=503,
        detail="La fuente de operaciones de Cartera todavía no está configurada.",
    )


def obtener_almacen_comprobantes() -> AlmacenComprobantes:
    directorio = os.getenv(
        "CARTERA_COMPROBANTES_DIR",
        "./data/comprobantes",
    )
    return AlmacenLocalComprobantes(directorio)


@router.get("/operaciones")
def consultar_operaciones(
    empresa_id: int,
    fuente: FuenteOperacionesCartera = Depends(obtener_fuente_operaciones),
) -> list[dict[str, object]]:
    return [
        asdict(operacion)
        for operacion in listar_operaciones(
            fuente,
            empresa_id=empresa_id,
        )
    ]


@router.get("/operaciones/{oc}")
def consultar_detalle_operacion(
    oc: str,
    empresa_id: int,
    fuente: FuenteOperacionesCartera = Depends(obtener_fuente_operaciones),
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

    return asdict(detalle)


@router.get("/comprobantes/pendientes")
def consultar_comprobantes_pendientes(
    empresa_id: int,
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
            "monto_esperado": float(item.monto_esperado),
            "nombre_archivo": item.nombre_archivo,
            "estado_auditoria": item.estado_auditoria,
            "creado_en": item.creado_en,
        }
        for item in pendientes
    ]


@router.post("/comprobantes", status_code=201)
def subir_comprobante(
    empresa_id: int = Form(...),
    oc: str = Form(...),
    cliente: str = Form(...),
    pais: str = Form(...),
    valor_ddp: float = Form(...),
    tipo_negociacion: str = Form(...),
    fecha_entrega: date = Form(...),
    comercial: str = Form(...),
    archivo: UploadFile = File(...),
    session: Session = Depends(obtener_session),
    almacen: AlmacenComprobantes = Depends(obtener_almacen_comprobantes),
) -> dict[str, object]:
    contenido = archivo.file.read()
    if not contenido:
        raise HTTPException(
            status_code=400,
            detail="El comprobante no puede estar vacío.",
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

    ubicacion = almacen.guardar(
        empresa_id=empresa_id,
        oc=comprobante.oc,
        nombre_archivo=comprobante.nombre_archivo,
        contenido_hash=comprobante.contenido_hash,
        contenido=contenido,
    )

    registro = guardar_comprobante(
        session,
        empresa_id=empresa_id,
        comprobante=comprobante,
        ubicacion_archivo=ubicacion,
    )
    session.commit()
    session.refresh(registro)

    return {
        "id": registro.id,
        "oc": registro.oc,
        "estado_auditoria": registro.estado_auditoria,
        "monto_esperado": float(registro.monto_esperado),
        "contenido_hash": registro.contenido_hash,
        "ubicacion_archivo": registro.ubicacion_archivo,
    }
