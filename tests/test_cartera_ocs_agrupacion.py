from decimal import Decimal

from app.motores.cartera_ocs.agrupacion import agrupar_operaciones_por_oc
from app.motores.cartera_ocs.importacion import RegistroCarteraEnCamino


def _registro(
    *,
    oc: str,
    cliente: str = "Cliente A",
    negociacion: str = "50/50",
    estado: str = "EN CAMINO",
    etapa: str = "EN CAMINO",
    documento: str = "BL-1",
    sku: str = "SKU-1",
    valor: str = "100.00",
    anticipo: str = "40.00",
    financiado: str = "60.00",
) -> RegistroCarteraEnCamino:
    return RegistroCarteraEnCamino(
        cliente=cliente,
        contacto="Contacto",
        producto="Producto",
        sku=sku,
        oc=oc,
        negociacion=negociacion,
        modo_transporte="MARITIMO",
        documento_transporte=documento,
        estado=estado,
        anio_oc=2026,
        eta="2026-10-01",
        etapa=etapa,
        valor=Decimal(valor),
        valor_anticipo=Decimal(anticipo),
        valor_financiado=Decimal(financiado),
        porcentaje_anticipo=Decimal("0.4"),
    )


def test_agrupa_lineas_de_una_oc_sin_elegir_un_estado_unico() -> None:
    grupos = agrupar_operaciones_por_oc(
        (
            _registro(
                oc="OC-1",
                estado="EN PRODUCCION",
                etapa="EN CAMINO",
                sku="SKU-1",
                valor="100.00",
                anticipo="40.00",
                financiado="60.00",
            ),
            _registro(
                oc="OC-1",
                estado="ENTREGADO",
                etapa="ENTREGADO",
                documento="BL-2",
                sku="SKU-2",
                valor="50.00",
                anticipo="20.00",
                financiado="30.00",
            ),
        )
    )

    assert len(grupos) == 1
    grupo = grupos[0]
    assert grupo.oc == "OC-1"
    assert len(grupo.lineas) == 2
    assert grupo.estados == ("EN PRODUCCION", "ENTREGADO")
    assert grupo.etapas == ("EN CAMINO", "ENTREGADO")
    assert grupo.documentos_transporte == ("BL-1", "BL-2")
    assert grupo.skus == ("SKU-1", "SKU-2")
    assert grupo.valor_ddp == Decimal("150.00")
    assert grupo.valor_anticipo == Decimal("60.00")
    assert grupo.valor_financiado == Decimal("90.00")


def test_preserva_multiples_clientes_y_negociaciones_como_composicion() -> None:
    grupo = agrupar_operaciones_por_oc(
        (
            _registro(oc="OC-2", cliente="Cliente A", negociacion="50/50"),
            _registro(oc="OC-2", cliente="Cliente B", negociacion="30/70"),
        )
    )[0]

    assert grupo.clientes == ("Cliente A", "Cliente B")
    assert grupo.negociaciones == ("50/50", "30/70")
    assert grupo.tiene_multiples_clientes is True
    assert grupo.tiene_multiples_negociaciones is True


def test_no_crea_una_oc_ficticia_para_lineas_sin_numero() -> None:
    grupos = agrupar_operaciones_por_oc(
        (
            _registro(oc=""),
            _registro(oc="OC-3"),
        )
    )

    assert [grupo.oc for grupo in grupos] == ["OC-3"]


def test_orden_de_grupos_y_valores_observados_es_determinista() -> None:
    grupos = agrupar_operaciones_por_oc(
        (
            _registro(oc="OC-B", estado="ZETA"),
            _registro(oc="OC-A", estado="BETA"),
            _registro(oc="OC-A", estado="ALFA"),
        )
    )

    assert [grupo.oc for grupo in grupos] == ["OC-A", "OC-B"]
    assert grupos[0].estados == ("BETA", "ALFA")
