from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, TimestampMixin


class Installer(Base, TimestampMixin):
    __tablename__ = "installer"

    id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        primary_key=True,
        autoincrement=True,
    )
    rut: Mapped[str] = mapped_column(
        String(12),
        nullable=False,
        unique=True,
    )
    nombre: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    activo: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
    )
