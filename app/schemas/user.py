from pydantic import BaseModel, Field, ConfigDict, field_validator, EmailStr
from typing import Optional
import re
from datetime import datetime

from app.enums.enums import RoleType

NOMBRE_APELLIDO_MIN_LENGTH = 1
NOMBRE_APELLIDO_MAX_LENGTH = 100

# Constantes para validación de contraseñas en login
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128


class UserBase(BaseModel):
    rut: Optional[str] = Field(
        default=None,
        description="User's RUT (unique)",
    )
    nombres: Optional[str] = Field(
        default=None,
        description="User's names",
    )
    apellidos: Optional[str] = Field(
        default=None,
        description="User's surnames",
    )
    email: Optional[EmailStr] = Field(
        default=None,
        description="User's email address (unique)",
        max_length=100,
    )

    model_config = ConfigDict(
        extra="ignore",
        from_attributes=True,
        validate_assignment=True,
    )

    @field_validator("rut")
    @classmethod
    def validate_rut_format(cls, v: Optional[str]) -> Optional[str]:
        """
        Valida que el RUT tenga el formato correcto: XXXXXXXX-X o XXXXXXX-X
        También proporciona mensajes de error claros
        """
        if v is None:
            return v

        # Patrón del RUT
        rut_pattern = re.compile(r"^\d{7,8}-[\dkK]$")

        if not rut_pattern.match(v):
            # Verificar casos comunes de error
            if re.match(r"^\d{8,9}$", v):
                # RUT sin guion
                raise ValueError(
                    f"El RUT '{v}' no tiene el formato correcto. "
                    f"Debe incluir el guion antes del dígito verificador (ej: {v[:-1]}-{v[-1]})"
                )
            elif "-" not in v:
                raise ValueError(
                    f"El RUT '{v}' debe incluir un guion antes del dígito verificador (formato: XXXXXXXX-X)"
                )
            else:
                raise ValueError(
                    f"El RUT '{v}' no tiene el formato correcto. "
                    f"Formato esperado: 7-8 dígitos, guion, y dígito verificador (0-9 o K). Ejemplo: 12345678-9"
                )

        return v.upper()  # Normalizar la K a mayúscula

    @field_validator("nombres", "apellidos")
    @classmethod
    def normalize_nombre(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v

        v = re.sub(r"\s+", " ", v.strip().title())

        if len(v) < NOMBRE_APELLIDO_MIN_LENGTH or len(v) > NOMBRE_APELLIDO_MAX_LENGTH:
            raise ValueError(
                f"Nombres or apellidos must be between {NOMBRE_APELLIDO_MIN_LENGTH} and {NOMBRE_APELLIDO_MAX_LENGTH} in length"
            )

        return v


class UserCreate(UserBase):
    rut: str = Field(...)
    nombres: str = Field(...)
    apellidos: str = Field(...)
    email: EmailStr = Field(...)


class UserUpdate(UserBase):
    contrasena: Optional[str] = Field(
        default=None,
        min_length=8,
        max_length=128,
    )
    activo: Optional[bool] = Field(
        default=None,
        description="Indicates if the user is active",
    )
    verificado: Optional[bool] = Field(
        default=None,
        description="Indicates if the user is verified",
    )
    rol: Optional[RoleType] = Field(
        default=None,
        description="Role assigned to the user",
    )


class UserResponse(UserBase):
    id: int
    rol: RoleType
    activo: bool
    verificado: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        extra="ignore",
        from_attributes=True,
        validate_assignment=True,
    )


"""Auth related schemas"""


