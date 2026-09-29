import pytest

from app.motores.compras_supply_chain.google_sheets import (
    CLOUD_PLATFORM_SCOPE,
    ClienteGoogleSheetsReadonly,
    ConfiguracionComprasGoogleSheets,
    FuenteComprasGoogleSheets,
    SHEETS_READONLY_SCOPE,
    _extraer_pivotes_supply_chain,
)
from app.motores.compras_supply_chain.normalizacion import (
    clasificar_estado,
    normalizar_fila_compra,
    normalizar_modo_transporte,
)


def test_safe_states_are_classified_without_guessing_ambiguous_states() -> None:
    assert clasificar_estado("EN PRODUCCIÓN") == (
        "EN PRODUCCION",
        "PRODUCCION",
        "NORMAL",
    )
    assert clasificar_estado("ENVIADO A DESTINO") == (
        "ENVIADO A DESTINO",
        "TRANSITO",
        "NORMAL",
    )
    assert clasificar_estado("ENTREGADO") == (
        "ENTREGADO",
        "RECIBIDO",
        "NORMAL",
    )
    assert clasificar_estado("EN RECLAMACIÓN") == (
        "EN RECLAMACION",
        "POR_DEFINIR",
        "RECLAMACION",
    )

    for pendiente in (
        "EN OTM",
        "PENDIENTE DEPÓSITO",
        "PENDIENTE INVIMA",
        "DEVOLUCIÓN",
    ):
        _, etapa, situacion = clasificar_estado(pendiente)
        assert etapa == "POR_DEFINIR"
        assert situacion == "POR_DEFINIR"


@pytest.mark.parametrize(
    ("origen", "esperado"),
    [
        ("MARÍTIMO", "MARITIMO"),
        ("MARITIMA", "MARITIMO"),
        ("AÉREO", "AEREO"),
        ("AÉREA", "AEREO"),
        ("CASILLERO", "CASILLERO"),
        ("MUESTRA", "MUESTRA"),
    ],
)
def test_transport_variants_are_normalized_but_source_value_is_preserved(
    origen: str,
    esperado: str,
) -> None:
    linea = normalizar_fila_compra(
        {
            "NUMERO OC": "OC-1",
            "CLIENTE": "Cliente",
            "SKU": "SKU-1",
            "PROVEEDOR": "Proveedor",
            "ESTADO ": "ENVIADO A DESTINO",
            "MODO TRANSPORTE": origen,
        },
        pais="CO",
        fila_fuente=8,
    )

    assert normalizar_modo_transporte(origen) == esperado
    assert linea.modo_transporte_origen == origen
    assert linea.modo_transporte_normalizado == esperado
    assert linea.estado_origen == "ENVIADO A DESTINO"
    assert linea.fila_fuente == 8
    assert linea.hoja_fuente == "INFORME CLIENTES (CO)"



def test_live_destination_delivery_headers_are_recognized() -> None:
    casos = {
        "CO": "FECHA ENTREGA A BODEGA EN BOG",
        "EC": "FECHA ENTREGA A BODEGA EN QUITO",
        "CL": "FECHA ENTREGA A BODEGA EN SANTIAGO",
    }

    for pais, encabezado in casos.items():
        linea = normalizar_fila_compra(
            {
                "NUMERO OC": f"OC-{pais}",
                "CLIENTE": "Cliente",
                "PROVEEDOR": "Proveedor",
                "ESTADO": "ENTREGADO",
                "MODO TRANSPORTE": "MARITIMO",
                encabezado: "2026-09-29",
            },
            pais=pais,
            fila_fuente=2,
        )
        assert linea.fecha_entrega_bodega_destino == "2026-09-29"


def test_na_purchase_order_is_kept_and_marked_unidentified() -> None:
    linea = normalizar_fila_compra(
        {
            "NUMERO OC": "N/A",
            "CLIENTE": "Cliente",
            "ESTADO": "ANULADA",
        },
        pais="CL",
        fila_fuente=2,
    )

    assert linea.numero_oc == "N/A"
    assert linea.oc_identificada is False
    assert linea.etapa_logistica == "SIN_ETAPA"
    assert linea.situacion_operativa == "ANULADA"


class ClienteFake:
    def __init__(self) -> None:
        self.llamadas: list[tuple[str, str]] = []

    def obtener_valores(
        self,
        *,
        spreadsheet_id: str,
        rango: str,
    ) -> list[list[object]]:
        self.llamadas.append((spreadsheet_id, rango))
        return [
            ["NUMERO OC", "CLIENTE", "PROVEEDOR", "ESTADO", "MODO TRANSPORTE"],
            [f"OC-{len(self.llamadas)}", "Cliente", "Proveedor", "ENTREGADO", "MARITIMO"],
        ]


