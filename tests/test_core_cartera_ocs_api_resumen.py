from datetime import date
from decimal import Decimal

from app.main import app
from app.motores.cartera_ocs.api import (
    obtener_fuente_mora,
    obtener_fuente_operaciones,
    obtener_fuente_proyeccion,
)
from app.motores.cartera_ocs.importacion import RegistroCarteraEnCamino
from app.motores.cartera_ocs.mora import RegistroCarteraMora
from app.motores.cartera_ocs.proyeccion import RegistroProyeccionPago
from tests.apoyo_auth import cliente_superadmin


class FuenteOperacionesFake:
    def listar(self, *, empresa_id: int):
        assert empresa_id == 3
        return (
            RegistroCarteraEnCamino(
                cliente="Cliente",
                contacto="",
                producto="",
                sku="SKU-1",
                oc="OC-1",
                negociacion="",
                modo_transporte="",
                documento_transporte="",
                estado="",
                anio_oc=2026,
                eta="",
                etapa="EN CAMINO",
                valor=Decimal("100.00"),
                valor_anticipo=Decimal("40.00"),
                valor_financiado=Decimal("60.00"),
                porcentaje_anticipo=Decimal("0.4"),
            ),
        )


class FuenteMoraFake:
    def listar(self, *, empresa_id: int):
        assert empresa_id == 3
        return (
            RegistroCarteraMora(
                cliente="Cliente",
                empresa="ASIATI",
                monto=Decimal("25.00"),
                observacion="",
                estado="MORA",
            ),
        )


class FuenteProyeccionFake:
    def listar(self, *, empresa_id: int):
        assert empresa_id == 3
        return (
            RegistroProyeccionPago(
                cliente="Cliente",
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
                fecha=date(2026, 10, 15),
                monto=Decimal("400.00"),
                mes="2026-10",
            ),
        )


def test_api_expone_resumen_descriptivo_de_operaciones() -> None:
    app.dependency_overrides[obtener_fuente_operaciones] = lambda: FuenteOperacionesFake()
    try:
        response = cliente_superadmin().get(
            "/api/v1/cartera/operaciones/resumen?empresa_id=3"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "lineas": 1,
        "ocs": 1,
        "clientes": 1,
        "valor_ddp": "100.00",
        "valor_anticipo": "40.00",
        "valor_financiado": "60.00",
        "por_etapa": [
            {"clave": "EN CAMINO", "registros": 1, "monto": "100.00"},
        ],
        "nota": "Resumen descriptivo de las líneas observadas; no define saldo de cartera.",
    }


def test_api_expone_resumen_descriptivo_de_mora() -> None:
    app.dependency_overrides[obtener_fuente_mora] = lambda: FuenteMoraFake()
    try:
        response = cliente_superadmin().get(
            "/api/v1/cartera/mora/resumen?empresa_id=3"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["registros"] == 1
    assert body["clientes"] == 1
    assert body["monto"] == "25.00"
    assert body["por_estado"] == [
        {"clave": "MORA", "registros": 1, "monto": "25.00"},
    ]
    assert body["por_empresa"] == [
        {"clave": "ASIATI", "registros": 1, "monto": "25.00"},
    ]


def test_api_expone_resumen_descriptivo_de_proyeccion() -> None:
    app.dependency_overrides[obtener_fuente_proyeccion] = lambda: FuenteProyeccionFake()
    try:
        response = cliente_superadmin().get(
            "/api/v1/cartera/proyeccion/resumen?empresa_id=3"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["registros"] == 1
    assert body["ocs"] == 1
    assert body["clientes"] == 1
    assert body["monto_esperado"] == "400.00"
    assert body["valor_oc"] == "1000.00"
    assert body["por_mes"] == [
        {"clave": "2026-10", "registros": 1, "monto": "400.00"},
    ]
    assert body["por_comercial"] == [
        {"clave": "ANA", "registros": 1, "monto": "400.00"},
    ]
