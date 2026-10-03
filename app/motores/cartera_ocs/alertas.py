from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable

from app.motores.cartera_ocs.importacion import RegistroCarteraEnCamino
from app.motores.cartera_ocs.mora import RegistroCarteraMora
from app.motores.cartera_ocs.proyeccion import RegistroProyeccionPago


UMBRAL_CONCENTRACION_MORA = Decimal("0.50")
UMBRAL_CONCENTRACION_CLIENTE_PROYECCION = Decimal("0.35")
UMBRAL_CONCENTRACION_FECHA_PROYECCION = Decimal("0.30")


@dataclass(frozen=True)
class AlertaCartera:
    codigo: str
    tono_heredado: str
    titulo: str
    evidencia: dict[str, Any]


def _texto_normalizado(valor: str) -> str:
    sin_acentos = unicodedata.normalize("NFD", str(valor or ""))
    base = "".join(
        caracter
        for caracter in sin_acentos
        if unicodedata.category(caracter) != "Mn"
    )
    return re.sub(r"[^A-Z0-9]", "", base.upper())


def detectar_mora_con_operaciones_en_camino(
    mora: Iterable[RegistroCarteraMora],
    operaciones: Iterable[RegistroCarteraEnCamino],
) -> AlertaCartera | None:
    """Cruza Mora y FC con matching conservador por nombre normalizado exacto.

    Johan usaba además coincidencia por inclusión de strings. Esa parte no se
    porta como decisión automática para evitar falsos positivos hasta tener un
    cliente_id o catálogo de alias validado.
    """
    operaciones_items = tuple(operaciones)
    cruces: list[dict[str, Any]] = []

    for registro_mora in mora:
        if registro_mora.estado != "MORA":
            continue

        claves = {
            clave
            for valor in (registro_mora.cliente, registro_mora.empresa)
            if len(clave := _texto_normalizado(valor)) > 3
        }
        if not claves:
            continue

        relacionadas = tuple(
            operacion
            for operacion in operaciones_items
            if _texto_normalizado(operacion.cliente) in claves
        )
        if not relacionadas:
            continue

        cruces.append(
            {
                "nombre": registro_mora.empresa or registro_mora.cliente,
                "mora": registro_mora.monto,
                "transito": sum(
                    (item.valor for item in relacionadas),
                    start=Decimal("0"),
                ),
                "ocs": len(
                    {
                        item.oc
                        for item in relacionadas
                        if str(item.oc or "").strip()
                    }
                ),
            }
        )

    if not cruces:
        return None

    cruces.sort(key=lambda item: item["transito"], reverse=True)
    return AlertaCartera(
        codigo="CARTERA_MORA_CON_TRANSITO",
        tono_heredado="alta",
        titulo="Clientes en mora con mercancía en tránsito",
        evidencia={
            "clientes": cruces,
            "clientes_afectados": len(cruces),
            "valor_transito": sum(
                (item["transito"] for item in cruces),
                start=Decimal("0"),
            ),
            "metodo_matching": "nombre_normalizado_exacto",
            "nota_matching": (
                "El legado también aceptaba inclusión parcial de nombres; "
                "esa heurística queda fuera hasta validar cliente_id/alias."
            ),
        },
    )


def detectar_concentracion_mora(
    mora: Iterable[RegistroCarteraMora],
    *,
    umbral: Decimal = UMBRAL_CONCENTRACION_MORA,
    top_n: int = 3,
) -> AlertaCartera | None:
    en_mora = sorted(
        (item for item in mora if item.estado == "MORA"),
        key=lambda item: item.monto,
        reverse=True,
    )
    total = sum((item.monto for item in en_mora), start=Decimal("0"))
    principales = tuple(en_mora[:top_n])
    monto_principales = sum(
        (item.monto for item in principales),
        start=Decimal("0"),
    )
    participacion = monto_principales / total if total > 0 else Decimal("0")

    if total <= 0 or participacion <= umbral:
        return None

    return AlertaCartera(
        codigo="CARTERA_MORA_CONCENTRADA",
        tono_heredado="alta",
        titulo="La mora está concentrada en pocos clientes",
        evidencia={
            "mora_total": total,
            "mora_top": monto_principales,
            "participacion": participacion,
            "umbral_heredado": umbral,
            "top_n": top_n,
            "principales": [
                {
                    "nombre": item.empresa or item.cliente,
                    "monto": item.monto,
                }
                for item in principales
            ],
            "criterio_heredado": "top_registros_mora",
        },
    )


