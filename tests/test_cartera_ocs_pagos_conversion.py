from datetime import date
from decimal import Decimal

import pytest

from app.motores.cartera_ocs.pagos_conversion import (
    TasaHistoricaPago,
    convertir_pago_referencia,
    seleccionar_tasa_pago,
)


def historico_sintetico():
    return [
        TasaHistoricaPago(date(2026, 1, 2), Decimal("3800"), Decimal("950")),
        TasaHistoricaPago(date(2026, 1, 5), Decimal("4000"), Decimal("1000")),
    ]


def test_pago_usd_a_cop_consulta_tasa_anterior_si_no_hay_del_dia():
    pago = convertir_pago_referencia(
        fecha_pago=date(2026, 1, 3),
        divisa="usd",
        monto=Decimal("100.00"),
        historico=historico_sintetico(),
    )
    assert pago.fecha_tasa == date(2026, 1, 2)
    assert pago.cop_referencia == Decimal("380000.00")
    assert pago.usd_referencia == Decimal("100.00")


def test_pago_cop_a_usd_usa_tasa_de_fecha_exacta():
    pago = convertir_pago_referencia(
        fecha_pago=date(2026, 1, 5),
        divisa="COP",
        monto=Decimal("400000.00"),
        historico=historico_sintetico(),
    )
    assert pago.fecha_tasa == date(2026, 1, 5)
    assert pago.cop_referencia == Decimal("400000.00")
    assert pago.usd_referencia == Decimal("100.00")


def test_pago_clp_convierte_a_usd_y_luego_cop():
    pago = convertir_pago_referencia(
        fecha_pago=date(2026, 1, 3),
        divisa="CLP",
        monto=Decimal("95000.00"),
        historico=historico_sintetico(),
    )
    assert pago.usd_referencia == Decimal("100.00")
    assert pago.cop_referencia == Decimal("380000.00")


def test_sin_tasa_anterior_no_se_inventa_conversion():
    with pytest.raises(ValueError, match="No existe tasa"):
        seleccionar_tasa_pago(date(2026, 1, 1), historico_sintetico())


def test_tasas_contradictorias_del_mismo_dia_se_rechazan():
    tasas = [
        TasaHistoricaPago(date(2026, 1, 2), Decimal("3800"), Decimal("950")),
        TasaHistoricaPago(date(2026, 1, 2), Decimal("3801"), Decimal("950")),
    ]
    with pytest.raises(ValueError, match="contradictorias"):
        seleccionar_tasa_pago(date(2026, 1, 3), tasas)


@pytest.mark.parametrize("divisa", ["EUR", "", "MXN"])
def test_divisa_no_soportada_falla_explicita(divisa):
    with pytest.raises(ValueError, match="Divisa no soportada"):
        convertir_pago_referencia(
            fecha_pago=date(2026, 1, 3),
            divisa=divisa,
            monto=Decimal("100"),
            historico=historico_sintetico(),
        )


def test_trm_cero_no_produce_division_por_cero():
    with pytest.raises(ValueError, match="TRM USD/COP invalida"):
        convertir_pago_referencia(
            fecha_pago=date(2026, 1, 3),
            divisa="COP",
            monto=Decimal("100"),
            historico=[
                TasaHistoricaPago(date(2026, 1, 2), Decimal("0"), Decimal("950"))
            ],
        )


def test_monto_float_no_permitido_para_conversion_financiera():
    with pytest.raises(ValueError, match="Decimal finito"):
        convertir_pago_referencia(
            fecha_pago=date(2026, 1, 3),
            divisa="USD",
            monto=100.0,
            historico=historico_sintetico(),
        )
