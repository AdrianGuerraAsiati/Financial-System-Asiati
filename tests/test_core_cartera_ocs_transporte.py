from datetime import date, datetime
from decimal import Decimal

from app.motores.cartera_ocs.fechas import parsear_fecha_cartera
from app.motores.cartera_ocs.importacion import RegistroCarteraEnCamino
from app.motores.cartera_ocs.transporte import (
    ESTADO_EN_CAMINO,
    ESTADO_SIN_DOCUMENTO,
    ESTADO_SIN_ETA,
    ESTADO_VENCIDO,
    agrupar_documentos_transporte,
)


def _registro(
    *,
    documento: str,
    eta: object,
    oc: str,
    valor: str = "100.00",
) -> RegistroCarteraEnCamino:
    return RegistroCarteraEnCamino(
        cliente="Cliente",
        contacto="",
        producto="Producto",
        sku=f"SKU-{oc}",
        oc=oc,
        negociacion="",
        modo_transporte="Marítimo",
        documento_transporte=documento,
        estado="",
        anio_oc=2026,
        eta=eta,
        etapa="EN CAMINO",
        valor=Decimal(valor),
        valor_anticipo=Decimal("40.00"),
        valor_financiado=Decimal(valor) - Decimal("40.00"),
        porcentaje_anticipo=Decimal("0.4"),
    )


def test_parser_fechas_preserva_formatos_observados_en_legado() -> None:
    assert parsear_fecha_cartera("2026-09-30") == date(2026, 9, 30)
    assert parsear_fecha_cartera("30/09/2026") == date(2026, 9, 30)
    assert parsear_fecha_cartera("30-09-2026") == date(2026, 9, 30)
    assert parsear_fecha_cartera("Date(2026,8,30)") == date(2026, 9, 30)
    assert parsear_fecha_cartera(datetime(2026, 9, 30, 12, 0)) == date(2026, 9, 30)
    assert parsear_fecha_cartera("31/02/2026") is None
    assert parsear_fecha_cartera("") is None


def test_agrupa_documentos_y_conserva_rango_eta_y_montos() -> None:
    documentos = agrupar_documentos_transporte(
        (
            _registro(
                documento="BL-1",
                eta="28/09/2026",
                oc="OC-1",
                valor="100.00",
            ),
            _registro(
                documento="BL-1",
                eta="02/10/2026",
                oc="OC-2",
                valor="250.00",
            ),
        ),
        fecha_corte=date(2026, 9, 30),
    )

    assert len(documentos) == 1
    documento = documentos[0]
    assert documento.documento == "BL-1"
    assert documento.ocs == ("OC-1", "OC-2")
    assert documento.lineas == 2
    assert documento.valor_ddp == Decimal("350.00")
    assert documento.eta_min == date(2026, 9, 28)
    assert documento.eta_max == date(2026, 10, 2)
    assert documento.estado == ESTADO_VENCIDO


def test_clasificacion_eta_replica_corte_estricto_del_legado() -> None:
    documentos = agrupar_documentos_transporte(
        (
            _registro(documento="BL-V", eta="29/09/2026", oc="OC-V"),
            _registro(documento="BL-H", eta="30/09/2026", oc="OC-H"),
            _registro(documento="BL-F", eta="01/10/2026", oc="OC-F"),
            _registro(documento="BL-S", eta="", oc="OC-S"),
            _registro(documento="", eta="29/09/2026", oc="OC-N"),
        ),
        fecha_corte=date(2026, 9, 30),
    )
    por_documento = {item.documento: item.estado for item in documentos}

    assert por_documento["BL-V"] == ESTADO_VENCIDO
    assert por_documento["BL-H"] == ESTADO_EN_CAMINO
    assert por_documento["BL-F"] == ESTADO_EN_CAMINO
    assert por_documento["BL-S"] == ESTADO_SIN_ETA
    assert por_documento[""] == ESTADO_SIN_DOCUMENTO
