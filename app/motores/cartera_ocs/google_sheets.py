import os
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Mapping, Protocol
from urllib.parse import quote

import google.auth
from google.auth import impersonated_credentials
from google.auth.transport.requests import AuthorizedSession

from app.motores.cartera_ocs.importacion import (
    RegistroCarteraEnCamino,
    normalizar_fila_cartera,
)
from app.motores.cartera_ocs.mora import (
    RegistroCarteraMora,
    normalizar_fila_mora,
)
from app.motores.cartera_ocs.proyeccion import (
    RegistroProyeccionPago,
    normalizar_fila_proyeccion,
)


SHEETS_READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"
CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"

CONTRATOS_FUENTE_CARTERA: dict[str, tuple[str, ...]] = {
    "OPERACIONES": (
        "NUMERO OC",
        "VALOR OCI (DDP)",
        "CARTERA",
    ),
    "MORA": (
        "Cliente",
        "Monto en mora (USD)",
        "CARTERA",
    ),
    "PROYECCION": (
        "NUMERO OC",
        "FECHA DE PAGO ESPERADA",
        "MONTO ESPERADO",
    ),
}


class ConfiguracionGoogleSheetsIncompletaError(RuntimeError):
    pass


@dataclass(frozen=True)
class DiagnosticoRangoCartera:
    tipo: str
    rango: str
    filas_datos: int
    campos_criticos_faltantes: tuple[str, ...]
    encabezados_duplicados: tuple[str, ...]

    @property
    def valido(self) -> bool:
        return (
            not self.campos_criticos_faltantes
            and not self.encabezados_duplicados
        )

    def como_dict(self) -> dict[str, object]:
        return {
            "tipo": self.tipo,
            "rango": self.rango,
            "filas_datos": self.filas_datos,
            "valido": self.valido,
            "campos_criticos_faltantes": list(
                self.campos_criticos_faltantes
            ),
            "encabezados_duplicados": list(
                self.encabezados_duplicados
            ),
        }


def analizar_rango_cartera(
    valores: list[list[Any]],
    *,
    tipo: str,
    rango: str,
) -> DiagnosticoRangoCartera:
    tipo_normalizado = tipo.strip().upper()
    requeridos = CONTRATOS_FUENTE_CARTERA.get(tipo_normalizado)
    if requeridos is None:
        raise ValueError(f"Tipo de fuente de Cartera desconocido: {tipo}.")

    encabezados = [
        str(valor).strip()
        for valor in (valores[0] if valores else [])
        if str(valor).strip()
    ]
    presentes = set(encabezados)
    duplicados = tuple(
        sorted(
            encabezado
            for encabezado in presentes
            if encabezados.count(encabezado) > 1
        )
    )
    faltantes = tuple(
        encabezado
        for encabezado in requeridos
        if encabezado not in presentes
    )
    filas_datos = sum(
        1
        for fila in valores[1:]
        if any(str(valor or "").strip() for valor in fila)
    )

    return DiagnosticoRangoCartera(
        tipo=tipo_normalizado,
        rango=rango,
        filas_datos=filas_datos,
        campos_criticos_faltantes=faltantes,
        encabezados_duplicados=duplicados,
    )


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
    """Cliente mínimo de Google Sheets API v4, siempre en solo lectura."""

    def __init__(
        self,
        session: Any | None = None,
        *,
        target_principal: str | None = None,
    ) -> None:
        if session is None:
            principal = (target_principal or "").strip()
            if principal:
                source_credentials, _ = google.auth.default(
                    scopes=[CLOUD_PLATFORM_SCOPE],
                )
                credentials = impersonated_credentials.Credentials(
                    source_credentials=source_credentials,
                    target_principal=principal,
                    target_scopes=[SHEETS_READONLY_SCOPE],
                    lifetime=3600,
                )
            else:
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


def _cliente_google_desde_entorno() -> ClienteGoogleSheetsApi:
    return ClienteGoogleSheetsApi(
        target_principal=os.getenv(
            "GOOGLE_IMPERSONATE_SERVICE_ACCOUNT",
            "",
        ).strip()
        or None,
    )


