import os
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Mapping, Protocol
from urllib.parse import quote

import google.auth
from google.auth.transport.requests import AuthorizedSession

from app.motores.cartera_ocs.importacion import (
    RegistroCarteraEnCamino,
    normalizar_fila_cartera,
)


SHEETS_READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"


class ConfiguracionGoogleSheetsIncompletaError(RuntimeError):
    pass


@dataclass(frozen=True)
class ConfiguracionGoogleSheets:
    spreadsheet_id: str
    rango: str


class ClienteValoresGoogleSheets(Protocol):
    def obtener_valores(
        self,
        *,
        spreadsheet_id: str,
        rango: str,
    ) -> list[list[Any]]: ...


class ClienteGoogleSheetsApi:
    """Cliente mínimo de Google Sheets API v4 con credenciales estándar."""

    def __init__(self, session: Any | None = None) -> None:
        if session is None:
            credentials, _ = google.auth.default(
                scopes=[SHEETS_READONLY_SCOPE],
            )
            session = AuthorizedSession(credentials)
        self.session = session

    def obtener_valores(
        self,
        *,
        spreadsheet_id: str,
        rango: str,
    ) -> list[list[Any]]:
        encoded_sheet = quote(spreadsheet_id, safe="")
        encoded_range = quote(rango, safe="")
        url = (
            "https://sheets.googleapis.com/v4/spreadsheets/"
            f"{encoded_sheet}/values/{encoded_range}?majorDimension=ROWS"
        )
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        body = response.json()
        return body.get("values", [])


class LectorFilasGoogleSheets(Protocol):
    def leer_filas(
        self,
        *,
        empresa_id: int,
    ) -> Iterable[Mapping[str, Any]]: ...


class LectorGoogleSheetsApi:
    """Convierte el rango de una hoja en filas identificadas por encabezado."""

    def __init__(
        self,
        *,
        cliente: ClienteValoresGoogleSheets,
        configuraciones: Mapping[int, ConfiguracionGoogleSheets],
    ) -> None:
        self.cliente = cliente
        self.configuraciones = configuraciones

    def leer_filas(
        self,
        *,
        empresa_id: int,
    ) -> Iterable[Mapping[str, Any]]:
        config = self.configuraciones.get(empresa_id)
        if config is None:
            raise ConfiguracionGoogleSheetsIncompletaError(
                f"No existe configuración de Google Sheets para empresa {empresa_id}."
            )

        valores = self.cliente.obtener_valores(
            spreadsheet_id=config.spreadsheet_id,
            rango=config.rango,
        )
        if not valores:
            return ()

        encabezados = [str(valor).strip() for valor in valores[0]]
        filas: list[dict[str, Any]] = []

        for valores_fila in valores[1:]:
            fila = {
                encabezado: (
                    valores_fila[indice]
                    if indice < len(valores_fila)
                    else ""
                )
                for indice, encabezado in enumerate(encabezados)
                if encabezado
            }
            if any(str(valor).strip() for valor in fila.values()):
                filas.append(fila)

        return tuple(filas)


class FuenteOperacionesGoogleSheets:
    """Adapta filas provenientes de Google Sheets al contrato de Cartera."""

    def __init__(self, lector: LectorFilasGoogleSheets) -> None:
        self.lector = lector

    def listar(
        self,
        *,
        empresa_id: int,
    ) -> tuple[RegistroCarteraEnCamino, ...]:
        operaciones: list[RegistroCarteraEnCamino] = []

        for fila in self.lector.leer_filas(empresa_id=empresa_id):
            registro = normalizar_fila_cartera(fila)
            if registro is not None:
                operaciones.append(registro)

        return tuple(operaciones)


def construir_fuente_google_sheets_desde_entorno(
    *,
    cliente: ClienteValoresGoogleSheets | None = None,
) -> FuenteOperacionesGoogleSheets:
    empresa_id = os.getenv("CARTERA_SHEETS_EMPRESA_ID", "").strip()
    spreadsheet_id = os.getenv("CARTERA_SHEETS_SPREADSHEET_ID", "").strip()
    rango = os.getenv("CARTERA_SHEETS_RANGE", "").strip()

    faltantes = [
        nombre
        for nombre, valor in (
            ("CARTERA_SHEETS_EMPRESA_ID", empresa_id),
            ("CARTERA_SHEETS_SPREADSHEET_ID", spreadsheet_id),
            ("CARTERA_SHEETS_RANGE", rango),
        )
        if not valor
    ]
    if faltantes:
        raise ConfiguracionGoogleSheetsIncompletaError(
            "Falta configurar: " + ", ".join(faltantes)
        )

    try:
        empresa = int(empresa_id)
    except ValueError as exc:
        raise ConfiguracionGoogleSheetsIncompletaError(
            "CARTERA_SHEETS_EMPRESA_ID debe ser entero."
        ) from exc

    cliente_real = cliente or ClienteGoogleSheetsApi()
    lector = LectorGoogleSheetsApi(
        cliente=cliente_real,
        configuraciones={
            empresa: ConfiguracionGoogleSheets(
                spreadsheet_id=spreadsheet_id,
                rango=rango,
            )
        },
    )
    return FuenteOperacionesGoogleSheets(lector)
