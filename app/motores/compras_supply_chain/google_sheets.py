from __future__ import annotations

import os
import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol
from urllib.parse import quote

import google.auth
from google.auth import impersonated_credentials
from google.auth.transport.requests import AuthorizedSession

from .contrato import (
    DiagnosticoEsquema,
    analizar_encabezados,
    es_encabezado_consumido,
)
from .dominio import LineaCompra
from .normalizacion import HOJAS_POR_PAIS, normalizar_fila_compra


SHEETS_READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"
CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"

RANGOS_DEFAULT = {
    "CO": "'INFORME CLIENTES (CO)'!A:BG",
    "EC": "'INFORME CLIENTES (EC)'!A:BG",
    "CL": "'INFORME CLIENTES (CL)'!A:BG",
}


class ConfiguracionComprasGoogleSheetsError(RuntimeError):
    pass


class EsquemaComprasInvalidoError(RuntimeError):
    pass


class LecturaComprasGoogleSheetsError(RuntimeError):
    pass


class ClienteValoresGoogleSheets(Protocol):
    def obtener_valores(
        self,
        *,
        spreadsheet_id: str,
        rango: str,
    ) -> list[list[Any]]: ...


@dataclass(frozen=True)
class PivotSupplyChain:
    pais: str
    fila_encabezado: int
    columna_estado: int
    hoja_origen: str


def _extraer_pivotes_supply_chain(
    metadatos: Mapping[str, Any],
    grid: Mapping[str, Any],
) -> tuple[PivotSupplyChain, ...]:
    titulos_por_id: dict[int, str] = {}
    for hoja in metadatos.get("sheets", []):
        propiedades = hoja.get("properties", {})
        sheet_id = propiedades.get("sheetId")
        titulo = propiedades.get("title")
        if isinstance(sheet_id, int) and isinstance(titulo, str):
            titulos_por_id[sheet_id] = titulo

    pais_por_titulo = {
        titulo: pais
        for pais, titulo in HOJAS_POR_PAIS.items()
    }

    pivotes: list[PivotSupplyChain] = []
    for hoja in grid.get("sheets", []):
        for bloque in hoja.get("data", []):
            inicio_fila = int(bloque.get("startRow", 0))
            inicio_columna = int(bloque.get("startColumn", 0))
            for desplazamiento_fila, fila in enumerate(
                bloque.get("rowData", [])
            ):
                for desplazamiento_columna, celda in enumerate(
                    fila.get("values", [])
                ):
                    pivote = celda.get("pivotTable")
                    if not isinstance(pivote, Mapping):
                        continue
                    fuente = pivote.get("source", {})
                    source_sheet_id = fuente.get("sheetId")
                    hoja_origen = titulos_por_id.get(source_sheet_id)
                    pais = pais_por_titulo.get(hoja_origen or "")
                    if not pais or not hoja_origen:
                        continue
                    pivotes.append(
                        PivotSupplyChain(
                            pais=pais,
                            fila_encabezado=(
                                inicio_fila + desplazamiento_fila
                            ),
                            columna_estado=(
                                inicio_columna + desplazamiento_columna
                            ),
                            hoja_origen=hoja_origen,
                        )
                    )

    return tuple(
        sorted(
            pivotes,
            key=lambda item: (
                item.fila_encabezado,
                item.columna_estado,
                item.pais,
            ),
        )
    )


class ClienteGoogleSheetsReadonly:
    """Cliente mínimo: solo GET sobre spreadsheets.values de Sheets API v4."""

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
                    scopes=[CLOUD_PLATFORM_SCOPE]
                )
                credentials = impersonated_credentials.Credentials(
                    source_credentials=source_credentials,
                    target_principal=principal,
                    target_scopes=[SHEETS_READONLY_SCOPE],
                    lifetime=3600,
                )
            else:
                credentials, _ = google.auth.default(
                    scopes=[SHEETS_READONLY_SCOPE]
                )
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

    def obtener_pivotes(
        self,
        *,
        spreadsheet_id: str,
        rango: str,
    ) -> tuple[PivotSupplyChain, ...]:
        spreadsheet = quote(spreadsheet_id, safe="")

        campos_metadatos = quote(
            "sheets(properties(sheetId,title))",
            safe="",
        )
        metadatos_url = (
            "https://sheets.googleapis.com/v4/spreadsheets/"
            f"{spreadsheet}?includeGridData=false&fields={campos_metadatos}"
        )
        metadatos_response = self.session.get(metadatos_url, timeout=30)
        metadatos_response.raise_for_status()

        rango_codificado = quote(rango, safe="")
        campos_pivotes = quote(
            "sheets(data(startRow,startColumn,rowData(values(pivotTable))))",
            safe="",
        )
        pivotes_url = (
            "https://sheets.googleapis.com/v4/spreadsheets/"
            f"{spreadsheet}?includeGridData=true"
            f"&ranges={rango_codificado}"
            f"&fields={campos_pivotes}"
        )
        pivotes_response = self.session.get(pivotes_url, timeout=30)
        pivotes_response.raise_for_status()

        return _extraer_pivotes_supply_chain(
            metadatos_response.json(),
            pivotes_response.json(),
        )


