from app.motores.compras_supply_chain.agrupacion import agrupar_ocs
from app.motores.compras_supply_chain.calidad import evaluar_calidad_lineas
from app.motores.compras_supply_chain.contrato import analizar_encabezados
from app.motores.compras_supply_chain.normalizacion import normalizar_fila_compra


def _linea(fila: dict[str, object], *, pais: str = "CO", numero: int = 2):
    return normalizar_fila_compra(fila, pais=pais, fila_fuente=numero)


def test_schema_contract_detects_missing_and_duplicate_headers() -> None:
    diagnostico = analizar_encabezados(
        ["NUMERO OC", "CLIENTE", "PROVEEDOR", "ESTADO", "ESTADO", "OTRA"],
        pais="CO",
        rango="CO!A:Z",
        filas_datos=10,
    )

    assert diagnostico.valido is False
    assert diagnostico.encabezados_duplicados == ("ESTADO",)
    assert "modo_transporte" in diagnostico.campos_criticos_faltantes
    assert diagnostico.encabezados_no_consumidos == ("OTRA",)


def test_quality_rules_are_observational_and_keep_source_coordinates() -> None:
    lineas = (
        _linea(
            {
                "NUMERO OC": "N/A",
                "CLIENTE": "",
                "PROVEEDOR": "",
                "ESTADO": "EN OTM",
                "MODO TRANSPORTE": "DRON",
                "FECHA ENTREGA EN BODEGA BOGOTA": "2026-09-10",
            },
            numero=8,
        ),
    )

    resultados = {r.codigo: r for r in evaluar_calidad_lineas(lineas)}

    assert resultados["OC_NO_IDENTIFICADA"].cantidad == 1
    assert resultados["CLIENTE_VACIO"].cantidad == 1
    assert resultados["PROVEEDOR_VACIO"].cantidad == 1
    assert resultados["ESTADO_POR_DEFINIR"].cantidad == 1
    assert resultados["TRANSPORTE_NO_CATALOGADO"].cantidad == 1
    assert resultados["ENTREGA_CON_ESTADO_NO_RECIBIDO"].cantidad == 1
    assert resultados["OC_NO_IDENTIFICADA"].muestras[0].fila_fuente == 8


def test_grouping_never_merges_unidentified_orders_and_exposes_mixed_dimensions() -> None:
    lineas = (
        _linea(
            {
                "NUMERO OC": "OC-1",
                "CLIENTE": "A",
                "PROVEEDOR": "P1",
                "ESTADO": "EN PRODUCCION",
                "MODO TRANSPORTE": "MARITIMO",
            },
            numero=2,
        ),
        _linea(
            {
                "NUMERO OC": "OC-1",
                "CLIENTE": "A",
                "PROVEEDOR": "P2",
                "ESTADO": "ENVIADO A DESTINO",
                "MODO TRANSPORTE": "AEREO",
            },
            numero=3,
        ),
        _linea(
            {
                "NUMERO OC": "N/A",
                "CLIENTE": "B",
                "PROVEEDOR": "P3",
                "ESTADO": "ENTREGADO",
                "MODO TRANSPORTE": "MUESTRA",
            },
            numero=4,
        ),
        _linea(
            {
                "NUMERO OC": "N/A",
                "CLIENTE": "C",
                "PROVEEDOR": "P4",
                "ESTADO": "ENTREGADO",
                "MODO TRANSPORTE": "MUESTRA",
            },
            numero=5,
        ),
    )

    resumenes = agrupar_ocs(lineas)
    identificada = next(r for r in resumenes if r.numero_oc == "OC-1")

    assert identificada.lineas == 2
    assert identificada.estado_mixto is True
    assert identificada.proveedor_mixto is True
    assert identificada.transporte_mixto is True
    assert len([r for r in resumenes if not r.oc_identificada]) == 2
