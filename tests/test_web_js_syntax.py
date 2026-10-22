"""Protege la compilación de todos los scripts críticos del frontend.

Las pruebas de inclusión de cadenas pueden pasar aunque un script tenga un
SyntaxError en tiempo de carga; Node --check detecta ese tipo de regresión.
"""
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = [
    "app/web/app.js",
    "app/web/modal.js",
    "app/web/cartera_sort.js",
    "app/web/cartera_drive.js",
    "app/web/cartera_aportes.js",
    "app/web/cartera_navegacion.js",
    "app/web/cartera_paginacion.js",
    "app/web/financial_charts.js",
    "app/web/google_sheets_connect.js",
    "app/web/google_sheets_oauth_launch.js",
]


@pytest.mark.parametrize("path", SCRIPTS)
@pytest.mark.skipif(shutil.which("node") is None, reason="Node no disponible")
def test_js_compila_sin_errores_de_sintaxis(path: str) -> None:
    script = ROOT / path
    salida = subprocess.run(
        ["node", "--check", str(script)],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert salida.returncode == 0, f"{path}: {salida.stderr}"