@dataclass(frozen=True)
class ConfiguracionComprasGoogleSheets:
    empresa_id: int
    spreadsheet_id: str
    rangos_por_pais: Mapping[str, str]
    cache_ttl_seconds: int = 60
    modo_fuente: str = "GOOGLE_SHEETS"
    rango_supply_chain: str | None = None


@dataclass(frozen=True)
class SnapshotCompras:
    cargado_en: datetime
    lineas: tuple[LineaCompra, ...]
    diagnosticos: tuple[DiagnosticoEsquema, ...]

    @property
    def esquema_valido(self) -> bool:
        return all(diagnostico.valido for diagnostico in self.diagnosticos)


class FuenteComprasGoogleSheets:
    def __init__(
        self,
        *,
        cliente: ClienteValoresGoogleSheets,
        configuracion: ConfiguracionComprasGoogleSheets,
    ) -> None:
        self.cliente = cliente
        self.configuracion = configuracion
        self._snapshot: SnapshotCompras | None = None
        self._snapshot_monotonic: float | None = None
        self._tablero_supply_chain: tuple[tuple[Any, ...], ...] | None = None
        self._tablero_supply_chain_monotonic: float | None = None

    def _validar_empresa(self, empresa_id: int) -> None:
        if empresa_id != self.configuracion.empresa_id:
            raise ConfiguracionComprasGoogleSheetsError(
                f"No existe configuración de Compras para empresa {empresa_id}."
            )

    def _cache_vigente(self) -> bool:
        if self._snapshot is None or self._snapshot_monotonic is None:
            return False
        edad = time.monotonic() - self._snapshot_monotonic
        return edad < self.configuracion.cache_ttl_seconds

    def obtener_snapshot(
        self,
        *,
        empresa_id: int,
        forzar_lectura: bool = False,
    ) -> SnapshotCompras:
        self._validar_empresa(empresa_id)

        if not forzar_lectura and self._cache_vigente():
            assert self._snapshot is not None
            return self._snapshot

        lineas: list[LineaCompra] = []
        diagnosticos: list[DiagnosticoEsquema] = []

        for pais in ("CO", "EC", "CL"):
            rango = self.configuracion.rangos_por_pais[pais]
            try:
                valores = self.cliente.obtener_valores(
                    spreadsheet_id=self.configuracion.spreadsheet_id,
                    rango=rango,
                )
            except Exception as exc:
                raise LecturaComprasGoogleSheetsError(
                    f"No se pudo leer la hoja de Compras para {pais} ({rango})."
                ) from exc
            normalizadas, diagnostico = _normalizar_rango(
                valores,
                pais=pais,
                rango=rango,
            )
            lineas.extend(normalizadas)
            diagnosticos.append(diagnostico)

        snapshot = SnapshotCompras(
            cargado_en=datetime.now(timezone.utc),
            lineas=tuple(lineas),
            diagnosticos=tuple(diagnosticos),
        )
        self._snapshot = snapshot
        self._snapshot_monotonic = time.monotonic()
        return snapshot

    def listar(self, *, empresa_id: int) -> tuple[LineaCompra, ...]:
        snapshot = self.obtener_snapshot(empresa_id=empresa_id)
        if not snapshot.esquema_valido:
            problemas = []
            for diagnostico in snapshot.diagnosticos:
                if diagnostico.valido:
                    continue
                if diagnostico.campos_criticos_faltantes:
                    problemas.append(
                        f"{diagnostico.pais}: faltan "
                        + ", ".join(diagnostico.campos_criticos_faltantes)
                    )
                if diagnostico.encabezados_duplicados:
                    problemas.append(
                        f"{diagnostico.pais}: encabezados duplicados "
                        + ", ".join(diagnostico.encabezados_duplicados)
                    )
            raise EsquemaComprasInvalidoError(
                "El esquema de Compras cambió y la lectura operativa se bloqueó "
                "para evitar resultados silenciosamente incorrectos. "
                + "; ".join(problemas)
            )
        return snapshot.lineas

    def obtener_tablero_supply_chain(
        self,
        *,
        empresa_id: int,
        forzar_lectura: bool = False,
    ) -> tuple[tuple[Any, ...], ...] | None:
        self._validar_empresa(empresa_id)
        rango = self.configuracion.rango_supply_chain
        if not rango:
            return None

        if (
            not forzar_lectura
            and self._tablero_supply_chain is not None
            and self._tablero_supply_chain_monotonic is not None
            and (
                time.monotonic() - self._tablero_supply_chain_monotonic
                < self.configuracion.cache_ttl_seconds
            )
        ):
            return self._tablero_supply_chain

        try:
            valores = self.cliente.obtener_valores(
                spreadsheet_id=self.configuracion.spreadsheet_id,
                rango=rango,
            )
        except Exception as exc:
            raise LecturaComprasGoogleSheetsError(
                f"No se pudo leer la vista derivada Supply Chain ({rango})."
            ) from exc

        self._tablero_supply_chain = tuple(tuple(fila) for fila in valores)
        self._tablero_supply_chain_monotonic = time.monotonic()
        return self._tablero_supply_chain

    def obtener_pivotes_supply_chain(
        self,
        *,
        empresa_id: int,
    ) -> tuple[PivotSupplyChain, ...]:
        self._validar_empresa(empresa_id)
        rango = self.configuracion.rango_supply_chain
        if not rango:
            return ()

        lector = getattr(self.cliente, "obtener_pivotes", None)
        if not callable(lector):
            return ()

        try:
            return tuple(
                lector(
                    spreadsheet_id=self.configuracion.spreadsheet_id,
                    rango=rango,
                )
            )
        except Exception as exc:
            raise LecturaComprasGoogleSheetsError(
                "No se pudo leer la metadata de pivotes de Supply Chain "
                f"({rango})."
            ) from exc

    def estado_cache(self) -> dict[str, object]:
        if self._snapshot is None or self._snapshot_monotonic is None:
            return {
                "tiene_snapshot": False,
                "ttl_segundos": self.configuracion.cache_ttl_seconds,
                "cargado_en": None,
                "edad_segundos": None,
                "vence_en_segundos": None,
            }

        edad = max(0.0, time.monotonic() - self._snapshot_monotonic)
        restante = max(0.0, self.configuracion.cache_ttl_seconds - edad)
        return {
            "tiene_snapshot": True,
            "ttl_segundos": self.configuracion.cache_ttl_seconds,
            "cargado_en": self._snapshot.cargado_en.isoformat(),
            "edad_segundos": round(edad, 3),
            "vence_en_segundos": round(restante, 3),
        }


