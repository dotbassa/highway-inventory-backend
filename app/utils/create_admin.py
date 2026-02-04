import os
from argon2 import PasswordHasher
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.user import User
from app.enums.enums import RoleType
from app.db.database import SessionLocal
from app.utils.logger import logger_instance as log


async def create_admin_user():
    admin_rut = os.getenv("ADMIN_RUT")
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    admin_nombres = os.getenv("ADMIN_NOMBRES")
    admin_apellidos = os.getenv("ADMIN_APELLIDOS")

    if not all([admin_rut, admin_email, admin_password]):
        log.info(
            "Variables de admin no configuradas, saltando creación de usuario admin"
        )
        return

    async with SessionLocal() as session:
        session: AsyncSession
        try:
            result = await session.execute(
                select(User).where(
                    (User.email == admin_email) | (User.rut == admin_rut)
                )
            )
            existing_user = result.scalar_one_or_none()

            if existing_user:
                return

            ph = PasswordHasher()
            hashed_password = ph.hash(admin_password)

            admin_user = User(
                rut=admin_rut,
                nombres=admin_nombres,
                apellidos=admin_apellidos,
                email=admin_email,
                contrasena=hashed_password,
                rol=RoleType.admin,
                activo=True,
                verificado=True,
            )

            session.add(admin_user)
            await session.commit()

            log.info(
                f"Usuario admin creado exitosamente",
                extra={
                    "email": admin_email,
                    "rut": admin_rut,
                },
            )

        except Exception as e:
            log.error(
                f"Error al crear usuario admin",
                extra={
                    "error": str(e),
                },
            )
            await session.rollback()


if __name__ == "__main__":
    import asyncio

    log.info("Creating admin user...")
    asyncio.run(create_admin_user())
    log.info("Process completed")
