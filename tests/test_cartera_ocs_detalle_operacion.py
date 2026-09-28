import pytest

from app.motores.cartera_ocs.consultas import (
    OperacionNoEncontradaError,
    obtener_detalle_operacion,
)
from app.motores.cartera_ocs.importacion import RegistroCarteraEnCamino


def _registro(oc: str, sku: str, valor: float) -> RegistroCarteraEnCamino:
    return RegistroCarteraEnCamino(
        cliente="Cliente A",
        contacto="Contacto A",
        producto=f"Producto {sku}",
        sku=sku,
        oc=oc,
        negociacion="Crédito",
        modo_transporte="Marítimo",
        documento_transporte="BL-1",
        estado="Entregado",
        anio_oc=2026,
        eta="2026-10-01",
        etapa="EN CAMINO",
        valor=valor,
        valor_anticipo=0,
        valor_financiado=valor,
        porcentaje_anticipo=0,
    )


class FuenteFake:
    def listar(self, *, empresa_id: int):
        assert empresa_id == 9
        return (
            _registro("OC-1", "SKU-A", 1000),
            _registro("OC-1", "SKU-B", 2000),
            _registro("OC-2", "SKU-C", 3000),
        )


def test_detail_preserves_all_lines_for_same_oc() -> None:
    detalle = obtener_detalle_operacion(
        FuenteFake(),
        empresa_id=9,
        oc="OC-1",
    )

    assert detalle.oc == "OC-1"
    assert [linea.sku for linea in detalle.lineas] == ["SKU-A", "SKU-B"]
    assert [linea.valor for linea in detalle.lineas] == [1000, 2000]


def test_missing_oc_is_explicit() -> None:
    with pytest.raises(OperacionNoEncontradaError):
        obtener_detalle_operacion(
            FuenteFake(),
            empresa_id=9,
            oc="OC-X",
        )
