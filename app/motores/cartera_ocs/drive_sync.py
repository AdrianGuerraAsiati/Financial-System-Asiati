"""Ejecución MANUAL del inventario, nunca desde el navegador.

Uso en contenedor ASIATI:
  python -m app.motores.cartera_ocs.drive_sync --preflight
  python -m app.motores.cartera_ocs.drive_sync
"""
import argparse
import json
import os

from app.core.session import crear_session
from app.motores.cartera_ocs.drive_index import (
    GoogleDriveInventario,
    sincronizar_desde_entorno,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventario documental de O.C. en Google Drive.")
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Verifica permisos de lectura de la carpeta sin escribir en PostgreSQL.",
    )
    args = parser.parse_args()

    if args.preflight:
        raiz_id = os.getenv("CARTERA_OC_DRIVE_FOLDER_ID", "").strip()
        if not raiz_id:
            raise ValueError("Configura CARTERA_OC_DRIVE_FOLDER_ID antes de verificar acceso.")
        GoogleDriveInventario().verificar_acceso_raiz(raiz_id)
        # Solo estado; no imprimir rutas, nombres ni identificadores de Drive.
        print(json.dumps({"estado": "OK", "acceso": "SOLO_LECTURA"}, ensure_ascii=False))
        return

    with crear_session() as session:
        with session.begin():
            resultado = sincronizar_desde_entorno(session)
    # Solo métricas, sin nombres de clientes, ID de archivos o tokens.
    print(json.dumps(resultado, ensure_ascii=False))


if __name__ == "__main__":
    main()
