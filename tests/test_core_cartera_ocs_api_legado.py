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
                cliente="Cliente A",
                contacto="",
                producto="",
                sku="SKU-1",
                oc="OC-1",
                negociacion="",
                modo_transporte="Marítimo",
                documento_transporte="BL-1",
                estado="",
                anio_oc=2026,
                eta="2026-09-29",
                etapa="EN CAMINO",
                valor=Decimal("200.00"),
                valor_anticipo=Decimal("80.00"),
                valor_financiado=Decimal("120.00"),
                porcentaje_anticipo=Decimal("0.4"),
            ),
        )


class FuenteMoraFake:
    def listar(self, *, empresa_id: int):
        assert empresa_id == 3
        return (
            RegistroCarteraMora(
                cliente="Cliente A",
                empresa="",
                monto=Decimal("60.00"),
                observacion="",
                estado="MORA",
            ),
            RegistroCarteraMora(
                cliente="Cliente B",
                empresa="",
                monto=Decimal("20.00"),
                observacion="",
                estado="MORA",
            ),
            RegistroCarteraMora(
                cliente="Cliente C",
                empresa="",
                monto=Decimal("10.00"),
                observacion="",
                estado="MORA",
            ),
            RegistroCarteraMora(
                cliente="Cliente D",
                empresa="",
                monto=Decimal("10.00"),
                observacion="",
                estado="MORA",
            ),
        )


class FuenteProyeccionFake:
    def listar(self, *, empresa_id: int):
        assert empresa_id == 3

        def item(cliente: str, monto: str, dia: int, oc: str):
            fecha = date(2026, 10, dia)
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
                mes="2026-10",
            )

        return (
            item("Cliente A", "40.00", 15, "OC-P1"),
            item("Cliente B", "30.00", 15, "OC-P2"),
            item("Cliente C", "30.00", 20, "OC-P3"),
        )


def _activar_fuentes() -> None:
    app.dependency_overrides[obtener_fuente_operaciones] = (
        lambda: FuenteOperacionesFake()
    )
    app.dependency_overrides[obtener_fuente_mora] = lambda: FuenteMoraFake()
    app.dependency_overrides[obtener_fuente_proyeccion] = (
        lambda: FuenteProyeccionFake()
    )


def test_api_expone_diagnostico_de_transporte_heredado() -> None:
    _activar_fuentes()
    try:
        response = cliente_superadmin().get(
            "/api/v1/cartera/transportes"
            "?empresa_id=3&fecha_corte=2026-09-30"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["fecha_corte"] == "2026-09-30"
    assert body["documentos"] == 1
    assert body["items"][0]["documento"] == "BL-1"
    assert body["items"][0]["estado"] == "VENCIDO"
    assert body["items"][0]["valor_ddp"] == "200.00"
    assert body["items"][0]["eta_min"] == "2026-09-29"


def test_api_expone_alertas_legadas_sin_persistir_hallazgos() -> None:
    _activar_fuentes()
    try:
        response = cliente_superadmin().get(
            "/api/v1/cartera/alertas?empresa_id=3&mes=2026-10"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    codigos = {item["codigo"] for item in body["items"]}
    assert body["mes"] == "2026-10"
    assert body["persistidas"] is False
    assert {
        "CARTERA_MORA_CON_TRANSITO",
        "CARTERA_MORA_CONCENTRADA",
        "CARTERA_PROYECCION_CONCENTRADA_CLIENTE",
        "CARTERA_PROYECCION_CONCENTRADA_FECHA",
    }.issubset(codigos)


def test_api_rechaza_mes_de_alertas_con_formato_invalido() -> None:
    _activar_fuentes()
    try:
        response = cliente_superadmin().get(
            "/api/v1/cartera/alertas?empresa_id=3&mes=octubre"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