def diagnosticar_fuente_google_sheets_desde_entorno(
    *,
    empresa_id: int,
    cliente: ClienteValoresGoogleSheets | None = None,
) -> dict[str, object]:
    empresa_configurada = os.getenv(
        "CARTERA_SHEETS_EMPRESA_ID",
        "",
    ).strip()
    spreadsheet_id = os.getenv(
        "CARTERA_SHEETS_SPREADSHEET_ID",
        "",
    ).strip()
    rangos = {
        "OPERACIONES": os.getenv("CARTERA_SHEETS_RANGE", "").strip(),
        "MORA": os.getenv("CARTERA_SHEETS_MORA_RANGE", "").strip(),
        "PROYECCION": os.getenv(
            "CARTERA_SHEETS_PROYECCION_RANGE",
            "",
        ).strip(),
    }

    faltantes = [
        nombre
        for nombre, valor in (
            ("CARTERA_SHEETS_EMPRESA_ID", empresa_configurada),
            ("CARTERA_SHEETS_SPREADSHEET_ID", spreadsheet_id),
            ("CARTERA_SHEETS_RANGE", rangos["OPERACIONES"]),
            ("CARTERA_SHEETS_MORA_RANGE", rangos["MORA"]),
            (
                "CARTERA_SHEETS_PROYECCION_RANGE",
                rangos["PROYECCION"],
            ),
        )
        if not valor
    ]
    if faltantes:
        return {
            "estado": "NO_CONFIGURADO",
            "empresa_id": empresa_id,
            "modo_fuente": "GOOGLE_SHEETS",
            "solo_lectura": True,
            "faltantes": faltantes,
            "diagnosticos": [],
            "resumen": {
                "rangos": 0,
                "rangos_validos": 0,
                "filas": 0,
            },
        }

    try:
        empresa_configurada_int = int(empresa_configurada)
    except ValueError:
        return {
            "estado": "NO_CONFIGURADO",
            "empresa_id": empresa_id,
            "modo_fuente": "GOOGLE_SHEETS",
            "solo_lectura": True,
            "faltantes": ["CARTERA_SHEETS_EMPRESA_ID debe ser entero"],
            "diagnosticos": [],
            "resumen": {
                "rangos": 0,
                "rangos_validos": 0,
                "filas": 0,
            },
        }

    if empresa_configurada_int != empresa_id:
        return {
            "estado": "NO_CONFIGURADO",
            "empresa_id": empresa_id,
            "modo_fuente": "GOOGLE_SHEETS",
            "solo_lectura": True,
            "faltantes": [
                (
                    "No existe configuración de Cartera para empresa "
                    f"{empresa_id}."
                )
            ],
            "diagnosticos": [],
            "resumen": {
                "rangos": 0,
                "rangos_validos": 0,
                "filas": 0,
            },
        }

    cliente_real = cliente or _cliente_google_desde_entorno()
    diagnosticos: list[dict[str, object]] = []
    errores_lectura = 0

    for tipo, rango in rangos.items():
        try:
            valores = cliente_real.obtener_valores(
                spreadsheet_id=spreadsheet_id,
                rango=rango,
            )
            diagnostico = analizar_rango_cartera(
                valores,
                tipo=tipo,
                rango=rango,
            )
            diagnosticos.append(diagnostico.como_dict())
        except Exception as exc:
            errores_lectura += 1
            diagnosticos.append(
                {
                    "tipo": tipo,
                    "rango": rango,
                    "filas_datos": 0,
                    "valido": False,
                    "campos_criticos_faltantes": [],
                    "encabezados_duplicados": [],
                    "error_lectura": type(exc).__name__,
                }
            )

    validos = sum(
        1
        for item in diagnosticos
        if item.get("valido") is True
    )
    filas = sum(
        int(item.get("filas_datos", 0))
        for item in diagnosticos
    )
    if errores_lectura:
        estado = "ERROR"
    elif validos == len(rangos):
        estado = "OK"
    else:
        estado = "DEGRADADO"

    return {
        "estado": estado,
        "empresa_id": empresa_id,
        "modo_fuente": "GOOGLE_SHEETS",
        "solo_lectura": True,
        "faltantes": [],
        "diagnosticos": diagnosticos,
        "resumen": {
            "rangos": len(rangos),
            "rangos_validos": validos,
            "filas": filas,
        },
    }


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

    cliente_real = cliente or _cliente_google_desde_entorno()
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



