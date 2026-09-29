from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable

from .contrato import DiagnosticoEsquema
from .dominio import LineaCompra


ESTADOS_ACTIVOS_TABLERO_ACTUAL: tuple[str, ...] = (
    "EN BODEGA ASIATI SHENZHEN",
    "EN BODEGA ASIATI YIWU",
    "EN NACIONALIZACION",
    "EN OTM",
    "EN PRODUCCION",
    "ENVIADO A DESTINO",
    "PENDIENTE DEPOSITO",
)
_ESTADOS_ACTIVOS = frozenset(ESTADOS_ACTIVOS_TABLERO_ACTUAL)


@dataclass(frozen=True)
class FamiliaMonetaria:
    codigo: str
    nombre: str
    campo_canonico: str
    atributo_linea: str
    pregunta: str


FAMILIAS_MONETARIAS: tuple[FamiliaMonetaria, ...] = (
    FamiliaMonetaria(
        codigo="costo_compra",
        nombre="Costo de compra",
        campo_canonico="valor_total_compra_usd",
        atributo_linea="valor_total_compra_usd_origen",
        pregunta="¿Cuál es el costo de compra USD asociado a la mercancía?",
    ),
    FamiliaMonetaria(
        codigo="valor_comercial_ddp",
        nombre="Valor comercial DDP",
        campo_canonico="valor_oci_ddp",
        atributo_linea="valor_oci_ddp_origen",
        pregunta="¿Cuál es el valor comercial OCI/DDP USD asociado a la mercancía?",
    ),
)


@dataclass(frozen=True)
class AcumuladoMonetario:
    lineas: int
    lineas_con_valor: int
    lineas_sin_valor: int
    lineas_valor_invalido: int
    monto: Decimal

    def como_dict(self) -> dict[str, object]:
        return {
            "lineas": self.lineas,
            "lineas_con_valor": self.lineas_con_valor,
            "lineas_sin_valor": self.lineas_sin_valor,
            "lineas_valor_invalido": self.lineas_valor_invalido,
            "monto_usd": _monto_texto(self.monto),
        }


@dataclass(frozen=True)
class ResultadoFamiliaMonetaria:
    familia: FamiliaMonetaria
    disponible: bool
    hojas_sin_campo: tuple[str, ...]
    activo: AcumuladoMonetario | None
    general: AcumuladoMonetario | None
    por_estado: tuple[tuple[str, bool, AcumuladoMonetario], ...]
    por_pais_activo: tuple[tuple[str, AcumuladoMonetario], ...]

    def como_dict(self) -> dict[str, object]:
        return {
            "codigo": self.familia.codigo,
            "nombre": self.familia.nombre,
            "campo_fuente": self.familia.campo_canonico,
            "moneda": "USD",
            "pregunta": self.familia.pregunta,
            "disponible": self.disponible,
            "hojas_sin_campo": list(self.hojas_sin_campo),
            "activo": self.activo.como_dict() if self.activo else None,
            "general": self.general.como_dict() if self.general else None,
            "por_estado": [
                {
                    "estado": estado,
                    "incluido_en_supply_chain_actual": activo,
                    **acumulado.como_dict(),
                }
                for estado, activo, acumulado in self.por_estado
            ],
            "por_pais_activo": {
                pais: acumulado.como_dict()
                for pais, acumulado in self.por_pais_activo
            },
        }


def _monto_texto(valor: Decimal) -> str:
    return format(valor.quantize(Decimal("0.01")), "f")


def decimal_desde_fuente(valor: str) -> Decimal | None:
    texto = str(valor or "").strip()
    if not texto:
        return None

    negativo_parentesis = texto.startswith("(") and texto.endswith(")")
    texto = texto.replace("\u00a0", "").replace(" ", "")
    texto = re.sub(r"(?i)USD|US\$", "", texto)
    texto = texto.replace("$", "")
    texto = texto.strip("()")
    texto = re.sub(r"[^0-9,\.\-]", "", texto)

    if not texto or texto in {"-", ".", ","}:
        raise InvalidOperation

    coma = texto.rfind(",")
    punto = texto.rfind(".")

    if coma >= 0 and punto >= 0:
        separador_decimal = "," if coma > punto else "."
        separador_miles = "." if separador_decimal == "," else ","
        texto = texto.replace(separador_miles, "")
        if separador_decimal == ",":
            texto = texto.replace(",", ".")
    elif coma >= 0:
        texto = _normalizar_separador_unico(texto, ",")
    elif punto >= 0:
        texto = _normalizar_separador_unico(texto, ".")

    if negativo_parentesis and not texto.startswith("-"):
        texto = "-" + texto

    return Decimal(texto)


