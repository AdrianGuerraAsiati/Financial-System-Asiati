"""Datos sintéticos para previsualizar Compras en desarrollo local.

Nunca se usan en producción y nunca escriben a Google Sheets.
"""

from __future__ import annotations

from typing import Any

from .google_sheets import (
    ConfiguracionComprasGoogleSheets,
    FuenteComprasGoogleSheets,
    RANGOS_DEFAULT,
)


class ClienteComprasDemo:
    def obtener_valores(
        self,
        *,
        spreadsheet_id: str,
        rango: str,
    ) -> list[list[Any]]:
        if "Supply Chain" in rango:
            return _supply_chain_demo()

        pais = _pais_desde_rango(rango)
        encabezados = [
            "NUMERO OC",
            "CLIENTE",
            "SKU",
            "DESCRIPCION",
            "PROVEEDOR",
            "ESTADO",
            "MODO TRANSPORTE",
            "DOCUMENTO DE TRANSPORTE",
            "ETD",
            "ETA",
            "FECHA ENTREGA EN BODEGA BOGOTA",
            "VALOR TOTAL COMPRA USD",
            "VALOR OCI (DDP)",
        ]
        return [encabezados, *_filas_demo(pais)]


def _supply_chain_demo() -> list[list[Any]]:
    return [
        ["COLOMBIA"],
        ["ESTADO", "SUM de VALOR OCI (DDP)"],
        ["EN PRODUCCION", "17800.00"],
        ["ENVIADO A DESTINO", "6100.00"],
        ["EN OTM", "1450.75"],
        ["PENDIENTE DEPÓSITO", "720.00"],
        [],
        ["ECUADOR"],
        ["ESTADO", "SUM de VALOR OCI (DDP)"],
        ["EN NACIONALIZACION", "9200.00"],
        ["EN BODEGA ASIATI YIWU", "3200.00"],
        [],
        ["CHILE"],
        ["ESTADO", "SUM de VALOR OCI (DDP)"],
        ["EN BODEGA ASIATI SHENZHEN", "10400.00"],
    ]


def _pais_desde_rango(rango: str) -> str:
    for pais in ("CO", "EC", "CL"):
        if f"({pais})" in rango or rango.startswith(f"{pais}!"):
            return pais
    return "CO"


def _filas_demo(pais: str) -> list[list[str]]:
    base = {
        "CO": [
            ["OC-CO-1001", "Cliente Andino", "SKU-001", "Equipo demo", "Proveedor A", "EN PRODUCCION", "MARITIMO", "", "", "2026-11-15", "", "12500.00", "17800.00"],
            ["OC-CO-1001", "Cliente Andino", "SKU-002", "Accesorio demo", "Proveedor B", "ENVIADO A DESTINO", "AEREO", "AWB-DEMO-1", "2026-09-20", "2026-10-05", "", "4200.00", "6100.00"],
            ["OC-CO-1002", "Cliente Centro", "SKU-003", "Muestra demo", "Proveedor C", "EN OTM", "MUESTRA", "OTM-DEMO", "2026-09-22", "2026-10-08", "", "980.50", "1450.75"],
            ["OC-CO-1003", "Cliente Norte", "SKU-004", "Producto entregado", "Proveedor D", "ENTREGADO", "MARITIMO", "BL-DEMO-9", "2026-08-10", "2026-09-10", "2026-09-14", "8300.00", "11200.00"],
            ["N/A", "Cliente Demo", "SKU-005", "Sin OC", "Proveedor A", "PENDIENTE DEPÓSITO", "MARITIMO", "", "", "", "", "500.00", "720.00"],
        ],
        "EC": [
            ["OC-EC-2001", "Cliente Ecuador", "SKU-101", "Equipo EC", "Proveedor A", "EN NACIONALIZACION", "MARITIMO", "BL-EC-1", "2026-08-30", "2026-09-28", "", "6400.00", "9200.00"],
            ["OC-EC-2002", "Cliente Ecuador", "SKU-102", "Producto origen", "Proveedor B", "EN BODEGA ASIATI YIWU", "CASILLERO", "", "", "", "", "2100.00", "3200.00"],
        ],
        "CL": [
            ["OC-CL-3001", "Cliente Chile", "SKU-201", "Equipo CL", "Proveedor E", "EN BODEGA ASIATI SHENZHEN", "MARITIMO", "", "", "", "", "7100.00", "10400.00"],
            ["OC-CL-3002", "Cliente Chile", "SKU-202", "Producto anulado", "Proveedor F", "ANULADA", "AEREO", "", "", "", "", "1300.00", "1800.00"],
        ],
    }
    return base[pais]


def construir_fuente_demo(*, empresa_id: int = 1) -> FuenteComprasGoogleSheets:
    return FuenteComprasGoogleSheets(
        cliente=ClienteComprasDemo(),
        configuracion=ConfiguracionComprasGoogleSheets(
            empresa_id=empresa_id,
            spreadsheet_id="DEMO_LOCAL",
            rangos_por_pais=RANGOS_DEFAULT,
            cache_ttl_seconds=60,
            modo_fuente="DEMO_LOCAL",
            rango_supply_chain="'Supply Chain'!A:Z",
        ),
    )
