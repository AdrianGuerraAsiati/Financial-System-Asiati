from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


ACCION_CERRAR = "CERRAR"
ACCION_REABRIR = "REABRIR"


class PeriodoCierreEvento(Base):
    __tablename__ = "periodo_cierre_eventos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    periodo_id: Mapped[int] = mapped_column(
        ForeignKey("periodos.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    accion: Mapped[str] = mapped_column(String(16), nullable=False)
    estado_anterior: Mapped[bool] = mapped_column(Boolean, nullable=False)
    estado_nuevo: Mapped[bool] = mapped_column(Boolean, nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocurrido_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
