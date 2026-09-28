import os
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.empresas import Empresa
from app.main import app
from app.motores.cartera_ocs.almacenamiento import AlmacenLocalComprobantes
from app.motores.cartera_ocs.api import (
    obtener_almacen_comprobantes,
    obtener_fuente_operaciones,
)
from app.motores.cartera_ocs.importacion import RegistroCarteraEnCamino


def _engine():
    return create_engine(os.environ["DATABASE_URL"])


class FuenteE2E:
    def listar(self, *, empresa_id: int):
        return (
            RegistroCarteraEnCamino(
                cliente="Cliente E2E",
                contacto="Contacto E2E",
                producto="Producto E2E",
                sku="SKU-E2E",
                oc="OC-E2E",
                negociacion="50% anticipo / 50% a la entrega",
                modo_transporte="Aéreo",
                documento_transporte="GUIA-E2E",
                estado="Entregado",
                anio_oc=2026,
                eta="2026-09-28",
                etapa="EN CAMINO",
                valor=2000,
                valor_anticipo=1000,
                valor_financiado=1000,
                porcentaje_anticipo=0.5,
            ),
        )


def test_cartera_vertical_journey(tmp_path: Path) -> None:
    with Session(_engine()) as session:
        empresa = Empresa(nombre="ASIATI cartera e2e")
        session.add(empresa)
        session.commit()
        empresa_id = empresa.id

    app.dependency_overrides[obtener_fuente_operaciones] = lambda: FuenteE2E()
    app.dependency_overrides[obtener_almacen_comprobantes] = (
        lambda: AlmacenLocalComprobantes(tmp_path)
    )
    client = TestClient(app)

    try:
        listado = client.get(f"/cartera/operaciones?empresa_id={empresa_id}")
        assert listado.status_code == 200
        assert [item["oc"] for item in listado.json()] == ["OC-E2E"]

        detalle_inicial = client.get(
            f"/cartera/operaciones/OC-E2E?empresa_id={empresa_id}"
        )
        assert detalle_inicial.status_code == 200
        assert detalle_inicial.json()["comprobantes_pendientes"] == 0

        carga = client.post(
            "/cartera/comprobantes",
            data={
                "empresa_id": str(empresa_id),
                "oc": "OC-E2E",
                "cliente": "Cliente E2E",
                "pais": "COLOMBIA",
                "valor_ddp": "2000",
                "tipo_negociacion": "50% anticipo / 50% a la entrega",
                "fecha_entrega": "2026-09-28",
                "comercial": "COMERCIAL E2E",
            },
            files={
                "archivo": (
                    "comprobante-e2e.pdf",
                    b"comprobante e2e",
                    "application/pdf",
                )
            },
        )
        assert carga.status_code == 201
        assert carga.json()["estado_auditoria"] == "PENDIENTE"

        detalle_final = client.get(
            f"/cartera/operaciones/OC-E2E?empresa_id={empresa_id}"
        )
        assert detalle_final.status_code == 200
        assert detalle_final.json()["comprobantes_pendientes"] == 1

        bandeja = client.get(
            f"/cartera/comprobantes/pendientes?empresa_id={empresa_id}"
        )
        assert bandeja.status_code == 200
        assert [item["oc"] for item in bandeja.json()] == ["OC-E2E"]
    finally:
        app.dependency_overrides.clear()
