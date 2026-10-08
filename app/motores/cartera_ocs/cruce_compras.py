"""Cruce descriptivo de líneas de Cartera y Compras, sin efectos financieros.

El resultado NO identifica obligaciones ni autoriza asociar pagos.
Conserva procedencia (hoja/fila) y no transforma datos operativos de origen.
"""
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable
import re
import unicodedata


@dataclass(frozen=True)
class LineaFuente:
    fuente: str
    fila: int
    oc: str
    sku: str
    cliente: str = ""
    documento: str = ""
    estado: str = ""
    descripcion: str = ""
    pais: str = ""
    ddp: Decimal | None = None


@dataclass(frozen=True)
class CruceLinea:
    fuente: str
    fila: int
    estado: str
    candidatos: int
    referencia_fuente: str | None = None
    referencia_fila: int | None = None


def _clave(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    sin_tildes = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9]", "", sin_tildes.upper())


def _pais(texto: str) -> str:
    valor = _clave(texto)
    return {
        "COLOMBIA": "CO", "CO": "CO",
        "ECUADOR": "EC", "EC": "EC",
        "CHILE": "CL", "CL": "CL",
    }.get(valor, valor)


def _monto_valido(valor: Decimal | None) -> bool:
    return valor is None or (isinstance(valor, Decimal) and valor.is_finite())


def comparar_cartera_con_compras(
    cartera: Iterable[LineaFuente],
    compras: Iterable[LineaFuente],
) -> tuple[CruceLinea, ...]:
    """Diagnóstico estricto por OC/SKU más atributos, nunca join de saldo.

    Un mismo par OC/SKU puede describir varias líneas. Se requieren atributos
    adicionales para seleccionar una referencia y DDP presente para certificar
    coincidencia monetaria. Los valores no disponibles no se rellenan.
    """
    indice: dict[tuple[str, str], list[LineaFuente]] = defaultdict(list)
    for compra in compras:
        if not _monto_valido(compra.ddp):
            raise ValueError("El DDP de Compras debe ser Decimal finito o None.")
        oc, sku = _clave(compra.oc), _clave(compra.sku)
        if oc and oc != "NA" and sku and sku != "NA":
            indice[(oc, sku)].append(compra)

    resultados = []
    for fila in cartera:
        if not _monto_valido(fila.ddp):
            raise ValueError("El DDP de Cartera debe ser Decimal finito o None.")
        oc, sku = _clave(fila.oc), _clave(fila.sku)
        base = dict(fuente=fila.fuente, fila=fila.fila)

        if not oc or oc == "NA" or not sku or sku == "NA":
            resultados.append(CruceLinea(**base, estado="CLAVE_INCOMPLETA", candidatos=0))
            continue

        encontrados = indice.get((oc, sku), [])
        if not encontrados:
            resultados.append(CruceLinea(**base, estado="SIN_COINCIDENCIA", candidatos=0))
            continue

        candidatos = list(encontrados)
        def filtrar(campo: str, normalizador=_clave) -> bool:
            nonlocal candidatos
            original = normalizador(getattr(fila, campo))
            if not original:
                return True
            encontrados_campo = [
                compra for compra in candidatos
                if normalizador(getattr(compra, campo)) == original
            ]
            if not encontrados_campo:
                return False
            candidatos = encontrados_campo
            return True

        if not all([
            filtrar("pais", _pais),
            filtrar("cliente"),
            filtrar("documento"),
            filtrar("estado"),
            filtrar("descripcion"),
        ]):
            resultados.append(CruceLinea(
                **base, estado="ATRIBUTOS_DIFERENTES", candidatos=len(encontrados)
            ))
            continue

        if fila.ddp is not None:
            con_monto = [compra for compra in candidatos if compra.ddp == fila.ddp]
            if not con_monto:
                estado = (
                    "MONTO_SIN_EVIDENCIA"
                    if all(compra.ddp is None for compra in candidatos)
                    else "MONTO_DIFERENTE"
                )
                resultados.append(CruceLinea(
                    **base, estado=estado, candidatos=len(candidatos)
                ))
                continue
            candidatos = con_monto
        else:
            resultados.append(CruceLinea(
                **base, estado="MONTO_SIN_EVIDENCIA", candidatos=len(candidatos)
            ))
            continue

        if len(candidatos) != 1:
            resultados.append(CruceLinea(
                **base, estado="AMBIGUO", candidatos=len(candidatos)
            ))
            continue

        referencia = candidatos[0]
        resultados.append(CruceLinea(
            **base, estado="COINCIDE", candidatos=1,
            referencia_fuente=referencia.fuente,
            referencia_fila=referencia.fila,
        ))

    return tuple(resultados)


def resumir_cruce(resultados: Iterable[CruceLinea]) -> dict[str, int]:
    """Agrega únicamente conteos observados. No suma montos ni genera deudas."""
    return dict(sorted(Counter(resultado.estado for resultado in resultados).items()))
