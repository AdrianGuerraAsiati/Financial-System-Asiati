from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReglaImportada:
    motor_slug: str
    fuente_id: int | None
    patron: str
    tipo_match: str
    prioridad: int
    condiciones: dict[str, Any]
    tipo: str | None
    unidad_negocio: str | None
    categoria: str | None
    empresa: str | None
    tercero: str | None
    modalidad: str | None
    fijo_variable: str | None
    ciudad: str | None
    requiere_revision: bool
    origen: str | None


def reglas_desde_catalogo_wallets(
    catalogo: dict[str, Any],
    *,
    motor_slug: str = "conciliacion_wallets",
    fuente_id: int | None = None,
) -> list[ReglaImportada]:
    """Adapta el catálogo aceptado por wallets al contrato genérico del core.

    En wallets, "tipo" es la condición cruda ENTRADA/SALIDA e
    "ingreso_egreso" es la primera dimensión contable.
    """
    conceptos = catalogo.get("conceptos")
    if not isinstance(conceptos, list):
        raise ValueError("El catálogo de wallets debe incluir una lista 'conceptos'.")

    reglas: list[ReglaImportada] = []
    for indice, concepto in enumerate(conceptos, start=1):
        for requerido in ("tipo", "empieza_con", "ingreso_egreso"):
            if requerido not in concepto:
                raise ValueError(
                    f"Concepto #{indice} del catálogo no incluye '{requerido}'."
                )

        condiciones: dict[str, Any] = {"tipo_fuente": concepto["tipo"]}
        if concepto.get("contiene"):
            condiciones["contiene"] = concepto["contiene"]

        reglas.append(
            ReglaImportada(
                motor_slug=motor_slug,
                fuente_id=fuente_id,
                patron=concepto["empieza_con"],
                tipo_match="EMPIEZA_CON",
                prioridad=indice,
                condiciones=condiciones,
                tipo=concepto.get("ingreso_egreso"),
                unidad_negocio=concepto.get("unidad_negocio"),
                categoria=concepto.get("categoria"),
                empresa=None,
                tercero=None,
                modalidad="WALLET",
                fijo_variable="VARIABLE",
                ciudad=None,
                requiere_revision=bool(concepto.get("requiere_revision", False)),
                origen=concepto.get("origen"),
            )
        )
    return reglas
