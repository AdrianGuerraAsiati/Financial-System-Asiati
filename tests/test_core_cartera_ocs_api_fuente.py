from app.main import app
from app.motores.cartera_ocs.api import obtener_estado_fuente
from tests.apoyo_auth import cliente_superadmin


def test_web_exposes_cartera_source_state() -> None:
    app.dependency_overrides[obtener_estado_fuente] = lambda: {
        "estado": "OK",
        "empresa_id": 3,
        "modo_fuente": "GOOGLE_SHEETS",
        "solo_lectura": True,
        "faltantes": [],
        "diagnosticos": [
            {
                "tipo": "OPERACIONES",
                "rango": "FC!A:Z",
                "filas_datos": 10,
                "valido": True,
                "campos_criticos_faltantes": [],
                "encabezados_duplicados": [],
            }
        ],
        "resumen": {
            "rangos": 3,
            "rangos_validos": 3,
            "filas": 30,
        },
    }
    try:
        response = cliente_superadmin().get(
            "/api/v1/cartera/fuente/estado?empresa_id=3"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["estado"] == "OK"
    assert response.json()["solo_lectura"] is True
    assert response.json()["resumen"]["rangos_validos"] == 3
