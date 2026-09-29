from __future__ import annotations

import os
import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol
from urllib.parse import quote

import google.auth
from google.auth.transport.requests import AuthorizedSession

from .contrato import DiagnosticoEsquema, analizar_encabezados
from .dominio import LineaCompra
from .normalizacion import normalizar_fila_compra


SHEETS_READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"

RANGOS_DEFAULT = {
    "CO": "'INFORME CLIENTES (CO)'!A:BG",
    "EC": "'INFORME CLIENTES (EC)'!A:BG",
    "CL": "'INFORME CLIENTES (CL)'!A:BG",
}


class ConfiguracionComprasGoogleSheetsError(RuntimeError):
    pass


class EsquemaComprasInvalidoError(RuntimeError):
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
    cache_ttl_seconds: int = 60


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
            valores = self.cliente.obtener_valores(
                spreadsheet_id=self.configuracion.spreadsheet_id,
                rango=rango,
            )
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
        if any(str(valor or "").strip() for valor in fila.values()):
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
            cache_ttl_seconds=_entero_positivo(
                "COMPRAS_SHEETS_CACHE_SECONDS",
                60,
            ),
        ),
    )
