import pytest

from app.core.cargas.errors import ContextoCargaInvalidoError
from app.core.cargas.service import registrar_carga


class SpySession:
    def __init__(self) -> None:
        self.added = []

    def add(self, entity) -> None:
        self.added.append(entity)


def test_rejects_source_from_another_empresa() -> None:
    session = SpySession()

    with pytest.raises(ContextoCargaInvalidoError):
        registrar_carga(
            session,
            empresa_id=1,
            fuente_id=20,
            periodo_id=30,
            contenido_hash="a" * 64,
            fuente_pertenece=lambda _s, _fuente_id, _empresa_id: False,
            periodo_pertenece=lambda _s, _periodo_id, _empresa_id: True,
        )

    assert session.added == []


def test_rejects_period_from_another_empresa() -> None:
    session = SpySession()

    with pytest.raises(ContextoCargaInvalidoError):
        registrar_carga(
            session,
            empresa_id=1,
            fuente_id=20,
            periodo_id=30,
            contenido_hash="b" * 64,
            fuente_pertenece=lambda _s, _fuente_id, _empresa_id: True,
            periodo_pertenece=lambda _s, _periodo_id, _empresa_id: False,
        )

    assert session.added == []


def test_registers_load_when_context_is_consistent() -> None:
    session = SpySession()

    carga = registrar_carga(
        session,
        empresa_id=1,
        fuente_id=20,
        periodo_id=30,
        contenido_hash="c" * 64,
        fuente_pertenece=lambda _s, _fuente_id, _empresa_id: True,
        periodo_pertenece=lambda _s, _periodo_id, _empresa_id: True,
    )

    assert carga in session.added
    assert carga.empresa_id == 1
    assert carga.fuente_id == 20
    assert carga.periodo_id == 30
