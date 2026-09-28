from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


TIPO_PREGUNTA = "PREGUNTA"
TIPO_RESPUESTA = "RESPUESTA"
TIPO_NOTA = "NOTA"


class HallazgoMensaje(Base):
    """Hilo del caso especial de un hallazgo."""

    __tablename__ = "hallazgo_mensajes"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('PREGUNTA', 'RESPUESTA', 'NOTA')",
            name="ck_hallazgo_mensajes_tipo",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hallazgo_id: Mapped[int] = mapped_column(
        ForeignKey("hallazgos.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )
    tipo: Mapped[str] = mapped_column(String(16), nullable=False)
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    creado_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
