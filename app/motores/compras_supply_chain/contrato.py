from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from .normalizacion import normalizar_encabezado


@dataclass(frozen=True)
class CampoContrato:
    canonico: str
    aliases: tuple[str, ...]
    critico: bool = False
    define_fila: bool = True


CAMPOS: tuple[CampoContrato, ...] = (
    CampoContrato("numero_oc", ("NUMERO OC",), critico=True),
    CampoContrato("cliente", ("CLIENTE",), critico=True),
    CampoContrato("sku", ("SKU",), critico=False),
    CampoContrato("descripcion", ("DESCRIPCION", "DESCRIPCIÓN"), critico=False),
    CampoContrato("proveedor", ("PROVEEDOR",), critico=True),
    CampoContrato("estado", ("ESTADO", "ESTADO "), critico=True),
    CampoContrato("modo_transporte", ("MODO TRANSPORTE",), critico=True),
    CampoContrato(
        "documento_transporte",
        ("DOCUMENTO DE TRANSPORTE", "DOC TRANSPORTE"),
        critico=False,
    ),
    CampoContrato("etd", ("ETD",), critico=False),
    CampoContrato("eta", ("ETA", " ETA"), critico=False),
    CampoContrato(
        "fecha_entrega_bodega_destino",
        (
            "FECHA ENTREGA EN BODEGA BOGOTA",
            "FECHA ENTREGA EN BODEGA BOGOTÁ",
            "FECHA ENTREGA EN BODEGA QUITO",
            "FECHA ENTREGA EN BODEGA SANTIAGO",
            "FECHA ENTREGA A BODEGA EN BOG",
            "FECHA ENTREGA A BODEGA EN QUITO",
            "FECHA ENTREGA A BODEGA EN SANTIAGO",
            "FECHA ENTREGA BODEGA DESTINO",
        ),
        critico=False,
    ),
    CampoContrato(
        "valor_total_compra_usd",
        ("VALOR TOTAL COMPRA USD",),
        critico=False,
    ),
    CampoContrato("valor_oci_ddp", ("VALOR OCI (DDP)",), critico=False),
    CampoContrato("cantidad", ("QTY",), define_fila=True),
    CampoContrato("unidad_comercial", ("UNIDAD COMERCIAL",), define_fila=True),
    CampoContrato(
        "unidad_comercial_nombre",
        ("NOMBRE UNIDAD COMERCIAL (auto)",),
        define_fila=False,
    ),
    CampoContrato(
        "id_cotizacion",
        ("SOLICITUD COTIZACION ID COTIZACION",),
        define_fila=True,
    ),
    CampoContrato(
        "numero_factura_proveedor",
        ("NUMERO DE FACTURA",),
        define_fila=True,
    ),
    CampoContrato("incoterm", ("INCOTERMS",), define_fila=True),
    CampoContrato(
        "costo_unitario_usd",
        ("COSTO COMPRA CHINA/VENTA A LATAM USD",),
        define_fila=True,
    ),
    CampoContrato(
        "tipo_negociacion",
        ("TIPO DE NEGOCIACION",),
        define_fila=True,
    ),
    CampoContrato(
        "fecha_abono_compra",
        ("FECHA DE COMPRA EN CHINA (ABONO)",),
        define_fila=True,
    ),
    CampoContrato(
        "fecha_pago_total_compra",
        ("FECHA PAGO TOTAL EN CHINA",),
        define_fila=True,
    ),
    CampoContrato(
        "production_time_dias_estimado",
        ("PRODUCTION TIME DAYS (ESTIMADO)",),
        define_fila=True,
    ),
    CampoContrato("ctn", ("CTN",), define_fila=True),
    CampoContrato("peso_vol", ("PESO VOL (auto)",), define_fila=False),
    CampoContrato("largo_cm", ("LARGO (cm)", " LARGO (cm)"), define_fila=True),
    CampoContrato("ancho_cm", ("ANCHO (cm)",), define_fila=True),
    CampoContrato("alto_cm", ("ALTO (cm)",), define_fila=True),
    CampoContrato("peso_total_kg", ("PESO TOTAL (Kg)",), define_fila=True),
    CampoContrato(
        "fecha_entrega_proveedor_estimada",
        ("FECHA ENTREGA PROV. ESTIMADA (auto)",),
        define_fila=False,
    ),
    CampoContrato(
        "fecha_fin_produccion",
        ("FECHA FINALIZACIÓN DE PRODUCCIÓN",),
        define_fila=True,
    ),
    CampoContrato(
        "fecha_ingreso_bodega_origen",
        ("FECHA INGRESO A BODEGA EN ORIGEN",),
        define_fila=True,
    ),
    CampoContrato(
        "dias_produccion_real",
        ("DÍAS DE PRODUCCIÓN REAL (auto)",),
        define_fila=False,
    ),
    CampoContrato(
        "dias_hasta_bodega_origen",
        ("DÍAS HASTA BODEGA ORIGEN DESDE FINALIZACIÓN DE PROD (auto)",),
        define_fila=False,
    ),
    CampoContrato(
        "certificado_origen",
        ("CERTIFICADO DE ORIGEN",),
        define_fila=True,
    ),
    CampoContrato("fecha_cargue", ("FECHA CARGUE",), define_fila=True),
    CampoContrato(
        "telex_bl",
        ("Telex/BL", "Telex/BL (auto)"),
        define_fila=False,
    ),
    CampoContrato("nacionalizacion", ("NACIONALIZACION",), define_fila=True),
    CampoContrato("factura_destino", ("FACTURA",), define_fila=True),
    CampoContrato(
        "comercial_asignado",
        ("COMERCIAL ASIGNADO",),
        define_fila=True,
    ),
    CampoContrato("fecha_en_valor", ("FECHA EN VALOR",), define_fila=False),
    CampoContrato(
        "semana_entrega_proveedor",
        ("SEMANA ENTREGA PROV",),
        define_fila=False,
    ),
    CampoContrato("mes", ("MES",), define_fila=False),
    CampoContrato("anio", ("AÑO",), define_fila=False),
    CampoContrato(
        "fecha_solicitud_pago_abono",
        ("FECHA SOLICITUD PAGO (abono)",),
        define_fila=True,
    ),
    CampoContrato(
        "motivo_demora_abono",
        ("MOTIVO DEMORA ABONO",),
        define_fila=True,
    ),
    CampoContrato("elaboro_oc", ("ELABORO OC",), define_fila=True),
)


