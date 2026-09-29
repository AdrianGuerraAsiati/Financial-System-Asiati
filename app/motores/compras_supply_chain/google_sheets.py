from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import quote

import google.auth
from google.auth.transport.requests import AuthorizedSession

from .dominio import LineaCompra
from .normalizacion import HOJAS_POR_PAIS, normalizar_fila_compra


SHEETS_READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"

RANGOS_DEFAULT = {
    "CO": "'INFORME CLIENTES (CO)'!A:BG",
    "EC": "'INFORME CLIENTES (EC)'!A:BG",
    "CL": "'INFORME CLIENTES (CL)'!A:BG",
}


class ConfiguracionComprasGoogleSheetsError(RuntimeError):
    pass


class ClienteValoresGoogleSheets(Protocol):
    def obtener_valores(
        self,
        *,
        spreadsheet_id: str,
        rango: str,
    ) -> list[list[Any]]: ...


class ClienteGoogleSheetsReadonly:
    """Cliente mínimo: solo GET sobre spreadsheets.values de Sheets API v4."""

    def __init__(self, session: Any | None = None) -> None:
        if session is None:
            credentials, _ = google.auth.default(scopes=[SHEETS_READONLY_SCOPE])
            session = AuthorizedSession(credentials)
        self.session = session

    def obtener_valores(
        self,
        *,
        spreadsheet_id: str,
        rango: str,
    ) -> list[list[Any]]:
        spreadsheet = quote(spreadsheet_id, safe="")
        rango_codificado = quote(rango, safe="")
        url = (
            "https://sheets.googleapis.com/v4/spreadsheets/"
            f"{spreadsheet}/values/{rango_codificado}?majorDimension=ROWS"
        )
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return response.json().get("values", [])


@dataclass(frozen=True)
class ConfiguracionComprasGoogleSheets:
    empresa_id: int
    spreadsheet_id: str
    rangos_por_pais: Mapping[str, str]


class FuenteComprasGoogleSheets:
    def __init__(
        self,
        *,
        cliente: ClienteValoresGoogleSheets,
        configuracion: ConfiguracionComprasGoogleSheets,
    ) -> None:
        self.cliente = cliente
        self.configuracion = configuracion

    def listar(self, *, empresa_id: int) -> tuple[LineaCompra, ...]:
        if empresa_id != self.configuracion.empresa_id:
            raise ConfiguracionComprasGoogleSheetsError(
                f"No existe configuración de Compras para empresa {empresa_id}."
            )

        lineas: list[LineaCompra] = []
        for pais in ("CO", "EC", "CL"):
            rango = self.configuracion.rangos_por_pais[pais]
            valores = self.cliente.obtener_valores(
                spreadsheet_id=self.configuracion.spreadsheet_id,
                rango=rango,
            )
            lineas.extend(_normalizar_rango(valores, pais=pais))

        return tuple(lineas)


def _normalizar_rango(
    valores: list[list[Any]],
    *,
    pais: str,
) -> tuple[LineaCompra, ...]:
    if not valores:
        return ()

    encabezados = [str(valor).strip() for valor in valores[0]]
    resultado: list[LineaCompra] = []

    for indice, valores_fila in enumerate(valores[1:], start=2):
        fila = {
            encabezado: (
                valores_fila[posicion]
                if posicion < len(valores_fila)
                else ""
            )
            for posicion, encabezado in enumerate(encabezados)
            if encabezado
        }
        if not any(str(valor or "").strip() for valor in fila.values()):
            continue
        resultado.append(
            normalizar_fila_compra(
                fila,
                pais=pais,
                fila_fuente=indice,
            )
        )

    return tuple(resultado)


def construir_fuente_compras_desde_entorno(
    *,
    cliente: ClienteValoresGoogleSheets | None = None,
) -> FuenteComprasGoogleSheets:
    empresa_id = os.getenv("COMPRAS_SHEETS_EMPRESA_ID", "").strip()
    spreadsheet_id = os.getenv("COMPRAS_SHEETS_SPREADSHEET_ID", "").strip()

    faltantes = [
        nombre
        for nombre, valor in (
            ("COMPRAS_SHEETS_EMPRESA_ID", empresa_id),
            ("COMPRAS_SHEETS_SPREADSHEET_ID", spreadsheet_id),
        )
        if not valor
    ]
    if faltantes:
        raise ConfiguracionComprasGoogleSheetsError(
            "Falta configurar: " + ", ".join(faltantes)
        )

    try:
        empresa = int(empresa_id)
    except ValueError as exc:
        raise ConfiguracionComprasGoogleSheetsError(
            "COMPRAS_SHEETS_EMPRESA_ID debe ser entero."
        ) from exc

    rangos = {
        pais: os.getenv(
            f"COMPRAS_SHEETS_{pais}_RANGE",
            rango_default,
        ).strip()
        for pais, rango_default in RANGOS_DEFAULT.items()
    }
    vacios = [
        f"COMPRAS_SHEETS_{pais}_RANGE"
        for pais, rango in rangos.items()
        if not rango
    ]
    if vacios:
        raise ConfiguracionComprasGoogleSheetsError(
            "Falta configurar: " + ", ".join(vacios)
        )

    return FuenteComprasGoogleSheets(
        cliente=cliente or ClienteGoogleSheetsReadonly(),
        configuracion=ConfiguracionComprasGoogleSheets(
            empresa_id=empresa,
            spreadsheet_id=spreadsheet_id,
            rangos_por_pais=rangos,
        ),
    )
