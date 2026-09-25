from app.core.cargas import Carga
from app.core.fuentes import Fuente


def test_fuente_has_empresa_identity() -> None:
    fuente = Fuente(empresa_id=1, nombre="Wallet principal")

    assert fuente.empresa_id == 1
    assert fuente.nombre == "Wallet principal"


def test_carga_carries_source_and_period_context() -> None:
    carga = Carga(
        empresa_id=1,
        fuente_id=2,
        periodo_id=3,
        contenido_hash="a" * 64,
    )

    assert carga.fuente_id == 2
    assert carga.periodo_id == 3
