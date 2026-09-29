from __future__ import annotations

import os
from typing import Any, Protocol

from .google_sheets import (
    CONTRATOS_FUENTE_CARTERA,
    ClienteGoogleSheetsApi,
    ConfiguracionGoogleSheetsIncompletaError,
)


PREVIEW_MAX_ROWS = 20
PREVIEW_MAX_COLUMN = "ZZ"


class ClienteDescubrimientoCartera(Protocol):
    def obtener_hojas(
        self,
        *,
        spreadsheet_id: str,
    ) -> tuple[str, ...]: ...

    def obtener_valores(
        self,
        *,
        spreadsheet_id: str,
        rango: str,
    ) -> list[list[Any]]: ...


def _titulo_a1(titulo: str) -> str:
    return "'" + titulo.replace("'", "''") + "'"


def _mejor_candidato(
    valores: list[list[Any]],
    *,
    tipo: str,
    titulo_hoja: str,
) -> dict[str, object] | None:
    requeridos = CONTRATOS_FUENTE_CARTERA[tipo]
    mejor: dict[str, object] | None = None
    mejor_puntaje = 0

    for indice, fila in enumerate(valores, start=1):
        encabezados = {
            str(valor).strip()
            for valor in fila
            if str(valor).strip()
        }
        encontrados = [
            campo
            for campo in requeridos
            if campo in encabezados
        ]
        puntaje = len(encontrados)
        if puntaje == 0:
            continue

        faltantes = [
            campo
            for campo in requeridos
            if campo not in encabezados
        ]
        coincide = not faltantes
        candidato = {
            "tipo": tipo,
            "fila_encabezado": indice,
            "campos_encontrados": encontrados,
            "campos_faltantes": faltantes,
            "coincide": coincide,
            "rango_sugerido": (
                f"{_titulo_a1(titulo_hoja)}!A{indice}:{PREVIEW_MAX_COLUMN}"
                if coincide
                else None
            ),
        }

        if (
            mejor is None
            or puntaje > mejor_puntaje
            or (
                puntaje == mejor_puntaje
                and bool(candidato["coincide"])
                and not bool(mejor["coincide"])
            )
        ):
            mejor = candidato
            mejor_puntaje = puntaje

    return mejor


def descubrir_hojas_cartera_desde_entorno(
    *,
    empresa_id: int,
    cliente: ClienteDescubrimientoCartera | None = None,
) -> dict[str, object]:
    empresa_configurada = os.getenv(
        "CARTERA_SHEETS_EMPRESA_ID",
        "",
    ).strip()
    spreadsheet_id = os.getenv(
        "CARTERA_SHEETS_SPREADSHEET_ID",
        "",
    ).strip()

    faltantes = [
        nombre
        for nombre, valor in (
            ("CARTERA_SHEETS_EMPRESA_ID", empresa_configurada),
            ("CARTERA_SHEETS_SPREADSHEET_ID", spreadsheet_id),
        )
        if not valor
    ]
    if faltantes:
        raise ConfiguracionGoogleSheetsIncompletaError(
            "Falta configurar: " + ", ".join(faltantes)
        )

    try:
        empresa_configurada_int = int(empresa_configurada)
    except ValueError as exc:
        raise ConfiguracionGoogleSheetsIncompletaError(
            "CARTERA_SHEETS_EMPRESA_ID debe ser entero."
        ) from exc

    if empresa_configurada_int != empresa_id:
        raise ConfiguracionGoogleSheetsIncompletaError(
            f"No existe configuración de Google Sheets para empresa {empresa_id}."
        )

    cliente_real = cliente or ClienteGoogleSheetsApi(
        target_principal=os.getenv(
            "GOOGLE_IMPERSONATE_SERVICE_ACCOUNT",
            "",
        ).strip()
        or None,
    )

    hojas: list[dict[str, object]] = []
    coincidencias_exactas = 0

    for titulo in cliente_real.obtener_hojas(
        spreadsheet_id=spreadsheet_id,
    ):
        titulo_a1 = _titulo_a1(titulo)
        rango_preview = (
            f"{titulo_a1}!A1:{PREVIEW_MAX_COLUMN}{PREVIEW_MAX_ROWS}"
        )
        try:
            valores = cliente_real.obtener_valores(
                spreadsheet_id=spreadsheet_id,
                rango=rango_preview,
            )
        except Exception as exc:
            hojas.append(
                {
                    "titulo": titulo,
                    "rango_previsualizacion": rango_preview,
                    "candidatos": [],
                    "error_lectura": type(exc).__name__,
                }
            )
            continue

        candidatos: list[dict[str, object]] = []
        for tipo in CONTRATOS_FUENTE_CARTERA:
            candidato = _mejor_candidato(
                valores,
                tipo=tipo,
                titulo_hoja=titulo,
            )
            if candidato is None:
                continue
            candidatos.append(candidato)
            if candidato["coincide"] is True:
                coincidencias_exactas += 1

        hojas.append(
            {
                "titulo": titulo,
                "rango_previsualizacion": rango_preview,
                "candidatos": candidatos,
            }
        )

    return {
        "empresa_id": empresa_id,
        "spreadsheet_id": spreadsheet_id,
        "solo_lectura": True,
        "hojas": hojas,
        "coincidencias_exactas": coincidencias_exactas,
        "nota": (
            "Las coincidencias se basan únicamente en encabezados del "
            "contrato de Cartera. El descubrimiento no modifica Google Sheets "
            "ni configura variables automáticamente."
        ),
    }