class LoginRequest(BaseModel):
    user_email: EmailStr = Field(
        ...,
        description="User's email address",
        max_length=100,
    )
    contrasena: str = Field(
        ...,
        description="User's password",
        max_length=PASSWORD_MAX_LENGTH,
    )

    model_config = ConfigDict(
        extra="forbid",  # Rechazar campos adicionales no definidos
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    @field_validator("contrasena")
    @classmethod
    def validate_password_security(cls, v: str) -> str:

        v = v.strip()

        if len(v) > PASSWORD_MAX_LENGTH:
            raise ValueError(
                f"La contraseña no puede exceder {PASSWORD_MAX_LENGTH} caracteres"
            )

        # Detectar patrones de inyección SQL
        sql_injection_patterns = [
            r"(\bOR\b|\bAND\b).*[=<>]",  # OR 1=1, AND 1=1
            r"[;'\"]\s*(DROP|DELETE|INSERT|UPDATE|SELECT|UNION|EXEC|EXECUTE)",  # SQL keywords peligrosos
            r"--",  # Comentarios SQL
            r"/\*.*\*/",  # Comentarios SQL de bloque
            r"xp_",  # Stored procedures de SQL Server
            r"\bEXEC\b",  # EXEC statements
        ]

        for pattern in sql_injection_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError(
                    "La contraseña contiene patrones no permitidos por razones de seguridad"
                )

        # Detectar patrones de inyección XML/XSS
        xml_xss_patterns = [
            r"<\s*script",  # <script>
            r"<\s*/?\s*(iframe|object|embed|applet)",  # Tags peligrosos
            r"javascript\s*:",  # javascript:
            r"on\w+\s*=",  # onclick=, onerror=, etc.
            r"<!\[CDATA\[",  # CDATA sections
            r"&\s*#",  # HTML entities que pueden ser usados para ofuscar
        ]

        for pattern in xml_xss_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError(
                    "La contraseña contiene patrones no permitidos por razones de seguridad"
                )

        # Detectar caracteres de control y nulos que pueden causar problemas
        if re.search(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", v):
            raise ValueError("La contraseña no puede contener caracteres de control")

        # Detectar intentos de path traversal
        if re.search(r"\.\./|\.\.\\", v):
            raise ValueError("La contraseña contiene patrones no permitidos")

        return v


class TokenData(BaseModel):
    user_name: str = Field(
        ...,
        description="User's name",
    )
    user_rut: str = Field(
        ...,
        description="User's RUT",
    )
    user_email: EmailStr = Field(
        ...,
        description="User's email address",
    )
    user_role: RoleType = Field(
        ...,
        description="Role assigned to the user",
    )
    has_temporary_password: bool = Field(
        ...,
        description="Indicates if the user has a temporary password",
    )
    exp: datetime = Field(
        ...,
        description="Expiration time of the token",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=True,
        from_attributes=True,
    )


class TokenResponse(BaseModel):
    access_token: str = Field(
        ...,
        description="JWT access token",
    )
    token_type: str = Field(
        default="bearer",
        description="Type of the token",
    )

    model_config = ConfigDict(
        extra="ignore",
        from_attributes=True,
    )


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(
        ...,
        description="Contraseña temporal actual",
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
    )
    new_password: str = Field(
        ...,
        description="Nueva contraseña permanente",
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
    )

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    @field_validator("new_password")
    @classmethod
    def validate_password_security(cls, v: str) -> str:

        v = v.strip()

        if len(v) > PASSWORD_MAX_LENGTH:
            raise ValueError(
                f"La contraseña no puede exceder {PASSWORD_MAX_LENGTH} caracteres"
            )

        # Detectar patrones de inyección SQL
        sql_injection_patterns = [
            r"(\bOR\b|\bAND\b).*[=<>]",
            r"[;'\"]\s*(DROP|DELETE|INSERT|UPDATE|SELECT|UNION|EXEC|EXECUTE)",
            r"--",
            r"/\*.*\*/",
            r"xp_",
            r"\bEXEC\b",
        ]

        for pattern in sql_injection_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError(
                    "La contraseña contiene patrones no permitidos por razones de seguridad"
                )

        # Detectar patrones de inyección XML/XSS
        xml_xss_patterns = [
            r"<\s*script",
            r"<\s*/?\s*(iframe|object|embed|applet)",
            r"javascript\s*:",
            r"on\w+\s*=",
            r"<!\[CDATA\[",
            r"&\s*#",
        ]

        for pattern in xml_xss_patterns:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError(
                    "La contraseña contiene patrones no permitidos por razones de seguridad"
                )

        # Detectar caracteres de control y nulos
        if re.search(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", v):
            raise ValueError("La contraseña no puede contener caracteres de control")

        # Detectar intentos de path traversal
        if re.search(r"\.\./|\.\.\\", v):
            raise ValueError("La contraseña contiene patrones no permitidos")

        return v
