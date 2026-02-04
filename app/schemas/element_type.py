from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
from datetime import datetime
import re

NOMBRE_MIN_LENGTH = 1
NOMBRE_MAX_LENGTH = 255


class ElementTypeBase(BaseModel):
    nombre: Optional[str] = Field(
        default=None,
        description="Element type's name",
    )

    model_config = ConfigDict(
        extra="ignore",
        from_attributes=True,
    )

    @field_validator("nombre")
    @classmethod
    def normalize_nombre(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v

        v = re.sub(r"\s+", " ", v.strip().capitalize())

        if len(v) < NOMBRE_MIN_LENGTH or len(v) > NOMBRE_MAX_LENGTH:
            raise ValueError(
                f"Nombre must be between {NOMBRE_MIN_LENGTH} and {NOMBRE_MAX_LENGTH} in length"
            )

        return v


class ElementTypeCreate(ElementTypeBase):
    nombre: str = Field(...)


class ElementTypeUpdate(ElementTypeBase):
    activo: Optional[bool] = Field(
        default=None,
        description="Installer's active status",
    )


class ElementTypeResponse(ElementTypeBase):
    id: int
    activo: bool
    created_at: datetime
    updated_at: datetime
