from app.motores.cartera_ocs.google_sheets import (
    analizar_rango_cartera,
    diagnosticar_fuente_google_sheets_desde_entorno,
)


class ClienteDiagnosticoFake:
    def __init__(self) -> None:
        self.llamadas = []

    def obtener_valores(self, *, spreadsheet_id: str, rango: str):
        self.llamadas.append((spreadsheet_id, rango))
        if rango == "FC!A:Z":
            return [
                [
                    "NOMBRE",
                    "CLIENTE",
                    "NUMERO OC",
                    "VALOR OCI (DDP)",
                    "CARTERA",
                ],
                ["Cliente A", "Contacto", "OC-1", "100", "EN CAMINO"],
            ]
        if rango == "MORA!A:Z":
            return [
                [
                    "Cliente",
                    "Empresa / Subtítulo",
                    "Monto en mora (USD)",
                    "Observación más reciente",
                    "CARTERA",
                ],
                ["Cliente Mora", "ASIATI", "50", "Pendiente", "MORA"],
            ]
        if rango == "PROY!A:Z":
            return [
                [
                    "NUMERO OC",
                    "FECHA DE PAGO ESPERADA",
                    "MONTO ESPERADO",
                ],
                ["OC-1", "2026-10-15", "40"],
            ]
        raise AssertionError(rango)


def test_source_range_diagnostic_detects_missing_critical_headers() -> None:
    diagnostico = analizar_rango_cartera(
        [
            ["NOMBRE", "CLIENTE", "VALOR OCI (DDP)", "CARTERA"],
            ["Cliente", "Contacto", "100", "EN CAMINO"],
        ],
        tipo="OPERACIONES",
        rango="FC!A:Z",
    )

    assert diagnostico.valido is False
    assert diagnostico.filas_datos == 1
    assert diagnostico.campos_criticos_faltantes == ("NUMERO OC",)


def test_source_range_diagnostic_accepts_projection_contract() -> None:
    diagnostico = analizar_rango_cartera(
        [
            ["NUMERO OC", "FECHA DE PAGO ESPERADA", "MONTO ESPERADO"],
            ["OC-1", "2026-10-15", "40"],
        ],
        tipo="PROYECCION",
        rango="PROY!A:Z",
    )

    assert diagnostico.valido is True
    assert diagnostico.filas_datos == 1
    assert diagnostico.encabezados_duplicados == ()


def test_environment_diagnostic_reads_all_three_cartera_ranges(monkeypatch) -> None:
    monkeypatch.setenv("CARTERA_SHEETS_EMPRESA_ID", "7")
    monkeypatch.setenv("CARTERA_SHEETS_SPREADSHEET_ID", "sheet-123")
    monkeypatch.setenv("CARTERA_SHEETS_RANGE", "FC!A:Z")
    monkeypatch.setenv("CARTERA_SHEETS_MORA_RANGE", "MORA!A:Z")
    monkeypatch.setenv("CARTERA_SHEETS_PROYECCION_RANGE", "PROY!A:Z")

    cliente = ClienteDiagnosticoFake()
    estado = diagnosticar_fuente_google_sheets_desde_entorno(
        empresa_id=7,
        cliente=cliente,
    )

    assert estado["estado"] == "OK"
    assert estado["solo_lectura"] is True
    assert estado["empresa_id"] == 7
    assert estado["resumen"]["rangos"] == 3
    assert estado["resumen"]["rangos_validos"] == 3
    assert estado["resumen"]["filas"] == 3
    assert {item["tipo"] for item in estado["diagnosticos"]} == {
        "OPERACIONES",
        "MORA",
        "PROYECCION",
    }
    assert cliente.llamadas == [
        ("sheet-123", "FC!A:Z"),
        ("sheet-123", "MORA!A:Z"),
        ("sheet-123", "PROY!A:Z"),
    ]


def test_environment_diagnostic_reports_missing_configuration(monkeypatch) -> None:
    for nombre in (
        "CARTERA_SHEETS_EMPRESA_ID",
        "CARTERA_SHEETS_SPREADSHEET_ID",
        "CARTERA_SHEETS_RANGE",
        "CARTERA_SHEETS_MORA_RANGE",
        "CARTERA_SHEETS_PROYECCION_RANGE",
    ):
        monkeypatch.delenv(nombre, raising=False)

    estado = diagnosticar_fuente_google_sheets_desde_entorno(empresa_id=1)

    assert estado["estado"] == "NO_CONFIGURADO"
    assert "CARTERA_SHEETS_SPREADSHEET_ID" in estado["faltantes"]
    assert "CARTERA_SHEETS_RANGE" in estado["faltantes"]


def test_environment_diagnostic_allows_partial_cartera_configuration(monkeypatch) -> None:
    monkeypatch.setenv("CARTERA_SHEETS_EMPRESA_ID", "7")
    monkeypatch.setenv("CARTERA_SHEETS_SPREADSHEET_ID", "sheet-123")
    monkeypatch.setenv("CARTERA_SHEETS_RANGE", "FC!A:Z")
    monkeypatch.delenv("CARTERA_SHEETS_MORA_RANGE", raising=False)
    monkeypatch.delenv("CARTERA_SHEETS_PROYECCION_RANGE", raising=False)

    cliente = ClienteDiagnosticoFake()
    estado = diagnosticar_fuente_google_sheets_desde_entorno(
        empresa_id=7,
        cliente=cliente,
    )

    assert estado["estado"] == "DEGRADADO"
    assert estado["resumen"]["rangos"] == 3
    assert estado["resumen"]["rangos_configurados"] == 1
    assert estado["resumen"]["rangos_validos"] == 1
    assert estado["resumen"]["filas"] == 1
    assert estado["faltantes"] == [
        "CARTERA_SHEETS_MORA_RANGE",
        "CARTERA_SHEETS_PROYECCION_RANGE",
    ]
    diagnosticos = {
        item["tipo"]: item
        for item in estado["diagnosticos"]
    }
    assert diagnosticos["OPERACIONES"]["valido"] is True
    assert diagnosticos["OPERACIONES"]["configurado"] is True
    assert diagnosticos["MORA"]["valido"] is False
    assert diagnosticos["MORA"]["configurado"] is False
    assert diagnosticos["PROYECCION"]["valido"] is False
    assert diagnosticos["PROYECCION"]["configurado"] is False
    assert cliente.llamadas == [("sheet-123", "FC!A:Z")]
