import mimetypes
import os
from dataclasses import asdict
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auditoria.service import registrar_auditoria
from app.core.auth.dependencias import Acceso, requiere
from app.core.session import obtener_session
from app.motores.cartera_ocs.agrupacion import (
    OperacionAgrupadaCartera,
    agrupar_operaciones_por_oc,
)
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
from app.motores.cartera_ocs.descubrimiento import (
    descubrir_hojas_cartera_desde_entorno,
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
from app.motores.cartera_ocs.negociaciones import (
    diagnosticar_negociaciones,
)
from app.motores.cartera_ocs.proyeccion import (
    FuenteProyeccionCartera,
    listar_proyeccion,
)
from app.motores.cartera_ocs.resumen import (
    AgrupacionMontoCartera,
    resumir_mora,
    resumir_operaciones,
    resumir_proyeccion,
)
from app.motores.cartera_ocs.validacion import validar_cartera_en_camino
from app.motores.cartera_ocs.snapshots import (
    LecturaSnapshotCarteraError,
    capturar_snapshot_cartera_desde_entorno,
    guardar_snapshot_cartera,
    listar_snapshots_cartera,
    snapshot_cartera_como_dict,
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


def _operacion_agrupada_como_dict(
    operacion: OperacionAgrupadaCartera,
) -> dict[str, object]:
    return {
        "oc": operacion.oc,
        "lineas": len(operacion.lineas),
        "clientes": list(operacion.clientes),
        "negociaciones": list(operacion.negociaciones),
        "estados": list(operacion.estados),
        "etapas": list(operacion.etapas),
        "modos_transporte": list(operacion.modos_transporte),
        "documentos_transporte": list(operacion.documentos_transporte),
        "skus": list(operacion.skus),
        "valor_ddp": _dinero_texto(operacion.valor_ddp),
        "valor_anticipo": _dinero_texto(operacion.valor_anticipo),
        "valor_financiado": _dinero_texto(operacion.valor_financiado),
        "tiene_multiples_clientes": operacion.tiene_multiples_clientes,
        "tiene_multiples_negociaciones": (
            operacion.tiene_multiples_negociaciones
        ),
        "tiene_multiples_estados": operacion.tiene_multiples_estados,
        "tiene_multiples_etapas": operacion.tiene_multiples_etapas,
    }


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


def _agrupacion_como_dict(
    agrupacion: AgrupacionMontoCartera,
) -> dict[str, object]:
    return {
        "clave": agrupacion.clave,
        "registros": agrupacion.registros,
        "monto": _dinero_texto(agrupacion.monto),
    }


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


def obtener_descubrimiento_fuente(
    empresa_id: int,
) -> dict[str, object]:
    try:
        return descubrir_hojas_cartera_desde_entorno(
            empresa_id=empresa_id,
        )
    except ConfiguracionGoogleSheetsIncompletaError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc


def obtener_almacen_comprobantes() -> AlmacenComprobantes:
    directorio = os.getenv(
        "CARTERA_COMPROBANTES_DIR",
        "./data/comprobantes",
    )
    return AlmacenLocalComprobantes(directorio)


@router.get("/fuente/descubrir")
def consultar_descubrimiento_fuente(
    empresa_id: int,
    _acceso: Acceso = Depends(ver_cartera),
    resultado: dict[str, object] = Depends(obtener_descubrimiento_fuente),
) -> dict[str, object]:
    return resultado


@router.get("/fuente/estado")
def consultar_estado_fuente(
    empresa_id: int,
    _acceso: Acceso = Depends(ver_cartera),
    estado: dict[str, object] = Depends(obtener_estado_fuente),
) -> dict[str, object]:
    return estado


@router.post("/snapshots", status_code=201)
def capturar_snapshot_cartera(
    empresa_id: int,
    _acceso: Acceso = Depends(ver_cartera),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    try:
        snapshot = capturar_snapshot_cartera_desde_entorno(
            empresa_id=empresa_id,
        )
    except (
        ConfiguracionGoogleSheetsIncompletaError,
        LecturaSnapshotCarteraError,
    ) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    persistido, creado = guardar_snapshot_cartera(
        session,
        empresa_id=empresa_id,
        snapshot=snapshot,
    )
    if creado:
        registrar_auditoria(
            session,
            usuario_id=_acceso.usuario.id,
            empresa_id=empresa_id,
            accion="cartera.snapshot_guardado",
            entidad="cartera_snapshot",
            entidad_id=persistido.id,
            despues={
                "contenido_hash": persistido.contenido_hash,
                "filas": persistido.filas,
                "operaciones": persistido.operaciones,
                "registros_mora": persistido.registros_mora,
                "proyecciones": persistido.proyecciones,
            },
            ip=_acceso.ip,
        )
    session.commit()
    session.refresh(persistido)

    return {
        "creado": creado,
        "snapshot": snapshot_cartera_como_dict(persistido),
        "nota": (
            "La captura se guarda en la base de datos de la plataforma. "
            "Google Sheets permanece estrictamente en modo solo lectura."
        ),
    }


@router.get("/snapshots")
def consultar_snapshots_cartera(
    empresa_id: int,
    limit: int = Query(50, ge=1, le=200),
    _acceso: Acceso = Depends(ver_cartera),
    session: Session = Depends(obtener_session),
) -> dict[str, object]:
    snapshots = listar_snapshots_cartera(
        session,
        empresa_id=empresa_id,
        limite=limit,
    )
    return {
        "total": len(snapshots),
        "items": [
            snapshot_cartera_como_dict(item)
            for item in snapshots
        ],
        "nota": (
            "Histórico inmutable de capturas de la fuente de Cartera. "
            "No sustituye Google Sheets como fuente operativa."
        ),
    }


@router.get("/calidad")
def consultar_calidad(
    empresa_id: int,
    _acceso: Acceso = Depends(ver_cartera),
    fuente: FuenteOperacionesCartera = Depends(obtener_fuente_operaciones),
) -> dict[str, object]:
    registros = listar_operaciones(
        fuente,
        empresa_id=empresa_id,
    )
    casos = validar_cartera_en_camino(registros)

    return {
        "registros": len(registros),
        "casos": len(casos),
        "detalle": [
            {
                "codigo": caso.codigo,
                "cantidad": caso.cantidad,
                "valor": _dinero_texto(caso.valor),
                "registros": [
                    _operacion_como_dict(registro)
                    for registro in caso.registros
                ],
            }
            for caso in casos
        ],
    }


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


@router.get("/ocs")
def consultar_ocs_agrupadas(
    empresa_id: int,
    _acceso: Acceso = Depends(ver_cartera),
    fuente: FuenteOperacionesCartera = Depends(obtener_fuente_operaciones),
) -> dict[str, object]:
    registros = listar_operaciones(
        fuente,
        empresa_id=empresa_id,
    )
    agrupadas = agrupar_operaciones_por_oc(registros)
    return {
        "total": len(agrupadas),
        "lineas_sin_oc": sum(
            1
            for registro in registros
            if not str(registro.oc or "").strip()
        ),
        "items": [
            _operacion_agrupada_como_dict(item)
            for item in agrupadas
        ],
        "nota": (
            "Cada OC conserva su composición observada. "
            "No se asigna un único estado o negociación cuando hay múltiples."
        ),
    }


@router.get("/negociaciones/diagnostico")
def consultar_diagnostico_negociaciones(
    empresa_id: int,
    _acceso: Acceso = Depends(ver_cartera),
    fuente: FuenteOperacionesCartera = Depends(obtener_fuente_operaciones),
) -> dict[str, object]:
    patrones = diagnosticar_negociaciones(
        listar_operaciones(
            fuente,
            empresa_id=empresa_id,
        )
    )
    return {
        "patrones": len(patrones),
        "requieren_revision": sum(
            1
            for patron in patrones
            if patron.diagnostico.requiere_revision
        ),
        "items": [
            {
                "texto": patron.texto,
                "lineas": patron.lineas,
                "valor_ddp": _dinero_texto(patron.valor_ddp),
                "porcentaje_saldo": _decimal_texto(
                    patron.diagnostico.terminos.porcentaje_saldo
                ),
                "dias_plazo": patron.diagnostico.terminos.dias_plazo,
                "porcentajes_detectados": list(
                    patron.diagnostico.porcentajes_detectados
                ),
                "dias_detectados": patron.diagnostico.dias_detectados,
                "porcentaje_interpretable": (
                    patron.diagnostico.porcentaje_interpretable
                ),
                "plazo_interpretable": (
                    patron.diagnostico.plazo_interpretable
                ),
                "requiere_revision": patron.diagnostico.requiere_revision,
                "motivos_revision": list(
                    patron.diagnostico.motivos_revision
                ),
            }
            for patron in patrones
        ],
        "nota": (
            "El diagnóstico conserva las reglas heredadas de MAJO. "
            "Solo hace visibles los fallbacks del parser."
        ),
    }


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


@router.get("/operaciones/resumen")
def consultar_resumen_operaciones(
    empresa_id: int,
    _acceso: Acceso = Depends(ver_cartera),
    fuente: FuenteOperacionesCartera = Depends(obtener_fuente_operaciones),
) -> dict[str, object]:
    resumen = resumir_operaciones(
        listar_operaciones(
            fuente,
            empresa_id=empresa_id,
        )
    )
    return {
        "lineas": resumen.lineas,
        "ocs": resumen.ocs,
        "clientes": resumen.clientes,
        "valor_ddp": _dinero_texto(resumen.valor_ddp),
        "valor_anticipo": _dinero_texto(resumen.valor_anticipo),
        "valor_financiado": _dinero_texto(resumen.valor_financiado),
        "por_etapa": [
            _agrupacion_como_dict(item)
            for item in resumen.por_etapa
        ],
        "nota": (
            "Resumen descriptivo de las líneas observadas; "
            "no define saldo de cartera."
        ),
    }


@router.get("/mora/resumen")
def consultar_resumen_mora(
    empresa_id: int,
    _acceso: Acceso = Depends(ver_cartera),
    fuente: FuenteMoraCartera = Depends(obtener_fuente_mora),
) -> dict[str, object]:
    resumen = resumir_mora(
        listar_mora(
            fuente,
            empresa_id=empresa_id,
        )
    )
    return {
        "registros": resumen.registros,
        "clientes": resumen.clientes,
        "monto": _dinero_texto(resumen.monto),
        "por_estado": [
            _agrupacion_como_dict(item)
            for item in resumen.por_estado
        ],
        "por_empresa": [
            _agrupacion_como_dict(item)
            for item in resumen.por_empresa
        ],
        "nota": (
            "Resumen descriptivo de la fuente de Mora; "
            "los estados se conservan sin reinterpretación."
        ),
    }


@router.get("/proyeccion/resumen")
def consultar_resumen_proyeccion(
    empresa_id: int,
    _acceso: Acceso = Depends(ver_cartera),
    fuente: FuenteProyeccionCartera = Depends(obtener_fuente_proyeccion),
) -> dict[str, object]:
    resumen = resumir_proyeccion(
        listar_proyeccion(
            fuente,
            empresa_id=empresa_id,
        )
    )
    return {
        "registros": resumen.registros,
        "ocs": resumen.ocs,
        "clientes": resumen.clientes,
        "monto_esperado": _dinero_texto(resumen.monto_esperado),
        "valor_oc": _dinero_texto(resumen.valor_oc),
        "por_mes": [
            _agrupacion_como_dict(item)
            for item in resumen.por_mes
        ],
        "por_comercial": [
            _agrupacion_como_dict(item)
            for item in resumen.por_comercial
        ],
        "nota": (
            "Monto esperado y valor de OC se reportan por separado; "
            "no se suman entre sí."
        ),
    }


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
