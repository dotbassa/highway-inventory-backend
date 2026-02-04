from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

from app.db.base_class import Base, TimestampMixin


class MacroLocation(Base, TimestampMixin):
    __tablename__ = "macro_location"

    id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        primary_key=True,
        autoincrement=True,
    )
    nombre: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
    )
    km_inicial: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )
    km_final: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=True,
    )
    georeferencia_inicial: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    georeferencia_final: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    activo: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
    )
