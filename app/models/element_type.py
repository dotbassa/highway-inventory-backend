from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, TimestampMixin


class ElementType(Base, TimestampMixin):
    __tablename__ = "element_type"

    id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        primary_key=True,
        autoincrement=True,
    )
    nombre: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )
    activo: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
    )
