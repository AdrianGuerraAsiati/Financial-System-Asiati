"""Carga idempotente de los valores iniciales de las listas de categorización.

    python -m app.core.dimensiones --archivo docs/nucleo/dimensiones_iniciales.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.core.dimensiones.service import cargar_valores_iniciales
from app.core.session import crear_session


def main() -> int:
    parser = argparse.ArgumentParser(description="Carga los valores iniciales de las listas de categorización.")
    parser.add_argument("--archivo", required=True, help="JSON con la clave 'valores' por dimensión.")
    args = parser.parse_args()
    valores = json.loads(Path(args.archivo).read_text(encoding="utf-8"))["valores"]
    with crear_session() as session:
        resultado = cargar_valores_iniciales(session, valores)
        session.commit()
    print(json.dumps({"creados": resultado.creados, "existentes": resultado.existentes}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
