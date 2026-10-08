from decimal import Decimal

import pytest

from app.motores.cartera_ocs.cruce_compras import (
    LineaFuente,
    comparar_cartera_con_compras,
    resumir_cruce,
)


def linea(**cambios):
    datos = dict(
        fuente="FC", fila=2, oc="GM-123", sku="W 100-01",
        cliente="Cliente A", documento="BL-001", estado="ENVIADO A DESTINO",
        descripcion="Bolsa azul", pais="", ddp=Decimal("100.00"),
    )
    datos.update(cambios)
    return LineaFuente(**datos)


def compra(**cambios):
    return linea(fuente="INFORME CLIENTES (CO)", fila=99, pais="CO", **cambios)


def test_coincidencia_por_atributos_y_ddp_con_procedencia():
    resultado, = comparar_cartera_con_compras([linea()], [compra()])
    assert resultado.estado == "COINCIDE"
    assert resultado.referencia_fuente == "INFORME CLIENTES (CO)"
    assert resultado.referencia_fila == 99


def test_normalizacion_diagnostica_no_se_trata_como_id_maestro():
    resultado, = comparar_cartera_con_compras(
        [linea(oc="GM 123", sku="W10001", cliente="Clíente A")],
        [compra()],
    )
    assert resultado.estado == "COINCIDE"


def test_pais_explicito_evitar_asignaciones_entre_empresas():
    resultado, = comparar_cartera_con_compras(
        [linea(pais="ECUADOR")], [compra()]
    )
    assert resultado.estado == "ATRIBUTOS_DIFERENTES"
    assert resultado.referencia_fila is None


def test_misma_oc_y_sku_se_desambigua_por_documento_y_descripcion():
    registros = [
        compra(documento="BL-002", descripcion="Bolsa roja", fila=8),
        compra(documento="BL-001", descripcion="Bolsa azul", fila=9),
    ]
    resultado, = comparar_cartera_con_compras([linea()], registros)
    assert resultado.estado == "COINCIDE"
    assert resultado.referencia_fila == 9


def test_duplicados_indistinguibles_nunca_eligen_fila_al_azar():
    resultado, = comparar_cartera_con_compras(
        [linea()], [compra(fila=8), compra(fila=9)]
    )
    assert resultado.estado == "AMBIGUO"
    assert resultado.candidatos == 2
    assert resultado.referencia_fila is None


def test_monto_desconocido_no_se_rellena_desde_compras():
    resultado, = comparar_cartera_con_compras(
        [linea(ddp=None)], [compra()]
    )
    assert resultado.estado == "MONTO_SIN_EVIDENCIA"
    assert resultado.referencia_fila is None


def test_monto_de_compras_desconocido_no_se_trata_como_cero():
    resultado, = comparar_cartera_con_compras(
        [linea()], [compra(ddp=None)]
    )
    assert resultado.estado == "MONTO_SIN_EVIDENCIA"


def test_monto_distinto_se_reporta_sin_modificar_ninguna_fuente():
    fila = linea()
    compra_diferente = compra(ddp=Decimal("200"))
    resultado, = comparar_cartera_con_compras([fila], [compra_diferente])
    assert resultado.estado == "MONTO_DIFERENTE"
    assert fila.ddp == Decimal("100.00")
    assert compra_diferente.ddp == Decimal("200")


@pytest.mark.parametrize("oc,sku", [
    ("N/A", "W100-01"), ("GM123", "N/A"), ("", "SKU"),
])
def test_clave_incompleta_no_se_usa_para_conciliar(oc, sku):
    resultado, = comparar_cartera_con_compras(
        [linea(oc=oc, sku=sku)], [compra(oc=oc, sku=sku)]
    )
    assert resultado.estado == "CLAVE_INCOMPLETA"


def test_linea_que_no_existe_en_compras():
    resultado, = comparar_cartera_con_compras(
        [linea(oc="GM999")], [compra()]
    )
    assert resultado.estado == "SIN_COINCIDENCIA"


def test_otros_estados_y_resumen_agregado_sin_montos():
    resultados = comparar_cartera_con_compras(
        [linea(), linea(fila=3, ddp=None)],
        [compra()],
    )
    assert resumir_cruce(resultados) == {
        "COINCIDE": 1,
        "MONTO_SIN_EVIDENCIA": 1,
    }


def test_rechaza_float_y_nan_para_evidencia_monetaria():
    with pytest.raises(ValueError, match="Decimal finito"):
        comparar_cartera_con_compras([linea(ddp=100.0)], [compra()])
    with pytest.raises(ValueError, match="Decimal finito"):
        comparar_cartera_con_compras(
            [linea()], [compra(ddp=Decimal("NaN"))]
        )
