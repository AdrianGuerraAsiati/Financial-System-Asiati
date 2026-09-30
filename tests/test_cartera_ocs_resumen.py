from datetime import date
from decimal import Decimal

from app.motores.cartera_ocs.importacion import RegistroCarteraEnCamino
from app.motores.cartera_ocs.mora import RegistroCarteraMora
from app.motores.cartera_ocs.proyeccion import RegistroProyeccionPago
from app.motores.cartera_ocs.resumen import (
    resumir_mora,
    resumir_operaciones,
    resumir_proyeccion,
)


def _operacion(
    *,
    oc: str,
    cliente: str,
    etapa: str,
    valor: str,
    anticipo: str,
    financiado: str,
) -> RegistroCarteraEnCamino:
    return RegistroCarteraEnCamino(
        cliente=cliente,
        contacto="",
        producto="Producto",
        sku="SKU",
        oc=oc,
        negociacion="",
        modo_transporte="",
        documento_transporte="",
        estado="",
        anio_oc=2026,
        eta="",
        etapa=etapa,
        valor=Decimal(valor),
        valor_anticipo=Decimal(anticipo),
        valor_financiado=Decimal(financiado),
        porcentaje_anticipo=Decimal("0"),
    )


def test_resumen_operaciones_es_descriptivo_y_no_colapsa_lineas_por_oc() -> None:
    resumen = resumir_operaciones(
        (
            _operacion(
                oc="OC-1",
                cliente="Cliente A",
                etapa="EN CAMINO",
                valor="100.00",
                anticipo="40.00",
                financiado="60.00",
            ),
            _operacion(
                oc="OC-1",
                cliente="Cliente A",
                etapa="EN CAMINO",
                valor="50.00",
                anticipo="20.00",
                financiado="30.00",
            ),
            _operacion(
                oc="OC-2",
                cliente="Cliente B",
                etapa="ENTREGADO",
                valor="200.00",
                anticipo="100.00",
                financiado="100.00",
            ),
        )
    )

    assert resumen.lineas == 3
    assert resumen.ocs == 2
    assert resumen.clientes == 2
    assert resumen.valor_ddp == Decimal("350.00")
    assert resumen.valor_anticipo == Decimal("160.00")
    assert resumen.valor_financiado == Decimal("190.00")
    assert [(item.clave, item.registros, item.monto) for item in resumen.por_etapa] == [
        ("EN CAMINO", 2, Decimal("150.00")),
        ("ENTREGADO", 1, Decimal("200.00")),
    ]


def test_resumen_operaciones_no_inventa_oc_para_filas_sin_numero() -> None:
    resumen = resumir_operaciones(
        (
            _operacion(
                oc="",
                cliente="Cliente A",
                etapa="Sin clasificar",
                valor="10.00",
                anticipo="0",
                financiado="0",
            ),
        )
    )

    assert resumen.lineas == 1
    assert resumen.ocs == 0
    assert resumen.valor_ddp == Decimal("10.00")


def test_resumen_mora_agrupa_por_estado_y_empresa_sin_mezclar_totales() -> None:
    resumen = resumir_mora(
        (
            RegistroCarteraMora(
                cliente="Cliente A",
                empresa="ASIATI CO",
                monto=Decimal("100.00"),
                observacion="",
                estado="MORA",
            ),
            RegistroCarteraMora(
                cliente="Cliente B",
                empresa="ASIATI CO",
                monto=Decimal("50.00"),
                observacion="",
                estado="ACUERDO",
            ),
            RegistroCarteraMora(
                cliente="Cliente A",
                empresa="ASIATI EC",
                monto=Decimal("25.00"),
                observacion="",
                estado="MORA",
            ),
        )
    )

    assert resumen.registros == 3
    assert resumen.clientes == 2
    assert resumen.monto == Decimal("175.00")
    assert [(item.clave, item.registros, item.monto) for item in resumen.por_estado] == [
        ("ACUERDO", 1, Decimal("50.00")),
        ("MORA", 2, Decimal("125.00")),
    ]
    assert [(item.clave, item.registros, item.monto) for item in resumen.por_empresa] == [
        ("ASIATI CO", 2, Decimal("150.00")),
        ("ASIATI EC", 1, Decimal("25.00")),
    ]


def test_resumen_proyeccion_conserva_monto_esperado_separado_de_valor_oc() -> None:
    resumen = resumir_proyeccion(
        (
            RegistroProyeccionPago(
                cliente="Cliente A",
                contacto="",
                producto="",
                sku="",
                oc="OC-1",
                pais="CO",
                estado="",
                documento_transporte="",
                dias=Decimal("30"),
                valor_oc=Decimal("1000.00"),
                comercial="ANA",
                fecha=date(2026, 10, 5),
                monto=Decimal("400.00"),
                mes="2026-10",
            ),
            RegistroProyeccionPago(
                cliente="Cliente B",
                contacto="",
                producto="",
                sku="",
                oc="OC-2",
                pais="EC",
                estado="",
                documento_transporte="",
                dias=Decimal("45"),
                valor_oc=Decimal("800.00"),
                comercial="ANA",
                fecha=date(2026, 11, 5),
                monto=Decimal("300.00"),
                mes="2026-11",
            ),
        )
    )

    assert resumen.registros == 2
    assert resumen.ocs == 2
    assert resumen.clientes == 2
    assert resumen.monto_esperado == Decimal("700.00")
    assert resumen.valor_oc == Decimal("1800.00")
    assert [(item.clave, item.registros, item.monto) for item in resumen.por_mes] == [
        ("2026-10", 1, Decimal("400.00")),
        ("2026-11", 1, Decimal("300.00")),
    ]
    assert [(item.clave, item.registros, item.monto) for item in resumen.por_comercial] == [
        ("ANA", 2, Decimal("700.00")),
    ]
