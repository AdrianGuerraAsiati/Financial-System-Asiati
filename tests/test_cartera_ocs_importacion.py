from decimal import Decimal

from app.motores.cartera_ocs.importacion import (
    normalizar_fila_cartera,
    parsear_numero_cartera,
)


def test_parsea_formatos_numericos_usados_por_el_tablero_actual() -> None:
    assert parsear_numero_cartera("USD 4.300,00") == Decimal("4300.00")
    assert parsear_numero_cartera("106,752") == Decimal("106.752")
    assert parsear_numero_cartera("0,3") == Decimal("0.3")
    assert parsear_numero_cartera("4,300.00") == Decimal("4300.00")
    assert parsear_numero_cartera("4.300") == Decimal("4300")


def test_normaliza_una_fila_de_cartera_en_camino_con_los_encabezados_actuales() -> None:
    fila = {
        "NOMBRE": "Cliente Principal",
        "CLIENTE": "Contacto comercial",
        "DESCRIPCION": "Producto A",
        "SKU": "SKU-01",
        "NUMERO OC": "OC-123",
        "TIPO DE NEGOCIACION": "50% anticipo / 50% saldo",
        "VALOR OCI (DDP)": "USD 4.300,00",
        "MODO TRANSPORTE": "Aéreo",
        "DOCUMENTO DE TRANSPORTE": "GUIA-9",
        "ESTADO": "En tránsito",
        "AÑO OC": 2026,
        "ETA": "2026-10-15",
        "ANTICIPO": "0,5",
        "VALOR ANTICIPO": "2.150,00",
        "VALOR FINANCIADO": "2.150,00",
        "CARTERA": "2. EN CAMINO",
    }

    registro = normalizar_fila_cartera(fila)

    assert registro is not None
    assert registro.cliente == "Cliente Principal"
    assert registro.contacto == "Contacto comercial"
    assert registro.oc == "OC-123"
    assert registro.etapa == "EN CAMINO"
    assert registro.valor == Decimal("4300.00")
    assert registro.valor_anticipo == Decimal("2150.00")
    assert registro.valor_financiado == Decimal("2150.00")
    assert registro.porcentaje_anticipo == Decimal("0.5")


def test_usa_cliente_como_respaldo_cuando_nombre_no_viene_informado() -> None:
    registro = normalizar_fila_cartera(
        {
            "NOMBRE": "",
            "CLIENTE": "Cliente Alterno",
            "NUMERO OC": "OC-77",
            "CARTERA": "",
        }
    )

    assert registro is not None
    assert registro.cliente == "Cliente Alterno"
    assert registro.contacto == "Cliente Alterno"
    assert registro.etapa == "Sin clasificar"


def test_excluye_filas_de_total_sin_sku() -> None:
    assert normalizar_fila_cartera(
        {
            "NOMBRE": "TOTAL",
            "CLIENTE": "",
            "SKU": "",
            "NUMERO OC": "",
        }
    ) is None


def test_decimal_preserva_precision_financiera() -> None:
    assert (
        parsear_numero_cartera("0,1")
        + parsear_numero_cartera("0,2")
        == Decimal("0.3")
    )
