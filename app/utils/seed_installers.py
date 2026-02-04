import asyncio
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.installer import Installer
from app.db.database import SessionLocal
from app.utils.logger import logger_instance as log


INSTALLERS = [
    {"rut": "13186420-5", "nombre": "Miguel Rodriguez Maldonado"},
    {"rut": "18510690-K", "nombre": "Jean Valencia Ramirez"},
    {"rut": "21933312-9", "nombre": "Roberto Ponce Ramirez"},
    {"rut": "21188204-2", "nombre": "Victor Aldea Luengo"},
    {"rut": "20384249-K", "nombre": "David Leiva Perez"},
    {"rut": "19049404-7", "nombre": "Raul Ahumada Fernandez"},
    {"rut": "18659685-4", "nombre": "Patricio Tapia Castillo"},
    {"rut": "15498416-K", "nombre": "Diego Araya Moreno"},
    {"rut": "15062247-6", "nombre": "Michael Contreras Arancibia"},
    {"rut": "19214404-3", "nombre": "Felipe Lopez Lopez"},
]


async def seed_installers():
    async with SessionLocal() as session:
        session: AsyncSession
        try:
            result = await session.execute(select(Installer.rut))
            existing_ruts = {row[0] for row in result.all()}

            new_count = 0
            for installer_data in INSTALLERS:
                if installer_data["rut"] not in existing_ruts:
                    installer = Installer(
                        rut=installer_data["rut"],
                        nombre=installer_data["nombre"],
                    )
                    session.add(installer)
                    new_count += 1

            if new_count > 0:
                await session.commit()
                log.info(
                    f"Seeded {new_count} new installers, total: {len(INSTALLERS)}",
                )
            else:
                log.info("All installers already exist")

        except Exception as e:
            await session.rollback()
            log.error(
                f"Error seeding installers",
                extra={
                    "error": str(e),
                },
            )


if __name__ == "__main__":
    log.info("Beginning seed of installers...")
    asyncio.run(seed_installers())
    log.info("Process completed")