_ALIAS_A_CAMPO = {
    normalizar_encabezado(alias): campo.canonico
    for campo in CAMPOS
    for alias in campo.aliases
}


@dataclass(frozen=True)
class DiagnosticoEsquema:
    pais: str
    rango: str
    encabezados: tuple[str, ...]
    filas_datos: int
    campos_reconocidos: tuple[str, ...]
    campos_criticos_faltantes: tuple[str, ...]
    campos_esperados_faltantes: tuple[str, ...]
    encabezados_duplicados: tuple[str, ...]
    encabezados_no_consumidos: tuple[str, ...]

    @property
    def valido(self) -> bool:
        return not self.campos_criticos_faltantes and not self.encabezados_duplicados

    def como_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["valido"] = self.valido
        return data


def es_encabezado_consumido(encabezado: Any) -> bool:
    return normalizar_encabezado(encabezado) in _ALIAS_A_CAMPO


_ENCABEZADOS_QUE_DEFINEN_FILA = {
    normalizar_encabezado(alias)
    for campo in CAMPOS
    if campo.define_fila
    for alias in campo.aliases
}


def es_encabezado_sustantivo(encabezado: Any) -> bool:
    return normalizar_encabezado(encabezado) in _ENCABEZADOS_QUE_DEFINEN_FILA


def analizar_encabezados(
    encabezados: Iterable[Any],
    *,
    pais: str,
    rango: str,
    filas_datos: int,
) -> DiagnosticoEsquema:
    originales = tuple(str(valor or "").strip() for valor in encabezados)
    normalizados = [normalizar_encabezado(valor) for valor in originales]

    conteos: dict[str, int] = {}
    for encabezado in normalizados:
        if not encabezado:
            continue
        conteos[encabezado] = conteos.get(encabezado, 0) + 1

    duplicados = tuple(
        sorted(
            encabezado
            for encabezado, cantidad in conteos.items()
            if cantidad > 1 and encabezado in _ALIAS_A_CAMPO
        )
    )

    reconocidos = {
        _ALIAS_A_CAMPO[encabezado]
        for encabezado in normalizados
        if encabezado in _ALIAS_A_CAMPO
    }

    criticos = {campo.canonico for campo in CAMPOS if campo.critico}
    esperados = {campo.canonico for campo in CAMPOS}

    faltantes_criticos = tuple(sorted(criticos - reconocidos))
    faltantes_esperados = tuple(sorted((esperados - reconocidos) - criticos))

    no_consumidos = tuple(
        original
        for original, normalizado in zip(originales, normalizados, strict=True)
        if normalizado and normalizado not in _ALIAS_A_CAMPO
    )

    return DiagnosticoEsquema(
        pais=pais,
        rango=rango,
        encabezados=originales,
        filas_datos=filas_datos,
        campos_reconocidos=tuple(sorted(reconocidos)),
        campos_criticos_faltantes=faltantes_criticos,
        campos_esperados_faltantes=faltantes_esperados,
        encabezados_duplicados=duplicados,
        encabezados_no_consumidos=no_consumidos,
    )