def test_google_client_uses_explicit_keyless_impersonation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.motores.compras_supply_chain.google_sheets as modulo

    source_credentials = object()
    target_credentials = object()
    capturado: dict[str, object] = {}

    def fake_default(*, scopes):
        capturado["source_scopes"] = scopes
        return source_credentials, None

    def fake_impersonated_credentials(**kwargs):
        capturado.update(kwargs)
        return target_credentials

    class SessionFake:
        def __init__(self, credentials):
            capturado["session_credentials"] = credentials

    monkeypatch.setattr(modulo.google.auth, "default", fake_default)
    monkeypatch.setattr(
        modulo.impersonated_credentials,
        "Credentials",
        fake_impersonated_credentials,
    )
    monkeypatch.setattr(modulo, "AuthorizedSession", SessionFake)

    ClienteGoogleSheetsReadonly(
        target_principal=(
            " financial-system-sheets@asiati-financial-system."
            "iam.gserviceaccount.com "
        )
    )

    assert capturado["source_scopes"] == [CLOUD_PLATFORM_SCOPE]
    assert capturado["source_credentials"] is source_credentials
    assert capturado["target_principal"] == (
        "financial-system-sheets@asiati-financial-system."
        "iam.gserviceaccount.com"
    )
    assert capturado["target_scopes"] == [SHEETS_READONLY_SCOPE]
    assert capturado["lifetime"] == 3600
    assert capturado["session_credentials"] is target_credentials


def test_source_reads_the_three_country_ranges_and_never_requires_write_api() -> None:
    cliente = ClienteFake()
    fuente = FuenteComprasGoogleSheets(
        cliente=cliente,
        configuracion=ConfiguracionComprasGoogleSheets(
            empresa_id=7,
            spreadsheet_id="sheet-id",
            rangos_por_pais={
                "CO": "'INFORME CLIENTES (CO)'!A:BG",
                "EC": "'INFORME CLIENTES (EC)'!A:BG",
                "CL": "'INFORME CLIENTES (CL)'!A:BG",
            },
        ),
    )

    lineas = fuente.listar(empresa_id=7)

    assert len(lineas) == 3
    assert {linea.pais for linea in lineas} == {"CO", "EC", "CL"}
    assert len(cliente.llamadas) == 3
    assert SHEETS_READONLY_SCOPE.endswith("spreadsheets.readonly")
    assert not hasattr(cliente, "actualizar_valores")



def test_unconsumed_duplicate_headers_do_not_degrade_operational_schema() -> None:
    class ClienteConDuplicadoNoConsumido:
        def obtener_valores(self, *, spreadsheet_id: str, rango: str):
            return [
                [
                    "NUMERO OC",
                    "CLIENTE",
                    "PROVEEDOR",
                    "ESTADO",
                    "MODO TRANSPORTE",
                    "CBM",
                    "CBM",
                ],
                ["OC-1", "Cliente", "Proveedor", "ENTREGADO", "MARITIMO", "1", "1"],
            ]

    fuente = FuenteComprasGoogleSheets(
        cliente=ClienteConDuplicadoNoConsumido(),
        configuracion=ConfiguracionComprasGoogleSheets(
            empresa_id=7,
            spreadsheet_id="sheet-id",
            rangos_por_pais={"CO": "CO!A:Z", "EC": "EC!A:Z", "CL": "CL!A:Z"},
        ),
    )

    snapshot = fuente.obtener_snapshot(empresa_id=7)

    assert snapshot.esquema_valido is True
    assert all(
        diagnostico.encabezados_duplicados == ()
        for diagnostico in snapshot.diagnosticos
    )


def test_formula_only_trailing_rows_are_not_counted_as_purchase_lines() -> None:
    class ClienteConFormulasArrastradas:
        def obtener_valores(self, *, spreadsheet_id: str, rango: str):
            return [
                [
                    "NUMERO OC",
                    "CLIENTE",
                    "PROVEEDOR",
                    "ESTADO",
                    "MODO TRANSPORTE",
                    "ALERTA PROVEEDOR (auto)",
                ],
                ["OC-1", "Cliente", "Proveedor", "ENTREGADO", "MARITIMO", "OK"],
                ["", "", "", "", "", "FORMULA"],
                ["", "", "", "", "", "FORMULA"],
            ]

    fuente = FuenteComprasGoogleSheets(
        cliente=ClienteConFormulasArrastradas(),
        configuracion=ConfiguracionComprasGoogleSheets(
            empresa_id=7,
            spreadsheet_id="sheet-id",
            rangos_por_pais={"CO": "CO!A:Z", "EC": "EC!A:Z", "CL": "CL!A:Z"},
        ),
    )

    snapshot = fuente.obtener_snapshot(empresa_id=7)

    assert len(snapshot.lineas) == 3
    assert all(diagnostico.filas_datos == 1 for diagnostico in snapshot.diagnosticos)