def _normalizar_separador_unico(texto: str, separador: str) -> str:
    partes = texto.split(separador)
    if len(partes) == 2:
        enteros, decimales = partes
        if len(decimales) in {1, 2}:
            return enteros + "." + decimales
        if len(decimales) == 3:
            return enteros + decimales
        return enteros + "." + decimales

    ultimo = partes[-1]
    if len(ultimo) in {1, 2}:
        return "".join(partes[:-1]) + "." + ultimo
    return "".join(partes)


def _acumular(
    lineas: Iterable[LineaCompra],
    *,
    atributo: str,
) -> AcumuladoMonetario:
    total = Decimal("0")
    cantidad = 0
    con_valor = 0
    sin_valor = 0
    invalidos = 0

    for linea in lineas:
        cantidad += 1
        valor_origen = getattr(linea, atributo)
        if not str(valor_origen or "").strip():
            sin_valor += 1
            continue
        try:
            monto = decimal_desde_fuente(valor_origen)
        except InvalidOperation:
            invalidos += 1
            continue
        if monto is None:
            sin_valor += 1
            continue
        total += monto
        con_valor += 1

    return AcumuladoMonetario(
        lineas=cantidad,
        lineas_con_valor=con_valor,
        lineas_sin_valor=sin_valor,
        lineas_valor_invalido=invalidos,
        monto=total,
    )


def _hojas_sin_campo(
    diagnosticos: Iterable[DiagnosticoEsquema],
    *,
    campo_canonico: str,
    pais: str | None,
) -> tuple[str, ...]:
    faltantes: list[str] = []
    for diagnostico in diagnosticos:
        if pais and diagnostico.pais != pais:
            continue
        if campo_canonico not in diagnostico.campos_reconocidos:
            faltantes.append(diagnostico.pais)
    return tuple(sorted(faltantes))


def calcular_familias_monetarias(
    lineas: Iterable[LineaCompra],
    diagnosticos: Iterable[DiagnosticoEsquema],
    *,
    pais: str | None = None,
) -> tuple[ResultadoFamiliaMonetaria, ...]:
    lineas_filtradas = tuple(
        linea for linea in lineas if pais is None or linea.pais == pais
    )
    estados_observados = tuple(
        sorted(
            {
                linea.estado_normalizado or "(VACIO)"
                for linea in lineas_filtradas
            }
        )
    )

    resultados: list[ResultadoFamiliaMonetaria] = []
    for familia in FAMILIAS_MONETARIAS:
        hojas_sin_campo = _hojas_sin_campo(
            diagnosticos,
            campo_canonico=familia.campo_canonico,
            pais=pais,
        )
        disponible = not hojas_sin_campo

        if not disponible:
            resultados.append(
                ResultadoFamiliaMonetaria(
                    familia=familia,
                    disponible=False,
                    hojas_sin_campo=hojas_sin_campo,
                    activo=None,
                    general=None,
                    por_estado=(),
                    por_pais_activo=(),
                )
            )
            continue

        activas = tuple(
            linea
            for linea in lineas_filtradas
            if linea.estado_normalizado in _ESTADOS_ACTIVOS
        )
        por_estado = tuple(
            (
                estado,
                estado in _ESTADOS_ACTIVOS,
                _acumular(
                    (
                        linea
                        for linea in lineas_filtradas
                        if (linea.estado_normalizado or "(VACIO)") == estado
                    ),
                    atributo=familia.atributo_linea,
                ),
            )
            for estado in estados_observados
        )

        paises = tuple(sorted({linea.pais for linea in activas}))
        por_pais = tuple(
            (
                codigo_pais,
                _acumular(
                    (linea for linea in activas if linea.pais == codigo_pais),
                    atributo=familia.atributo_linea,
                ),
            )
            for codigo_pais in paises
        )

        resultados.append(
            ResultadoFamiliaMonetaria(
                familia=familia,
                disponible=True,
                hojas_sin_campo=(),
                activo=_acumular(activas, atributo=familia.atributo_linea),
                general=_acumular(
                    lineas_filtradas,
                    atributo=familia.atributo_linea,
                ),
                por_estado=por_estado,
                por_pais_activo=por_pais,
            )
        )

    return tuple(resultados)


def resumen_poblacion_activa(
    lineas: Iterable[LineaCompra],
    *,
    pais: str | None = None,
) -> dict[str, object]:
    filtradas = tuple(
        linea for linea in lineas if pais is None or linea.pais == pais
    )
    activas = tuple(
        linea
        for linea in filtradas
        if linea.estado_normalizado in _ESTADOS_ACTIVOS
    )
    return {
        "criterio": "estados_del_pivote_supply_chain_actual",
        "estados_incluidos": list(ESTADOS_ACTIVOS_TABLERO_ACTUAL),
        "lineas_activas": len(activas),
        "lineas_activas_por_estado": dict(
            sorted(Counter(linea.estado_normalizado for linea in activas).items())
        ),
        "nota": (
            "Esta población reproduce la selección observada en el tablero actual. "
            "No redefine EN OTM ni PENDIENTE DEPOSITO como una etapa logística."
        ),
    }
