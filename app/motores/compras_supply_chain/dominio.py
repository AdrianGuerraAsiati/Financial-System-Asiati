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

    def como_dict(self) -> dict[str, object]:
        return asdict(self)
