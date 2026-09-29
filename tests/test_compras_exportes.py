import io
import zipfile

from app.motores.compras_supply_chain.contrato import analizar_encabezados
from app.motores.compras_supply_chain.exportes import crear_zip_exportacion
from app.motores.compras_supply_chain.normalizacion import normalizar_fila_compra


def test_export_bundle_contains_utf8_csvs() -> None:
    linea = normalizar_fila_compra(
        {
            "NUMERO OC": "OC-1",
            "CLIENTE": "Cliente Bogotá",
            "SKU": "SKU-1",
            "PROVEEDOR": "Proveedor",
            "ESTADO": "EN PRODUCCION",
            "MODO TRANSPORTE": "MARITIMO",
            "VALOR TOTAL COMPRA USD": "100.25",
            "VALOR OCI (DDP)": "150.50",
        },
        pais="CO",
        fila_fuente=2,
    )
    diagnostico = analizar_encabezados(
        [
            "NUMERO OC",
            "CLIENTE",
            "PROVEEDOR",
            "ESTADO",
            "MODO TRANSPORTE",
            "VALOR TOTAL COMPRA USD",
            "VALOR OCI (DDP)",
        ],
        pais="CO",
        rango="CO!A:Z",
        filas_datos=1,
    )

    contenido = crear_zip_exportacion((linea,), (diagnostico,))

    with zipfile.ZipFile(io.BytesIO(contenido)) as archivo:
        assert set(archivo.namelist()) == {
            "compras_lineas.csv",
            "compras_ocs.csv",
            "compras_puntos_atencion.csv",
            "compras_kpis.csv",
        }
        texto = archivo.read("compras_lineas.csv").decode("utf-8-sig")
        assert "Cliente Bogotá" in texto
        assert "OC-1" in texto
