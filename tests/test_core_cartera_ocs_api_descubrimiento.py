from app.main import app
from app.motores.cartera_ocs.api import obtener_descubrimiento_fuente
from tests.apoyo_auth import cliente_superadmin


def test_web_exposes_cartera_source_discovery() -> None:
    app.dependency_overrides[obtener_descubrimiento_fuente] = lambda: {
        "empresa_id": 3,
        "spreadsheet_id": "sheet-cartera",
        "solo_lectura": True,
        "coincidencias_exactas": 1,
        "hojas": [
            {
                "titulo": "FC",
                "rango_previsualizacion": "'FC'!A1:ZZ20",
                "candidatos": [
                    {
                        "tipo": "OPERACIONES",
                        "fila_encabezado": 3,
                        "campos_encontrados": [
                            "NUMERO OC",
                            "VALOR OCI (DDP)",
                            "CARTERA",
                        ],
                        "campos_faltantes": [],
                        "coincide": True,
                        "rango_sugerido": "'FC'!A3:ZZ",
                    }
                ],
            }
        ],
        "nota": "Solo lectura.",
    }
    try:
        response = cliente_superadmin().get(
            "/api/v1/cartera/fuente/descubrir?empresa_id=3"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["solo_lectura"] is True
    assert body["coincidencias_exactas"] == 1
    assert body["hojas"][0]["candidatos"][0]["rango_sugerido"] == "'FC'!A3:ZZ"
