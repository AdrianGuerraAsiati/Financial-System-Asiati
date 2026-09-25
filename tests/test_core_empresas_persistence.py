from app.core.db import Base
from app.core.empresas import Empresa


def test_empresas_is_registered_as_core_table() -> None:
    assert Empresa.__tablename__ == "empresas"
    assert "empresas" in Base.metadata.tables


def test_empresa_has_minimum_identity_fields() -> None:
    columns = Empresa.__table__.columns

    assert columns["id"].primary_key is True
    assert columns["nombre"].nullable is False
