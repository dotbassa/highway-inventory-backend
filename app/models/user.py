from sqlalchemy import Integer, String, Enum as SqlAlchemyEnum
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

from app.db.base_class import Base, TimestampMixin
from app.enums.enums import RoleType


class User(Base, TimestampMixin):
    __tablename__ = "orgs_name_user"

    id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        primary_key=True,
        autoincrement=True,
    )
    rut: Mapped[str] = mapped_column(
        String,
        nullable=False,
        unique=True,
        index=True,
    )
    nombres: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=False,
    )
    apellidos: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=False,
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )
    contrasena: Mapped[Optional[str]] = mapped_column(
        String,
        nullable=False,
    )
    rol: Mapped[RoleType] = mapped_column(
        SqlAlchemyEnum(RoleType),
        nullable=False,
        default=RoleType.regular,
    )
    activo: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
    )
    verificado: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )
    tiene_contrasena_temporal: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )
