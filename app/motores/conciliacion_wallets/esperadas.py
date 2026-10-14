"""Cobertura de wallets declaradas para un período; sin inferencias desde ejecuciones."""
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, String, UniqueConstraint, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.core.db import Base
from app.core.periodos import Periodo


class WalletEsperada(Base):
    __tablename__ = "wallets_esperadas"
    __table_args__ = (
        UniqueConstraint("periodo_id", "tipo_wallet", "identidad_wallet", name="uq_wallets_esperadas_contexto"),
        CheckConstraint("tipo_wallet IN ('wiilog','tienda','pagos')", name="ck_wallets_esperadas_tipo"),
        CheckConstraint("(tipo_wallet = 'wiilog' AND identidad_wallet = '') OR (tipo_wallet <> 'wiilog' AND identidad_wallet <> '')", name="ck_wallets_esperadas_identidad"),
        Index("ix_wallets_esperadas_empresa_periodo", "empresa_id", "periodo_id"),
        ForeignKeyConstraint(["periodo_id", "empresa_id"], ["periodos.id", "periodos.empresa_id"], name="fk_wallets_esperadas_periodo_empresa", ondelete="RESTRICT"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id", ondelete="RESTRICT"), nullable=False)
    periodo_id: Mapped[int] = mapped_column(ForeignKey("periodos.id", ondelete="RESTRICT"), nullable=False)
    tipo_wallet: Mapped[str] = mapped_column(String(16), nullable=False)
    identidad_wallet: Mapped[str] = mapped_column(String(320), nullable=False, default="")
    registrado_por: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False)
    registrado_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


def claves_esperadas(session: Session, *, empresa_id: int, periodo_id: int) -> set[tuple[str, str]]:
    periodo = session.get(Periodo, periodo_id)
    if periodo is None or periodo.empresa_id != empresa_id:
        raise ValueError("El período no pertenece a la empresa indicada.")
    rows = session.scalars(select(WalletEsperada).where(
        WalletEsperada.empresa_id == empresa_id,
        WalletEsperada.periodo_id == periodo_id,
    ))
    return {(r.tipo_wallet, r.identidad_wallet) for r in rows}
