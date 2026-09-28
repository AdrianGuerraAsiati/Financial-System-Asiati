from pathlib import Path

import pytest

from app.motores.cartera_ocs.almacenamiento import AlmacenLocalComprobantes


def test_local_storage_reads_only_locations_inside_base_directory(tmp_path: Path) -> None:
    almacen = AlmacenLocalComprobantes(tmp_path)
    ubicacion = almacen.guardar(
        empresa_id=1,
        oc="OC-1",
        nombre_archivo="soporte.pdf",
        contenido_hash="a" * 64,
        contenido=b"contenido",
    )

    assert almacen.leer(ubicacion) == b"contenido"

    with pytest.raises(ValueError):
        almacen.leer("../fuera.pdf")