def _normalizar_rango(
    valores: list[list[Any]],
    *,
    pais: str,
    rango: str,
) -> tuple[tuple[LineaCompra, ...], DiagnosticoEsquema]:
    encabezados = [str(valor).strip() for valor in valores[0]] if valores else []
    filas_con_datos: list[tuple[int, dict[str, Any]]] = []

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
        if any(
            str(valor or "").strip()
            for encabezado, valor in fila.items()
            if es_encabezado_consumido(encabezado)
        ):
            filas_con_datos.append((indice, fila))

    diagnostico = analizar_encabezados(
        encabezados,
        pais=pais,
        rango=rango,
        filas_datos=len(filas_con_datos),
    )

    resultado = tuple(
        normalizar_fila_compra(
            fila,
            pais=pais,
            fila_fuente=indice,
        )
        for indice, fila in filas_con_datos
    )
    return resultado, diagnostico


def _booleano(nombre: str, defecto: bool = False) -> bool:
    crudo = os.getenv(nombre)
    if crudo is None or not crudo.strip():
        return defecto
    valor = crudo.strip().lower()
    if valor in {"1", "true", "yes", "si", "sí"}:
        return True
    if valor in {"0", "false", "no"}:
        return False
    raise ConfiguracionComprasGoogleSheetsError(
        f"{nombre} debe ser true o false."
    )


def _entero_positivo(nombre: str, defecto: int) -> int:
    crudo = os.getenv(nombre, str(defecto)).strip()
    try:
        valor = int(crudo)
    except ValueError as exc:
        raise ConfiguracionComprasGoogleSheetsError(
            f"{nombre} debe ser entero."
        ) from exc
    if valor <= 0:
        raise ConfiguracionComprasGoogleSheetsError(
            f"{nombre} debe ser mayor que cero."
        )
    return valor


def construir_fuente_compras_desde_entorno(
    *,
    cliente: ClienteValoresGoogleSheets | None = None,
) -> FuenteComprasGoogleSheets:
    if _booleano("COMPRAS_DEMO_MODE", False):
        if os.getenv("APP_ENV", "development").strip().lower() == "production":
            raise ConfiguracionComprasGoogleSheetsError(
                "COMPRAS_DEMO_MODE no puede usarse en producción."
            )
        from .demo import construir_fuente_demo

        empresa_demo = os.getenv("COMPRAS_SHEETS_EMPRESA_ID", "1").strip() or "1"
        try:
            empresa_id_demo = int(empresa_demo)
        except ValueError as exc:
            raise ConfiguracionComprasGoogleSheetsError(
                "COMPRAS_SHEETS_EMPRESA_ID debe ser entero."
            ) from exc
        return construir_fuente_demo(empresa_id=empresa_id_demo)

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
        cliente=cliente
        or ClienteGoogleSheetsReadonly(
            target_principal=(
                os.getenv("GOOGLE_IMPERSONATE_SERVICE_ACCOUNT", "").strip()
                or None
            )
        ),
        configuracion=ConfiguracionComprasGoogleSheets(
            empresa_id=empresa,
            spreadsheet_id=spreadsheet_id,
            rangos_por_pais=rangos,
            cache_ttl_seconds=_entero_positivo(
                "COMPRAS_SHEETS_CACHE_SECONDS",
                60,
            ),
            rango_supply_chain=(
                os.getenv(
                    "COMPRAS_SHEETS_SUPPLY_CHAIN_RANGE",
                    "'Supply Chain '!A:Z",
                ).strip()
                or None
            ),
        ),
    )
