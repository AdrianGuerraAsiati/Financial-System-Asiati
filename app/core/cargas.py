import hashlib

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def calcular_hash_contenido(contenido: bytes) -> str:
    """Devuelve un SHA-256 determinístico para el contenido de una carga."""
    return hashlib.sha256(contenido).hexdigest()


class Carga(Base):
    __tablename__ = "cargas"
    __table_args__ = (
        UniqueConstraint(
            "empresa_id",
            "contenido_hash",
            name="uq_cargas_empresa_hash",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(
        ForeignKey("empresas.id"),
        nullable=False,
    )
    fuente_id: Mapped[int] = mapped_column(
        ForeignKey("fuentes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    periodo_id: Mapped[int] = mapped_column(
        ForeignKey("periodos.id", ondelete="RESTRICT"),
        nullable=False,
    )
    contenido_hash: Mapped[str] = mapped_column(String(64), nullable=False)
