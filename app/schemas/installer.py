from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
from datetime import datetime
import re

NOMBRE_MIN_LENGTH = 1
NOMBRE_MAX_LENGTH = 255


class InstallerBase(BaseModel):
    rut: Optional[str] = Field(
        default=None,
        description="Installer's RUT (unique)",
        min_length=7,
        max_length=12,
        pattern=r"^\d{7,8}-[\dkK]$",
    )
    nombre: Optional[str] = Field(
        default=None,
        description="Installer's name",
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

        v = re.sub(r"\s+", " ", v.strip())

        if len(v) < NOMBRE_MIN_LENGTH or len(v) > NOMBRE_MAX_LENGTH:
            raise ValueError(
                f"Nombre must be between {NOMBRE_MIN_LENGTH} and {NOMBRE_MAX_LENGTH} in length"
            )

        return v


class InstallerCreate(InstallerBase):
    rut: str = Field(...)
    nombre: str = Field(...)


class InstallerUpdate(InstallerBase):
    activo: Optional[bool] = Field(
        default=None,
        description="Installer's active status",
    )


class InstallerResponse(InstallerBase):
    id: int
    activo: bool
    created_at: datetime
    updated_at: datetime
