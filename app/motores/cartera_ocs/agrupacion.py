from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from app.motores.cartera_ocs.importacion import RegistroCarteraEnCamino


@dataclass(frozen=True)
class OperacionAgrupadaCartera:
    oc: str
    lineas: tuple[RegistroCarteraEnCamino, ...]
    clientes: tuple[str, ...]
    negociaciones: tuple[str, ...]
    estados: tuple[str, ...]
    etapas: tuple[str, ...]
    modos_transporte: tuple[str, ...]
    documentos_transporte: tuple[str, ...]
    skus: tuple[str, ...]
    valor_ddp: Decimal
    valor_anticipo: Decimal
    valor_financiado: Decimal

    @property
    def tiene_multiples_clientes(self) -> bool:
        return len(self.clientes) > 1

    @property
    def tiene_multiples_negociaciones(self) -> bool:
        return len(self.negociaciones) > 1

    @property
    def tiene_multiples_estados(self) -> bool:
        return len(self.estados) > 1

    @property
    def tiene_multiples_etapas(self) -> bool:
        return len(self.etapas) > 1


def _valores_unicos_en_orden(valores: Iterable[str]) -> tuple[str, ...]:
    vistos: set[str] = set()
    resultado: list[str] = []

    for valor in valores:
        texto = str(valor or "").strip()
        if not texto or texto in vistos:
            continue
        vistos.add(texto)
        resultado.append(texto)

    return tuple(resultado)


def _construir_grupo(
    oc: str,
    lineas: list[RegistroCarteraEnCamino],
) -> OperacionAgrupadaCartera:
    items = tuple(lineas)
    return OperacionAgrupadaCartera(
        oc=oc,
        lineas=items,
        clientes=_valores_unicos_en_orden(item.cliente for item in items),
        negociaciones=_valores_unicos_en_orden(
            item.negociacion for item in items
        ),
        estados=_valores_unicos_en_orden(item.estado for item in items),
        etapas=_valores_unicos_en_orden(item.etapa for item in items),
        modos_transporte=_valores_unicos_en_orden(
            item.modo_transporte for item in items
        ),
        documentos_transporte=_valores_unicos_en_orden(
            item.documento_transporte for item in items
        ),
        skus=_valores_unicos_en_orden(item.sku for item in items),
        valor_ddp=sum(
            (item.valor for item in items),
            start=Decimal("0"),
        ),
        valor_anticipo=sum(
            (item.valor_anticipo for item in items),
            start=Decimal("0"),
        ),
        valor_financiado=sum(
            (item.valor_financiado for item in items),
            start=Decimal("0"),
        ),
    )


def agrupar_operaciones_por_oc(
    registros: Iterable[RegistroCarteraEnCamino],
) -> tuple[OperacionAgrupadaCartera, ...]:
    """Agrupa líneas por OC sin inventar una categoría única para la operación.

    Las filas sin número de OC se excluyen del agrupamiento; permanecen visibles
    en la fuente y en las validaciones de calidad.
    """

    por_oc: dict[str, list[RegistroCarteraEnCamino]] = {}

    for registro in registros:
        oc = str(registro.oc or "").strip()
        if not oc:
            continue
        por_oc.setdefault(oc, []).append(registro)

    return tuple(
        _construir_grupo(oc, por_oc[oc])
        for oc in sorted(por_oc)
    )
