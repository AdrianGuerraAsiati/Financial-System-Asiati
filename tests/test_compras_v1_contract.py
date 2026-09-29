from app.main import app
from app.motores.compras_supply_chain.google_sheets import (
    ClienteGoogleSheetsReadonly,
    SHEETS_READONLY_SCOPE,
)
from app.motores.compras_supply_chain.normalizacion import clasificar_estado


RUTAS_V1 = {
    "/api/v1/compras/fuente/estado",
    "/api/v1/compras/catalogos",
    "/api/v1/compras/calidad",
    "/api/v1/compras/resumen",
    "/api/v1/compras/kpis",
    "/api/v1/compras/dashboard",
    "/api/v1/compras/atencion",
    "/api/v1/compras/validacion/tablero",
    "/api/v1/compras/export.zip",
    "/api/v1/compras/ocs",
    "/api/v1/compras/lineas",
    "/api/v1/compras/cobertura",
    "/api/v1/compras/timeline",
    "/api/v1/compras/llegadas",
    "/api/v1/compras/snapshots",
}


def test_compras_v1_exposes_the_closed_contract() -> None:
    rutas = {
        path
        for path in app.openapi()["paths"]
        if path.startswith("/api/v1/compras")
    }

    assert RUTAS_V1 <= rutas


def test_compras_v1_does_not_expose_source_write_back_methods() -> None:
    metodos_http = {"GET", "POST", "PUT", "PATCH", "DELETE"}
    metodos_por_ruta = {
        path: {
            metodo.upper()
            for metodo in operacion
            if metodo.upper() in metodos_http
        }
        for path, operacion in app.openapi()["paths"].items()
        if path.startswith("/api/v1/compras")
    }

    metodos_mutables = {"PUT", "PATCH", "DELETE"}
    assert all(
        not (metodos & metodos_mutables)
        for metodos in metodos_por_ruta.values()
    )

    # El único POST de la V1 persiste evidencia interna; no escribe al Sheet.
    rutas_post = {
        ruta
        for ruta, metodos in metodos_por_ruta.items()
        if "POST" in metodos
    }
    assert rutas_post == {"/api/v1/compras/snapshots"}

    assert SHEETS_READONLY_SCOPE.endswith("spreadsheets.readonly")
    assert not hasattr(ClienteGoogleSheetsReadonly, "actualizar_valores")
    assert not hasattr(ClienteGoogleSheetsReadonly, "append_valores")


def test_compras_v1_keeps_ambiguous_business_states_unresolved() -> None:
    for estado in (
        "EN OTM",
        "PENDIENTE DEPÓSITO",
        "PENDIENTE INVIMA",
    ):
        _, etapa, situacion = clasificar_estado(estado)
        assert etapa == "POR_DEFINIR"
        assert situacion == "POR_DEFINIR"
