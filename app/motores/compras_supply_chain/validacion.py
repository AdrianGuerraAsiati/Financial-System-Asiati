from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from .dominio import LineaCompra
from .kpis import decimal_desde_fuente
from .normalizacion import normalizar_etiqueta


_PAISES = {
    "CO": ("CO", "COLOMBIA"),
    "EC": ("EC", "ECUADOR"),
    "CL": ("CL", "CHILE"),
}


@dataclass(frozen=True)
class ReferenciaTablero:
    pais: str
    fila_encabezado: int
    estados_ddp: tuple[tuple[str, Decimal], ...]

    def como_dict(self) -> dict[str, object]:
        return {
            "pais": self.pais,
            "fila_encabezado": self.fila_encabezado,
            "estados_ddp": {
                estado: format(monto.quantize(Decimal("0.01")), "f")
                for estado, monto in self.estados_ddp
            },
        }


@dataclass(frozen=True)
class ComparacionEstado:
    pais: str
    estado: str
    detalle_ddp: Decimal | None
    tablero_ddp: Decimal | None
    diferencia: Decimal | None
    resultado: str

    def como_dict(self) -> dict[str, object]:
        def monto(valor: Decimal | None) -> str | None:
            return None if valor is None else format(
                valor.quantize(Decimal("0.01")),
                "f",
            )

        return {
            "pais": self.pais,
            "estado": self.estado,
            "detalle_ddp": monto(self.detalle_ddp),
            "tablero_ddp": monto(self.tablero_ddp),
            "diferencia": monto(self.diferencia),
            "resultado": self.resultado,
        }


def _pais_cercano(valores: list[list[Any]], fila: int) -> str | None:
    inicio = max(0, fila - 5)
    fin = min(len(valores), fila + 1)
    texto = " ".join(
        normalizar_etiqueta(celda)
        for row in valores[inicio:fin]
        for celda in row
        if str(celda or "").strip()
    )
    for pais, aliases in _PAISES.items():
        if any(alias in texto for alias in aliases):
            return pais
    return None


def extraer_referencias_supply_chain(
    valores: list[list[Any]],
) -> tuple[ReferenciaTablero, ...]:
    referencias: list[ReferenciaTablero] = []

    for indice_fila, fila in enumerate(valores):
        normalizados = [normalizar_etiqueta(celda) for celda in fila]
        try:
            columna_estado = normalizados.index("ESTADO")
        except ValueError:
            continue

        columna_valor = None
        for indice_columna, encabezado in enumerate(normalizados):
            if "VALOR OCI" in encabezado and "DDP" in encabezado:
                columna_valor = indice_columna
                break
        if columna_valor is None:
            continue

        pais = _pais_cercano(valores, indice_fila)
        if pais is None:
            # Sin país no se compara para evitar afirmar que un pivote parcial
            # representa CO+EC+CL.
            continue

        estados: list[tuple[str, Decimal]] = []
        for fila_datos in valores[indice_fila + 1 :]:
            estado_crudo = (
                fila_datos[columna_estado]
                if columna_estado < len(fila_datos)
                else ""
            )
            valor_crudo = (
                fila_datos[columna_valor]
                if columna_valor < len(fila_datos)
                else ""
            )
            estado = normalizar_etiqueta(estado_crudo)

            if not estado:
                if estados:
                    break
                continue
            if estado in {"TOTAL GENERAL", "TOTAL"}:
                break
            if estado == "ESTADO":
                break

            try:
                monto = decimal_desde_fuente(str(valor_crudo or ""))
            except InvalidOperation:
                if estados:
                    break
                continue
            if monto is None:
                continue
            estados.append((estado, monto))

        if estados:
            referencias.append(
                ReferenciaTablero(
                    pais=pais,
                    fila_encabezado=indice_fila + 1,
                    estados_ddp=tuple(estados),
                )
            )

    # Si el Sheet repite un pivote para el mismo país, conservar el primero y
    # exponer determinísticamente una sola referencia por país.
    unicas: dict[str, ReferenciaTablero] = {}
    for referencia in referencias:
        unicas.setdefault(referencia.pais, referencia)
    return tuple(unicas[pais] for pais in sorted(unicas))


def _ddp_detalle_por_estado(
    lineas: Iterable[LineaCompra],
    *,
    pais: str,
) -> dict[str, Decimal]:
    resultado: dict[str, Decimal] = {}
    for linea in lineas:
        if linea.pais != pais or not linea.estado_normalizado:
            continue
        try:
            monto = decimal_desde_fuente(linea.valor_oci_ddp_origen)
        except InvalidOperation:
            continue
        if monto is None:
            continue
        resultado[linea.estado_normalizado] = (
            resultado.get(linea.estado_normalizado, Decimal("0")) + monto
        )
    return resultado


def comparar_con_supply_chain(
    lineas: Iterable[LineaCompra],
    referencias: Iterable[ReferenciaTablero],
) -> tuple[ComparacionEstado, ...]:
    comparaciones: list[ComparacionEstado] = []

    for referencia in referencias:
        detalle = _ddp_detalle_por_estado(lineas, pais=referencia.pais)
        tablero = dict(referencia.estados_ddp)
        estados = sorted(set(detalle) | set(tablero))

        for estado in estados:
            monto_detalle = detalle.get(estado)
            monto_tablero = tablero.get(estado)
            if monto_detalle is None:
                resultado = "SOLO_TABLERO"
                diferencia = None
            elif monto_tablero is None:
                resultado = "SOLO_DETALLE"
                diferencia = None
            else:
                diferencia = monto_detalle - monto_tablero
                resultado = (
                    "COINCIDE"
                    if diferencia.quantize(Decimal("0.01")) == Decimal("0.00")
                    else "DIFERENCIA"
                )
            comparaciones.append(
                ComparacionEstado(
                    pais=referencia.pais,
                    estado=estado,
                    detalle_ddp=monto_detalle,
                    tablero_ddp=monto_tablero,
                    diferencia=diferencia,
                    resultado=resultado,
                )
            )

    return tuple(comparaciones)


def resumen_validacion(
    comparaciones: Iterable[ComparacionEstado],
) -> dict[str, object]:
    comparaciones_lista = tuple(comparaciones)
    conteos: dict[str, int] = {}
    for item in comparaciones_lista:
        conteos[item.resultado] = conteos.get(item.resultado, 0) + 1
    return {
        "comparaciones": len(comparaciones_lista),
        "resultados": dict(sorted(conteos.items())),
        "todo_coincide": bool(comparaciones_lista)
        and all(item.resultado == "COINCIDE" for item in comparaciones_lista),
    }
