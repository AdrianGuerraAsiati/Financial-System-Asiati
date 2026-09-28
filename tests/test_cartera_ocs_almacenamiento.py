from pathlib import Path

from app.motores.cartera_ocs.almacenamiento import AlmacenLocalComprobantes


def test_almacen_local_guarda_el_archivo_y_devuelve_una_ubicacion_relativa(tmp_path: Path) -> None:
    almacen = AlmacenLocalComprobantes(tmp_path)

    ubicacion = almacen.guardar(
        empresa_id=7,
        oc="OC-123",
        nombre_archivo="../../comprobante.pdf",
        contenido_hash="a" * 64,
        contenido=b"contenido real",
    )

    assert ubicacion == f"7/OC-123/{'a' * 64}-comprobante.pdf"
    assert (tmp_path / ubicacion).read_bytes() == b"contenido real"
