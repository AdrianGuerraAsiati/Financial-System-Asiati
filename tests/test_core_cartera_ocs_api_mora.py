
from decimal import Decimal

from app.main import app
from tests.apoyo_auth import cliente_superadmin
from app.motores.cartera_ocs.api import obtener_fuente_mora
from app.motores.cartera_ocs.mora import RegistroCarteraMora


class FuenteFake:
    def listar(self, *, empresa_id: int):
        assert empresa_id == 3
        return (
            RegistroCarteraMora(
                cliente="Cliente API Mora",
                empresa="ASIATI Comercial",
                monto=Decimal("1250.50"),
                observacion="Seguimiento activo",
                estado="MORA",
            ),
        )


def test_web_lists_mora_for_empresa() -> None:
    app.dependency_overrides[obtener_fuente_mora] = lambda: FuenteFake()
    try:
        response = cliente_superadmin().get("/api/v1/cartera/mora?empresa_id=3")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == [
        {
            "cliente": "Cliente API Mora",
            "empresa": "ASIATI Comercial",
            "monto": "1250.50",
            "observacion": "Seguimiento activo",
            "estado": "MORA",
        }
    ]
