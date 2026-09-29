import pytest

from app.motores.compras_supply_chain.google_sheets import (
    ConfiguracionComprasGoogleSheets,
    FuenteComprasGoogleSheets,
    SHEETS_READONLY_SCOPE,
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
