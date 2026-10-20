"""Ejecución MANUAL del inventario, nunca desde el navegador.

Uso en contenedor ASIATI:
  python -m app.motores.cartera_ocs.drive_sync
"""
import json

from app.core.session import crear_session
from app.motores.cartera_ocs.drive_index import sincronizar_desde_entorno


def main() -> None:
    with crear_session() as session:
        with session.begin():
            resultado = sincronizar_desde_entorno(session)
    # Solo métricas, sin nombres de clientes, ID de archivos o tokens.
    print(json.dumps(resultado, ensure_ascii=False))


if __name__ == "__main__":
    main()