class FuenteMoraGoogleSheets:
    """Adapta filas de la hoja MORA al contrato de Cartera."""

    def __init__(self, lector: LectorFilasGoogleSheets) -> None:
        self.lector = lector

    def listar(
        self,
        *,
        empresa_id: int,
    ) -> tuple[RegistroCarteraMora, ...]:
        registros: list[RegistroCarteraMora] = []

        for fila in self.lector.leer_filas(empresa_id=empresa_id):
            registro = normalizar_fila_mora(fila)
            if registro is not None:
                registros.append(registro)

        return tuple(registros)


def construir_fuente_mora_google_sheets_desde_entorno(
    *,
    cliente: ClienteValoresGoogleSheets | None = None,
) -> FuenteMoraGoogleSheets:
    empresa_id = os.getenv("CARTERA_SHEETS_EMPRESA_ID", "").strip()
    spreadsheet_id = os.getenv("CARTERA_SHEETS_SPREADSHEET_ID", "").strip()
    rango = os.getenv("CARTERA_SHEETS_MORA_RANGE", "").strip()

    faltantes = [
        nombre
        for nombre, valor in (
            ("CARTERA_SHEETS_EMPRESA_ID", empresa_id),
            ("CARTERA_SHEETS_SPREADSHEET_ID", spreadsheet_id),
            ("CARTERA_SHEETS_MORA_RANGE", rango),
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

    lector = LectorGoogleSheetsApi(
        cliente=cliente or _cliente_google_desde_entorno(),
        configuraciones={
            empresa: ConfiguracionGoogleSheets(
                spreadsheet_id=spreadsheet_id,
                rango=rango,
            )
        },
    )
    return FuenteMoraGoogleSheets(lector)



class FuenteProyeccionGoogleSheets:
    """Adapta filas de PROYECCIONES al contrato de Cartera."""

    def __init__(self, lector: LectorFilasGoogleSheets) -> None:
        self.lector = lector

    def listar(
        self,
        *,
        empresa_id: int,
    ) -> tuple[RegistroProyeccionPago, ...]:
        registros: list[RegistroProyeccionPago] = []

        for fila in self.lector.leer_filas(empresa_id=empresa_id):
            registro = normalizar_fila_proyeccion(fila)
            if registro is not None:
                registros.append(registro)

        return tuple(registros)


def construir_fuente_proyeccion_google_sheets_desde_entorno(
    *,
    cliente: ClienteValoresGoogleSheets | None = None,
) -> FuenteProyeccionGoogleSheets:
    empresa_id = os.getenv("CARTERA_SHEETS_EMPRESA_ID", "").strip()
    spreadsheet_id = os.getenv("CARTERA_SHEETS_SPREADSHEET_ID", "").strip()
    rango = os.getenv("CARTERA_SHEETS_PROYECCION_RANGE", "").strip()

    faltantes = [
        nombre
        for nombre, valor in (
            ("CARTERA_SHEETS_EMPRESA_ID", empresa_id),
            ("CARTERA_SHEETS_SPREADSHEET_ID", spreadsheet_id),
            ("CARTERA_SHEETS_PROYECCION_RANGE", rango),
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

    lector = LectorGoogleSheetsApi(
        cliente=cliente or _cliente_google_desde_entorno(),
        configuraciones={
            empresa: ConfiguracionGoogleSheets(
                spreadsheet_id=spreadsheet_id,
                rango=rango,
            )
        },
    )
    return FuenteProyeccionGoogleSheets(lector)