def detectar_concentracion_proyeccion_cliente(
    proyecciones: Iterable[RegistroProyeccionPago],
    *,
    mes: str,
    umbral: Decimal = UMBRAL_CONCENTRACION_CLIENTE_PROYECCION,
) -> AlertaCartera | None:
    items = tuple(item for item in proyecciones if item.mes == mes)
    total = sum((item.monto for item in items), start=Decimal("0"))
    if total <= 0:
        return None

    por_cliente: dict[str, Decimal] = {}
    for item in items:
        por_cliente[item.cliente] = (
            por_cliente.get(item.cliente, Decimal("0")) + item.monto
        )

    if not por_cliente:
        return None

    cliente, monto = max(por_cliente.items(), key=lambda item: item[1])
    participacion = monto / total
    if participacion <= umbral:
        return None

    return AlertaCartera(
        codigo="CARTERA_PROYECCION_CONCENTRADA_CLIENTE",
        tono_heredado="media",
        titulo="Un cliente concentra la proyección del mes",
        evidencia={
            "mes": mes,
            "cliente": cliente,
            "monto": monto,
            "monto_mes": total,
            "participacion": participacion,
            "umbral_heredado": umbral,
        },
    )


def detectar_concentracion_proyeccion_fecha(
    proyecciones: Iterable[RegistroProyeccionPago],
    *,
    mes: str,
    umbral: Decimal = UMBRAL_CONCENTRACION_FECHA_PROYECCION,
) -> AlertaCartera | None:
    items = tuple(item for item in proyecciones if item.mes == mes)
    total = sum((item.monto for item in items), start=Decimal("0"))
    if total <= 0:
        return None

    por_fecha: dict[str, Decimal] = {}
    for item in items:
        clave = item.fecha.isoformat()
        por_fecha[clave] = por_fecha.get(clave, Decimal("0")) + item.monto

    if not por_fecha:
        return None

    fecha, monto = max(por_fecha.items(), key=lambda item: item[1])
    participacion = monto / total
    if participacion <= umbral:
        return None

    return AlertaCartera(
        codigo="CARTERA_PROYECCION_CONCENTRADA_FECHA",
        tono_heredado="media",
        titulo="Una sola fecha concentra el recaudo",
        evidencia={
            "mes": mes,
            "fecha": fecha,
            "monto": monto,
            "monto_mes": total,
            "participacion": participacion,
            "umbral_heredado": umbral,
        },
    )


def detectar_clientes_saldados(
    mora: Iterable[RegistroCarteraMora],
) -> AlertaCartera | None:
    saldados = tuple(item for item in mora if item.estado == "SALDADO")
    if not saldados:
        return None

    return AlertaCartera(
        codigo="CARTERA_CLIENTES_SALDADOS",
        tono_heredado="buena",
        titulo="Clientes que salieron de mora",
        evidencia={
            "clientes": [
                {
                    "nombre": item.empresa or item.cliente,
                    "monto": item.monto,
                }
                for item in saldados
            ],
            "clientes_saldados": len(saldados),
            "monto": sum(
                (item.monto for item in saldados),
                start=Decimal("0"),
            ),
        },
    )


def detectar_alertas_cartera(
    *,
    mora: Iterable[RegistroCarteraMora],
    operaciones: Iterable[RegistroCarteraEnCamino],
    proyecciones: Iterable[RegistroProyeccionPago],
    mes: str,
) -> tuple[AlertaCartera, ...]:
    mora_items = tuple(mora)
    operaciones_items = tuple(operaciones)
    proyeccion_items = tuple(proyecciones)

    candidatas = (
        detectar_mora_con_operaciones_en_camino(
            mora_items,
            operaciones_items,
        ),
        detectar_concentracion_mora(mora_items),
        detectar_concentracion_proyeccion_cliente(
            proyeccion_items,
            mes=mes,
        ),
        detectar_concentracion_proyeccion_fecha(
            proyeccion_items,
            mes=mes,
        ),
        detectar_clientes_saldados(mora_items),
    )
    return tuple(alerta for alerta in candidatas if alerta is not None)