def test_source_reuses_snapshot_inside_ttl() -> None:
    cliente = ClienteFake()
    fuente = FuenteComprasGoogleSheets(
        cliente=cliente,
        configuracion=ConfiguracionComprasGoogleSheets(
            empresa_id=7,
            spreadsheet_id="sheet-id",
            rangos_por_pais={
                "CO": "CO!A:Z",
                "EC": "EC!A:Z",
                "CL": "CL!A:Z",
            },
            cache_ttl_seconds=60,
        ),
    )

    primera = fuente.listar(empresa_id=7)
    segunda = fuente.listar(empresa_id=7)

    assert primera == segunda
    assert len(cliente.llamadas) == 3
    assert fuente.estado_cache()["tiene_snapshot"] is True

    fuente.obtener_snapshot(empresa_id=7, forzar_lectura=True)
    assert len(cliente.llamadas) == 6


def test_source_blocks_operational_read_when_critical_header_disappears() -> None:
    class ClienteConDrift:
        def obtener_valores(self, *, spreadsheet_id: str, rango: str):
            return [
                ["NUMERO OC", "CLIENTE", "ESTADO", "MODO TRANSPORTE"],
                ["OC-1", "Cliente", "ENTREGADO", "MARITIMO"],
            ]

    fuente = FuenteComprasGoogleSheets(
        cliente=ClienteConDrift(),
        configuracion=ConfiguracionComprasGoogleSheets(
            empresa_id=7,
            spreadsheet_id="sheet-id",
            rangos_por_pais={"CO": "CO!A:Z", "EC": "EC!A:Z", "CL": "CL!A:Z"},
        ),
    )

    snapshot = fuente.obtener_snapshot(empresa_id=7)

    assert snapshot.esquema_valido is False
    assert all(
        "proveedor" in diagnostico.campos_criticos_faltantes
        for diagnostico in snapshot.diagnosticos
    )

    from app.motores.compras_supply_chain.google_sheets import (
        EsquemaComprasInvalidoError,
    )

    with pytest.raises(EsquemaComprasInvalidoError, match="esquema de Compras cambió"):
        fuente.listar(empresa_id=7)



def test_source_wraps_external_read_failures() -> None:
    from app.motores.compras_supply_chain.google_sheets import (
        LecturaComprasGoogleSheetsError,
    )

    class ClienteRoto:
        def obtener_valores(self, *, spreadsheet_id: str, rango: str):
            raise RuntimeError("Google no disponible")

    fuente = FuenteComprasGoogleSheets(
        cliente=ClienteRoto(),
        configuracion=ConfiguracionComprasGoogleSheets(
            empresa_id=7,
            spreadsheet_id="sheet-id",
            rangos_por_pais={"CO": "CO!A:Z", "EC": "EC!A:Z", "CL": "CL!A:Z"},
        ),
    )

    with pytest.raises(LecturaComprasGoogleSheetsError, match="CO"):
        fuente.obtener_snapshot(empresa_id=7)


def test_pivot_metadata_maps_each_block_to_its_source_country() -> None:
    metadatos = {
        "sheets": [
            {
                "properties": {
                    "sheetId": 101,
                    "title": "INFORME CLIENTES (CO)",
                }
            },
            {
                "properties": {
                    "sheetId": 202,
                    "title": "INFORME CLIENTES (CL)",
                }
            },
            {
                "properties": {
                    "sheetId": 303,
                    "title": "INFORME CLIENTES (EC)",
                }
            },
        ]
    }
    grid = {
        "sheets": [
            {
                "data": [
                    {
                        "startRow": 1,
                        "startColumn": 1,
                        "rowData": [
                            {
                                "values": [
                                    {
                                        "pivotTable": {
                                            "source": {"sheetId": 101}
                                        }
                                    },
                                    {},
                                    {},
                                    {},
                                    {},
                                    {},
                                    {
                                        "pivotTable": {
                                            "source": {"sheetId": 202}
                                        }
                                    },
                                    {},
                                    {},
                                    {},
                                    {},
                                    {},
                                    {
                                        "pivotTable": {
                                            "source": {"sheetId": 303}
                                        }
                                    },
                                ]
                            }
                        ],
                    }
                ]
            }
        ]
    }

    pivotes = _extraer_pivotes_supply_chain(metadatos, grid)

    assert [(item.pais, item.fila_encabezado, item.columna_estado) for item in pivotes] == [
        ("CO", 1, 1),
        ("CL", 1, 7),
        ("EC", 1, 13),
    ]
