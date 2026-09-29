from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class LineaCompra:
    pais: str
    hoja_fuente: str
    fila_fuente: int

    numero_oc: str
    oc_identificada: bool
    cliente: str
    sku: str
    descripcion: str
    proveedor: str

    estado_origen: str
    estado_normalizado: str
    etapa_logistica: str
    situacion_operativa: str

    modo_transporte_origen: str
    modo_transporte_normalizado: str

    documento_transporte: str
    etd: str
    eta: str
    fecha_entrega_bodega_destino: str

    valor_total_compra_usd_origen: str
    valor_oci_ddp_origen: str

    cantidad: str = ""
    unidad_comercial: str = ""
    unidad_comercial_nombre: str = ""
    id_cotizacion: str = ""
    numero_factura_proveedor: str = ""
    incoterm: str = ""
    costo_unitario_usd_origen: str = ""
    tipo_negociacion: str = ""
    fecha_abono_compra: str = ""
    fecha_pago_total_compra: str = ""
    production_time_dias_estimado: str = ""
    ctn: str = ""
    peso_vol_origen: str = ""
    largo_cm_origen: str = ""
    ancho_cm_origen: str = ""
    alto_cm_origen: str = ""
    cbm_origen: str = ""
    peso_total_kg_origen: str = ""
    fecha_entrega_proveedor_estimada: str = ""
    fecha_fin_produccion: str = ""
    fecha_ingreso_bodega_origen: str = ""
    dias_produccion_real_origen: str = ""
    dias_hasta_bodega_origen_origen: str = ""
    certificado_origen: str = ""
    fecha_cargue: str = ""
    telex_bl: str = ""
    nacionalizacion: str = ""
    factura_destino: str = ""
    comercial_asignado: str = ""
    fecha_en_valor: str = ""
    semana_entrega_proveedor: str = ""
    mes_origen: str = ""
    anio_origen: str = ""
    fecha_solicitud_pago_abono: str = ""
    motivo_demora_abono: str = ""
    elaboro_oc: str = ""

    def como_dict(self) -> dict[str, object]:
        return asdict(self)
