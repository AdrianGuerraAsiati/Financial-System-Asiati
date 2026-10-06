"""Valores iniciales de las listas de categorización (decisión 0008). Sin base de datos."""
import json
from pathlib import Path

from app.core.dimensiones.service import DIMENSIONES, normalizar

VALORES = json.loads(Path("docs/nucleo/dimensiones_iniciales.json").read_text(encoding="utf-8"))["valores"]


def test_cubre_todas_las_dimensiones_administrables() -> None:
    assert set(VALORES) == set(DIMENSIONES)


def test_empresas_son_solo_las_cuatro_decididas() -> None:
    assert VALORES["empresa"] == ["WIILOG", "ASIATI", "TIENDAS ASIATI", "ORIGEN VITAL"]


def test_unidades_de_negocio_sin_dropshipping_ni_falta_ingresar() -> None:
    unidades = {normalizar(v) for v in VALORES["unidad_negocio"]}
    assert len(VALORES["unidad_negocio"]) == 19
    assert {"FF", "UM", "TIENDAS", "PROVEEDURIA", "TRANSFER INTERCOMPANY"} <= unidades
    assert "DROPSHIPPING" not in unidades
    assert "FALTA INGRESAR" not in unidades


def test_categorias_sin_marcadores_ni_duplicados() -> None:
    normalizadas = [normalizar(v) for v in VALORES["categoria"]]
    assert len(normalizadas) == len(set(normalizadas))
    assert not {"FALTA INGRESAR", "PRUEBA"} & set(normalizadas)
    # La categoría DROPSHIPPING (ganancia de la tienda) se mantiene.
    assert "DROPSHIPPING" in normalizadas


def test_fijo_variable_e_ingreso_egreso() -> None:
    assert VALORES["fijo_variable"] == ["FIJO", "VARIABLE"]
    assert VALORES["ingreso_egreso"] == ["INGRESO", "EGRESO", "NETO_CERO", "TRASLADO"]
