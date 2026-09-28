from app.motores.cartera_ocs.importacion import normalizar_fila_cartera
from app.motores.cartera_ocs.validacion import validar_cartera_en_camino


def _registro(**cambios):
    fila = {
        "NOMBRE": "Cliente A",
        "CLIENTE": "Contacto A",
        "DESCRIPCION": "Producto",
        "SKU": "SKU-1",
        "NUMERO OC": "OC-1",
        "VALOR OCI (DDP)": 100,
        "DOCUMENTO DE TRANSPORTE": "DOC-1",
        "VALOR ANTICIPO": 40,
        "VALOR FINANCIADO": 60,
        "CARTERA": "EN CAMINO",
    }
    fila.update(cambios)
    registro = normalizar_fila_cartera(fila)
    assert registro is not None
    return registro


def test_detecta_linea_con_valor_pero_sin_numero_de_oc() -> None:
    resultado = validar_cartera_en_camino([
        _registro(**{"NUMERO OC": ""}),
    ])

    assert [caso.codigo for caso in resultado] == ["sin_numero_oc"]
    assert resultado[0].valor == 100


def test_detecta_repetida_por_oc_sku_documento_producto_y_valor() -> None:
    original = _registro()
    repetida = _registro()

    resultado = validar_cartera_en_camino([original, repetida])

    duplicados = [caso for caso in resultado if caso.codigo == "linea_repetida"]

    assert len(duplicados) == 1
    assert duplicados[0].cantidad == 1
    assert duplicados[0].valor == 100


def test_detecta_valor_oci_distinto_de_anticipo_mas_financiado() -> None:
    resultado = validar_cartera_en_camino([
        _registro(**{"VALOR ANTICIPO": 40, "VALOR FINANCIADO": 50}),
    ])

    descuadres = [caso for caso in resultado if caso.codigo == "valor_oci_descuadra"]

    assert len(descuadres) == 1
    assert descuadres[0].valor == 10


def test_detecta_valor_oci_cero_con_anticipo_o_financiado() -> None:
    resultado = validar_cartera_en_camino([
        _registro(
            **{
                "VALOR OCI (DDP)": 0,
                "VALOR ANTICIPO": 25,
                "VALOR FINANCIADO": 75,
            }
        ),
    ])

    ceros = [caso for caso in resultado if caso.codigo == "valor_oci_cero_con_componentes"]

    assert len(ceros) == 1
    assert ceros[0].valor == 100
