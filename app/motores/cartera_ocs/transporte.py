from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable

from app.motores.cartera_ocs.fechas import parsear_fecha_cartera
from app.motores.cartera_ocs.importacion import RegistroCarteraEnCamino


ESTADO_VENCIDO = "VENCIDO"
ESTADO_EN_CAMINO = "EN_CAMINO"
ESTADO_SIN_ETA = "SIN_ETA"
ESTADO_SIN_DOCUMENTO = "SIN_DOCUMENTO"


@dataclass(frozen=True)
class DocumentoTransporteCartera:
    documento: str
    lineas: int
    ocs: tuple[str, ...]
    clientes: tuple[str, ...]
    modos_transporte: tuple[str, ...]
    valor_ddp: Decimal
    valor_anticipo: Decimal
    valor_financiado: Decimal
    eta_min: date | None
    eta_max: date | None
    estado: str


def _unicos_en_orden(valores: Iterable[str]) -> tuple[str, ...]:
    vistos: set[str] = set()
    salida: list[str] = []
    for valor in valores:
        texto = str(valor or "").strip()
        if not texto or texto in vistos:
            continue
        vistos.add(texto)
        salida.append(texto)
    return tuple(salida)


def _estado_documento(
    *,
    documento: str,
    eta_min: date | None,
    fecha_corte: date,
) -> str:
    if not documento:
        return ESTADO_SIN_DOCUMENTO
    if eta_min is None:
        return ESTADO_SIN_ETA
    if eta_min < fecha_corte:
        return ESTADO_VENCIDO
    return ESTADO_EN_CAMINO


def agrupar_documentos_transporte(
    registros: Iterable[RegistroCarteraEnCamino],
    *,
    fecha_corte: date | None = None,
) -> tuple[DocumentoTransporteCartera, ...]:
    """Porta la agrupación por guía/BL del tablero legado de Johan.

    El grupo sin documento es deliberado: el tablero anterior lo usaba para
    líneas aún sin guía asignada. Un documento se considera vencido cuando su
    ETA mínima es anterior a la fecha de corte; esta función no infiere llegada
    real a bodega porque la regla legada tampoco lo hacía.
    """
    corte = fecha_corte or date.today()
    grupos: dict[str, list[RegistroCarteraEnCamino]] = {}

    for registro in registros:
        documento = str(registro.documento_transporte or "").strip()
        grupos.setdefault(documento, []).append(registro)

    salida: list[DocumentoTransporteCartera] = []
    for documento, lineas in grupos.items():
        etas = tuple(
            fecha
            for item in lineas
            if (fecha := parsear_fecha_cartera(item.eta)) is not None
        )
        eta_min = min(etas) if etas else None
        eta_max = max(etas) if etas else None
        salida.append(
            DocumentoTransporteCartera(
                documento=documento,
                lineas=len(lineas),
                ocs=_unicos_en_orden(item.oc for item in lineas),
                clientes=_unicos_en_orden(item.cliente for item in lineas),
                modos_transporte=_unicos_en_orden(
                    item.modo_transporte for item in lineas
                ),
                valor_ddp=sum(
                    (item.valor for item in lineas),
                    start=Decimal("0"),
                ),
                valor_anticipo=sum(
                    (item.valor_anticipo for item in lineas),
                    start=Decimal("0"),
                ),
                valor_financiado=sum(
                    (item.valor_financiado for item in lineas),
                    start=Decimal("0"),
                ),
                eta_min=eta_min,
                eta_max=eta_max,
                estado=_estado_documento(
                    documento=documento,
                    eta_min=eta_min,
                    fecha_corte=corte,
                ),
            )
        )

    return tuple(salida)
