"""Diagnóstico externo HTTPS de Wallets: solo lectura y sin credenciales.

No prueba login Cognito, acceso a PostgreSQL ni regresiones financieras.
"""
from __future__ import annotations

import argparse
import json
import ssl
from urllib.parse import urlsplit
from urllib.request import urlopen


DEFAULT_URL = "https://3-141-226-208.sslip.io"
REQUIRED = {"/health": ("status", "ok"), "/ready": ("status", "ready")}


def comprobar(base_url: str, *, timeout: float = 8.0) -> list[str]:
    url = urlsplit(base_url)
    if url.scheme != "https" or not url.netloc or url.username or url.password or url.query or url.fragment:
        raise ValueError("Utilizar una URL HTTPS sin credenciales, query ni fragmento.")
    if url.path not in ("", "/"):
        raise ValueError("Indicar solo la URL base, sin rutas adicionales.")
    base = f"https://{url.netloc}"
    resultado = []
    for ruta, (clave, valor) in REQUIRED.items():
        # No deshabilitar la validación TLS ni volcar respuestas del servidor.
        with urlopen(base + ruta, timeout=timeout, context=ssl.create_default_context()) as resp:
            if resp.status != 200:
                raise RuntimeError(f"{ruta}: HTTP distinto de 200")
            datos = json.loads(resp.read(4096))
        if not isinstance(datos, dict) or datos.get(clave) != valor:
            raise RuntimeError(f"{ruta}: respuesta JSON inesperada")
        resultado.append(f"PASS: HTTPS {ruta}")
    return resultado


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL)
    args = parser.parse_args()
    try:
        for linea in comprobar(args.url):
            print(linea)
    except Exception as exc:
        # No emitir bodies, cabeceras, ni información potencialmente confidencial.
        print(f"FAIL: no se verificaron ambos endpoints ({type(exc).__name__}).")
        return 1
    print("AVISO: los endpoints actuales son estáticos; no certifican BD, Cognito ni el SHA instalado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
