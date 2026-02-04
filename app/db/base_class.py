from sqlalchemy import Column, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone

Base = declarative_base()


class TimestampMixin:
    """
    Mixin para agregar timestamps UTC a todos los modelos.

    Usa DateTime(timezone=True) para almacenar en PostgreSQL como TIMESTAMPTZ,
    y datetime.now(timezone.utc) para garantizar que siempre se guarde en UTC
    independientemente del timezone del servidor.
    """

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
