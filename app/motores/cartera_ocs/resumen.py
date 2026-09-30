from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Iterable, TypeVar

from app.motores.cartera_ocs.importacion import RegistroCarteraEnCamino
from app.motores.cartera_ocs.mora import RegistroCarteraMora
from app.motores.cartera_ocs.proyeccion import RegistroProyeccionPago


T = TypeVar("T")


@dataclass(frozen=True)
class AgrupacionMontoCartera:
    clave: str
    registros: int
    monto: Decimal


@dataclass(frozen=True)
class ResumenOperacionesCartera:
    lineas: int
    ocs: int
    clientes: int
    valor_ddp: Decimal
    valor_anticipo: Decimal
    valor_financiado: Decimal
    por_etapa: tuple[AgrupacionMontoCartera, ...]


@dataclass(frozen=True)
class ResumenMoraCartera:
    registros: int
    clientes: int
    monto: Decimal
    por_estado: tuple[AgrupacionMontoCartera, ...]
    por_empresa: tuple[AgrupacionMontoCartera, ...]


@dataclass(frozen=True)
class ResumenProyeccionCartera:
    registros: int
    ocs: int
    clientes: int
    monto_esperado: Decimal
    valor_oc: Decimal
    por_mes: tuple[AgrupacionMontoCartera, ...]
    por_comercial: tuple[AgrupacionMontoCartera, ...]


def _texto_unico(valores: Iterable[str]) -> set[str]:
    return {
        texto
        for valor in valores
        if (texto := str(valor or "").strip())
    }


def _agrupar_monto(
    registros: Iterable[T],
    *,
    clave: Callable[[T], str],
    monto: Callable[[T], Decimal],
    fallback: str,
) -> tuple[AgrupacionMontoCartera, ...]:
    acumulado: dict[str, tuple[int, Decimal]] = {}

    for registro in registros:
        valor_clave = str(clave(registro) or "").strip() or fallback
        cantidad_actual, monto_actual = acumulado.get(
            valor_clave,
            (0, Decimal("0")),
        )
        acumulado[valor_clave] = (
            cantidad_actual + 1,
            monto_actual + Decimal(str(monto(registro))),
        )

    return tuple(
        AgrupacionMontoCartera(
            clave=valor_clave,
            registros=cantidad,
            monto=valor_monto,
        )
        for valor_clave, (cantidad, valor_monto) in sorted(acumulado.items())
    )


def resumir_operaciones(
    registros: Iterable[RegistroCarteraEnCamino],
) -> ResumenOperacionesCartera:
    """Resume líneas de Operaciones sin inferir saldo ni estado financiero.

    La granularidad se conserva a nivel de línea. OCs cuenta únicamente
    números de OC no vacíos y los montos se suman exactamente como Decimal.
    """

    items = tuple(registros)
    return ResumenOperacionesCartera(
        lineas=len(items),
        ocs=len(_texto_unico(item.oc for item in items)),
        clientes=len(_texto_unico(item.cliente for item in items)),
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
        por_etapa=_agrupar_monto(
            items,
            clave=lambda item: item.etapa,
            monto=lambda item: item.valor,
            fallback="Sin clasificar",
        ),
    )


def resumir_mora(
    registros: Iterable[RegistroCarteraMora],
) -> ResumenMoraCartera:
    """Resume la fuente de Mora sin reinterpretar sus estados observados."""

    items = tuple(registros)
    return ResumenMoraCartera(
        registros=len(items),
        clientes=len(_texto_unico(item.cliente for item in items)),
        monto=sum(
            (item.monto for item in items),
            start=Decimal("0"),
        ),
        por_estado=_agrupar_monto(
            items,
            clave=lambda item: item.estado,
            monto=lambda item: item.monto,
            fallback="SIN ESTADO",
        ),
        por_empresa=_agrupar_monto(
            items,
            clave=lambda item: item.empresa,
            monto=lambda item: item.monto,
            fallback="SIN EMPRESA",
        ),
    )


def resumir_proyeccion(
    registros: Iterable[RegistroProyeccionPago],
) -> ResumenProyeccionCartera:
    """Resume proyecciones manteniendo separado DDP de monto esperado."""

    items = tuple(registros)
    return ResumenProyeccionCartera(
        registros=len(items),
        ocs=len(_texto_unico(item.oc for item in items)),
        clientes=len(_texto_unico(item.cliente for item in items)),
        monto_esperado=sum(
            (item.monto for item in items),
            start=Decimal("0"),
        ),
        valor_oc=sum(
            (item.valor_oc for item in items),
            start=Decimal("0"),
        ),
        por_mes=_agrupar_monto(
            items,
            clave=lambda item: item.mes,
            monto=lambda item: item.monto,
            fallback="SIN MES",
        ),
        por_comercial=_agrupar_monto(
            items,
            clave=lambda item: item.comercial,
            monto=lambda item: item.monto,
            fallback="SIN ASIGNAR",
        ),
    )
