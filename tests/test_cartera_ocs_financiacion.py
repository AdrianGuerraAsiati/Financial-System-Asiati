from datetime import date

from app.motores.cartera_ocs.financiacion import (
    OperacionFinanciada,
    generar_condicion_pago,
    parsear_tipo_negociacion,
)


def test_parsea_dos_porcentajes_y_toma_el_segundo_como_saldo() -> None:
    condicion = parsear_tipo_negociacion(
        "50% anticipo / 50% pago a 30 días"
    )

    assert condicion.porcentaje_saldo == 0.5
    assert condicion.dias_plazo == 30


def test_con_un_porcentaje_menor_a_100_calcula_el_saldo_restante() -> None:
    condicion = parsear_tipo_negociacion(
        "30% anticipo, pago a 45 dias"
    )

    assert condicion.porcentaje_saldo == 0.7
    assert condicion.dias_plazo == 45


def test_pago_a_la_entrega_tiene_cero_dias_de_plazo() -> None:
    condicion = parsear_tipo_negociacion(
        "50% anticipo / 50% a la entrega"
    )

    assert condicion.porcentaje_saldo == 0.5
    assert condicion.dias_plazo == 0


def test_genera_condicion_de_pago_desde_una_operacion_financiada() -> None:
    operacion = OperacionFinanciada(
        oc="OC-123",
        cliente="Cliente A",
        pais="COLOMBIA",
        valor_ddp=10000,
        tipo_negociacion="50% anticipo / 50% pago a 30 días",
        fecha_entrega=date(2026, 9, 10),
        comercial="COMERCIAL A",
    )

    condicion = generar_condicion_pago(operacion)

    assert condicion.oc == "OC-123"
    assert condicion.cliente == "Cliente A"
    assert condicion.porcentaje_saldo == 0.5
    assert condicion.dias_plazo == 30
    assert condicion.fecha_pago_esperada == date(2026, 10, 10)
    assert condicion.monto_original == 5000


def test_el_calculo_no_aplica_abonos_ni_comprobantes_en_esta_etapa() -> None:
    operacion = OperacionFinanciada(
        oc="OC-500",
        cliente="Cliente B",
        pais="CHILE",
        valor_ddp=2500,
        tipo_negociacion="40% anticipo / 60% a la entrega",
        fecha_entrega=date(2026, 9, 20),
        comercial="COMERCIAL B",
    )

    condicion = generar_condicion_pago(operacion)

    assert condicion.monto_original == 1500
    assert condicion.fecha_pago_esperada == date(2026, 9, 20)
