from datetime import date
from decimal import Decimal

from app.motores.cartera_ocs.alertas import (
    detectar_alertas_cartera,
    detectar_concentracion_mora,
    detectar_mora_con_operaciones_en_camino,
)
from app.motores.cartera_ocs.importacion import RegistroCarteraEnCamino
from app.motores.cartera_ocs.mora import RegistroCarteraMora
from app.motores.cartera_ocs.proyeccion import RegistroProyeccionPago


def _mora(
    cliente: str,
    monto: str,
    *,
    estado: str = "MORA",
    empresa: str = "",
) -> RegistroCarteraMora:
    return RegistroCarteraMora(
        cliente=cliente,
        empresa=empresa,
        monto=Decimal(monto),
        observacion="",
        estado=estado,
    )


def _operacion(cliente: str, valor: str, oc: str) -> RegistroCarteraEnCamino:
    return RegistroCarteraEnCamino(
        cliente=cliente,
        contacto="",
        producto="",
        sku=f"SKU-{oc}",
        oc=oc,
        negociacion="",
        modo_transporte="",
        documento_transporte=f"BL-{oc}",
        estado="",
        anio_oc=2026,
        eta="2026-10-01",
        etapa="EN CAMINO",
        valor=Decimal(valor),
        valor_anticipo=Decimal("0"),
        valor_financiado=Decimal(valor),
        porcentaje_anticipo=Decimal("0"),
    )


def _proyeccion(
    cliente: str,
    monto: str,
    fecha: date,
    oc: str,
) -> RegistroProyeccionPago:
    return RegistroProyeccionPago(
        cliente=cliente,
        contacto="",
        producto="",
        sku="",
        oc=oc,
        pais="CO",
        estado="",
        documento_transporte="",
        dias=Decimal("0"),
        valor_oc=Decimal(monto),
        comercial="ANA",
        fecha=fecha,
        monto=Decimal(monto),
        mes=f"{fecha.year:04d}-{fecha.month:02d}",
    )


def test_cruce_mora_transito_es_conservador_y_no_usa_substrings() -> None:
    alerta = detectar_mora_con_operaciones_en_camino(
        (_mora("Cliente Á", "25.00"),),
        (
            _operacion("CLIENTE A", "100.00", "OC-1"),
            _operacion("CLIENTE A HOLDINGS", "150.00", "OC-2"),
        ),
    )

    assert alerta is not None
    assert alerta.codigo == "CARTERA_MORA_CON_TRANSITO"
    assert alerta.evidencia["valor_transito"] == Decimal("100.00")
    assert alerta.evidencia["clientes"][0]["ocs"] == 1
    assert alerta.evidencia["metodo_matching"] == "nombre_normalizado_exacto"


def test_concentracion_mora_conserva_umbral_heredado_estricto() -> None:
    alerta = detectar_concentracion_mora(
        (
            _mora("A", "60"),
            _mora("B", "20"),
            _mora("C", "10"),
            _mora("D", "10"),
        )
    )
    assert alerta is not None
    assert alerta.evidencia["participacion"] == Decimal("0.9")
    assert alerta.evidencia["umbral_heredado"] == Decimal("0.50")

    sin_alerta = detectar_concentracion_mora(
        (
            _mora("A", "25"),
            _mora("B", "25"),
            _mora("C", "0"),
            _mora("D", "50"),
        ),
        top_n=1,
    )
    assert sin_alerta is None


def test_alertas_portadas_solo_dependientes_de_fc_mora_y_proyeccion() -> None:
    alertas = detectar_alertas_cartera(
        mora=(
            _mora("Cliente A", "60"),
            _mora("Cliente B", "20"),
            _mora("Cliente C", "10"),
            _mora("Cliente D", "10"),
            _mora("Cliente E", "5", estado="SALDADO"),
        ),
        operaciones=(
            _operacion("Cliente A", "200", "OC-1"),
        ),
        proyecciones=(
            _proyeccion("Cliente A", "40", date(2026, 10, 15), "OC-P1"),
            _proyeccion("Cliente B", "30", date(2026, 10, 15), "OC-P2"),
            _proyeccion("Cliente C", "30", date(2026, 10, 20), "OC-P3"),
        ),
        mes="2026-10",
    )

    por_codigo = {alerta.codigo: alerta for alerta in alertas}
    assert set(por_codigo) == {
        "CARTERA_MORA_CON_TRANSITO",
        "CARTERA_MORA_CONCENTRADA",
        "CARTERA_PROYECCION_CONCENTRADA_CLIENTE",
        "CARTERA_PROYECCION_CONCENTRADA_FECHA",
        "CARTERA_CLIENTES_SALDADOS",
    }
    assert (
        por_codigo["CARTERA_PROYECCION_CONCENTRADA_CLIENTE"]
        .evidencia["participacion"]
        == Decimal("0.4")
    )
    assert (
        por_codigo["CARTERA_PROYECCION_CONCENTRADA_FECHA"]
        .evidencia["participacion"]
        == Decimal("0.7")
    )
    assert (
        por_codigo["CARTERA_CLIENTES_SALDADOS"]
        .evidencia["monto"]
        == Decimal("5")
    )
