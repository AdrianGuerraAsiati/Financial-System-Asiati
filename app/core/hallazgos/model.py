from sqlalchemy import Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Hallazgo(Base):
    __tablename__ = "hallazgos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    periodo_id: Mapped[int] = mapped_column(
        ForeignKey("periodos.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    critico: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    resuelto: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
