from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from .dominio import LineaCompra


@dataclass(frozen=True)
class ResumenOC:
    clave: str
    pais: str
    numero_oc: str
    oc_identificada: bool
    lineas: int
    proveedores: tuple[str, ...]
    estados: tuple[str, ...]
    etapas_logisticas: tuple[str, ...]
    modos_transporte: tuple[str, ...]
    estado_mixto: bool
    proveedor_mixto: bool
    transporte_mixto: bool

    def como_dict(self) -> dict[str, object]:
        return asdict(self)


def _valores_no_vacios(valores: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({valor for valor in valores if valor.strip()}))


def agrupar_ocs(lineas: Iterable[LineaCompra]) -> tuple[ResumenOC, ...]:
    grupos: dict[str, list[LineaCompra]] = {}

    for linea in lineas:
        if linea.oc_identificada:
            clave = f"{linea.pais}:{linea.numero_oc.strip()}"
        else:
            # No unir todas las filas N/A/vacías como si fueran una sola OC.
            clave = f"{linea.pais}:SIN_OC:{linea.hoja_fuente}:{linea.fila_fuente}"
        grupos.setdefault(clave, []).append(linea)

    resultado: list[ResumenOC] = []
    for clave, grupo in grupos.items():
        primera = grupo[0]
        proveedores = _valores_no_vacios(linea.proveedor for linea in grupo)
        estados = _valores_no_vacios(linea.estado_normalizado for linea in grupo)
        etapas = _valores_no_vacios(linea.etapa_logistica for linea in grupo)
        modos = _valores_no_vacios(
            linea.modo_transporte_normalizado for linea in grupo
        )

        resultado.append(
            ResumenOC(
                clave=clave,
                pais=primera.pais,
                numero_oc=primera.numero_oc,
                oc_identificada=primera.oc_identificada,
                lineas=len(grupo),
                proveedores=proveedores,
                estados=estados,
                etapas_logisticas=etapas,
                modos_transporte=modos,
                estado_mixto=len(estados) > 1,
                proveedor_mixto=len(proveedores) > 1,
                transporte_mixto=len(modos) > 1,
            )
        )

    return tuple(
        sorted(
            resultado,
            key=lambda item: (
                item.pais,
                not item.oc_identificada,
                item.numero_oc,
                item.clave,
            ),
        )
    )
