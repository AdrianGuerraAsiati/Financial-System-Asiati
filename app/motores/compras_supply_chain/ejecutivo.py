from __future__ import annotations

from collections import Counter
from typing import Iterable

from .agrupacion import agrupar_ocs
from .atencion import evaluar_puntos_atencion
from .dominio import LineaCompra
from .kpis import ESTADOS_ACTIVOS_TABLERO_ACTUAL


_ESTADOS_ACTIVOS = frozenset(ESTADOS_ACTIVOS_TABLERO_ACTUAL)


def resumen_ejecutivo(lineas: Iterable[LineaCompra]) -> dict[str, object]:
    lineas_lista = tuple(lineas)
    activas = tuple(
        linea
        for linea in lineas_lista
        if linea.estado_normalizado in _ESTADOS_ACTIVOS
    )

    ocs = tuple(agrupar_ocs(lineas_lista))
    ocs_identificadas = tuple(oc for oc in ocs if oc.oc_identificada)
    claves_activas = {
        (linea.pais, linea.numero_oc)
        for linea in activas
        if linea.oc_identificada
    }

    puntos = evaluar_puntos_atencion(lineas_lista)

    return {
        "lineas": len(lineas_lista),
        "lineas_en_poblacion_actual": len(activas),
        "ocs_identificadas": len(ocs_identificadas),
        "ocs_con_al_menos_una_linea_en_poblacion_actual": len(claves_activas),
        "ocs_mixtas": sum(
            1
            for oc in ocs_identificadas
            if oc.estado_mixto or oc.proveedor_mixto or oc.transporte_mixto
        ),
        "lineas_sin_oc": sum(
            1 for linea in lineas_lista if not linea.oc_identificada
        ),
        "lineas_por_pais": dict(
            sorted(Counter(linea.pais for linea in lineas_lista).items())
        ),
        "lineas_activas_por_pais": dict(
            sorted(Counter(linea.pais for linea in activas).items())
        ),
        "lineas_activas_por_estado": dict(
            sorted(
                Counter(linea.estado_normalizado for linea in activas).items()
            )
        ),
        "lineas_activas_por_transporte": dict(
            sorted(
                Counter(
                    linea.modo_transporte_normalizado or "(VACIO)"
                    for linea in activas
                ).items()
            )
        ),
        "puntos_atencion_total": sum(punto.cantidad for punto in puntos),
        "puntos_atencion_por_codigo": {
            punto.codigo: punto.cantidad for punto in puntos
        },
        "nota": (
            "Los conteos de población actual reproducen los estados observados "
            "en el pivote Supply Chain; no redefinen estados ambiguos ni una OC "
            "corporativamente 'activa'."
        ),
    }
