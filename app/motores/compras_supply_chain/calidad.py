from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from .dominio import LineaCompra


MODOS_CONOCIDOS = {"MARITIMO", "AEREO", "CASILLERO", "MUESTRA"}


@dataclass(frozen=True)
class MuestraCalidad:
    pais: str
    hoja_fuente: str
    fila_fuente: int
    numero_oc: str

    def como_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ResultadoReglaCalidad:
    codigo: str
    categoria: str
    descripcion: str
    cantidad: int
    muestras: tuple[MuestraCalidad, ...]

    def como_dict(self) -> dict[str, object]:
        return {
            "codigo": self.codigo,
            "categoria": self.categoria,
            "descripcion": self.descripcion,
            "cantidad": self.cantidad,
            "muestras": [m.como_dict() for m in self.muestras],
        }


def _muestra(linea: LineaCompra) -> MuestraCalidad:
    return MuestraCalidad(
        pais=linea.pais,
        hoja_fuente=linea.hoja_fuente,
        fila_fuente=linea.fila_fuente,
        numero_oc=linea.numero_oc,
    )


def _resultado(
    *,
    codigo: str,
    categoria: str,
    descripcion: str,
    lineas: Iterable[LineaCompra],
    max_muestras: int,
) -> ResultadoReglaCalidad:
    lineas_lista = list(lineas)
    return ResultadoReglaCalidad(
        codigo=codigo,
        categoria=categoria,
        descripcion=descripcion,
        cantidad=len(lineas_lista),
        muestras=tuple(_muestra(linea) for linea in lineas_lista[:max_muestras]),
    )


def evaluar_calidad_lineas(
    lineas: Iterable[LineaCompra],
    *,
    max_muestras: int = 5,
) -> tuple[ResultadoReglaCalidad, ...]:
    lineas_lista = tuple(lineas)

    reglas = (
        _resultado(
            codigo="OC_NO_IDENTIFICADA",
            categoria="DATO_FALTANTE",
            descripcion="Línea sin número de OC identificable.",
            lineas=(linea for linea in lineas_lista if not linea.oc_identificada),
            max_muestras=max_muestras,
        ),
        _resultado(
            codigo="CLIENTE_VACIO",
            categoria="DATO_FALTANTE",
            descripcion="Línea sin cliente.",
            lineas=(linea for linea in lineas_lista if not linea.cliente.strip()),
            max_muestras=max_muestras,
        ),
        _resultado(
            codigo="PROVEEDOR_VACIO",
            categoria="DATO_FALTANTE",
            descripcion="Línea sin proveedor.",
            lineas=(linea for linea in lineas_lista if not linea.proveedor.strip()),
            max_muestras=max_muestras,
        ),
        _resultado(
            codigo="ESTADO_VACIO",
            categoria="DATO_FALTANTE",
            descripcion="Línea sin estado de origen.",
            lineas=(linea for linea in lineas_lista if not linea.estado_normalizado),
            max_muestras=max_muestras,
        ),
        _resultado(
            codigo="ESTADO_POR_DEFINIR",
            categoria="REQUIERE_CRITERIO",
            descripcion=(
                "Estado presente pero todavía sin clasificación logística aprobada."
            ),
            lineas=(
                linea
                for linea in lineas_lista
                if linea.estado_normalizado
                and linea.etapa_logistica == "POR_DEFINIR"
            ),
            max_muestras=max_muestras,
        ),
        _resultado(
            codigo="TRANSPORTE_VACIO",
            categoria="DATO_FALTANTE",
            descripcion="Línea sin modo de transporte.",
            lineas=(
                linea
                for linea in lineas_lista
                if not linea.modo_transporte_normalizado
            ),
            max_muestras=max_muestras,
        ),
        _resultado(
            codigo="TRANSPORTE_NO_CATALOGADO",
            categoria="VALOR_NO_RECONOCIDO",
            descripcion="Modo de transporte fuera del catálogo conocido.",
            lineas=(
                linea
                for linea in lineas_lista
                if linea.modo_transporte_normalizado
                and linea.modo_transporte_normalizado not in MODOS_CONOCIDOS
            ),
            max_muestras=max_muestras,
        ),
        _resultado(
            codigo="ENTREGA_CON_ESTADO_NO_RECIBIDO",
            categoria="CONSISTENCIA",
            descripcion=(
                "La línea tiene fecha de entrega a bodega, pero su etapa no es RECIBIDO. "
                "La plataforma solo informa; no corrige la fuente."
            ),
            lineas=(
                linea
                for linea in lineas_lista
                if linea.fecha_entrega_bodega_destino.strip()
                and linea.etapa_logistica not in {"RECIBIDO", "SIN_ETAPA"}
            ),
            max_muestras=max_muestras,
        ),
    )

    return tuple(regla for regla in reglas if regla.cantidad > 0)
