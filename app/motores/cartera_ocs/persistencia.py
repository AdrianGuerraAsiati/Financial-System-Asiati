from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.db import Base
from app.motores.cartera_ocs.comprobantes import ComprobantePago


class ComprobantePagoPersistido(Base):
    __tablename__ = "cartera_comprobantes_pago"
    __table_args__ = (
        UniqueConstraint(
            "empresa_id",
            "contenido_hash",
            name="uq_cartera_comprobante_empresa_hash",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(
        ForeignKey("empresas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    oc: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    cliente: Mapped[str] = mapped_column(String(255), nullable=False)
    pais: Mapped[str] = mapped_column(String(100), nullable=False)
    comercial: Mapped[str] = mapped_column(String(255), nullable=False)
    monto_esperado: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )
    nombre_archivo: Mapped[str] = mapped_column(String(255), nullable=False)
    contenido_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    ubicacion_archivo: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    estado_auditoria: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        index=True,
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


def guardar_comprobante(
    session: Session,
    *,
    empresa_id: int,
    comprobante: ComprobantePago,
    ubicacion_archivo: str | None = None,
) -> ComprobantePagoPersistido:
    """Persiste un comprobante radicado dentro del módulo de Cartera."""
    registro = ComprobantePagoPersistido(
        empresa_id=empresa_id,
        oc=comprobante.oc,
        cliente=comprobante.cliente,
        pais=comprobante.pais,
        comercial=comprobante.comercial,
        monto_esperado=Decimal(str(comprobante.monto_esperado)),
        nombre_archivo=comprobante.nombre_archivo,
        contenido_hash=comprobante.contenido_hash,
        ubicacion_archivo=ubicacion_archivo,
        estado_auditoria=comprobante.estado_auditoria,
    )
    session.add(registro)
    return registro


def existe_comprobante_por_hash(
    session: Session,
    *,
    empresa_id: int,
    contenido_hash: str,
) -> bool:
    statement = select(ComprobantePagoPersistido.id).where(
        ComprobantePagoPersistido.empresa_id == empresa_id,
        ComprobantePagoPersistido.contenido_hash == contenido_hash,
    )
    return session.scalar(statement) is not None



def obtener_comprobante_por_empresa(
    session: Session,
    *,
    empresa_id: int,
    comprobante_id: int,
) -> ComprobantePagoPersistido | None:
    statement = select(ComprobantePagoPersistido).where(
        ComprobantePagoPersistido.id == comprobante_id,
        ComprobantePagoPersistido.empresa_id == empresa_id,
    )
    return session.scalar(statement)
