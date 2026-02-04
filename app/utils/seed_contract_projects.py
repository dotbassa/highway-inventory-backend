import asyncio
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract_project import ContractProject
from app.db.database import SessionLocal
from app.utils.logger import logger_instance as log


CONTRACT_PROJECTS = [
    "NASA",
    "Túnel el Melón",
]


async def seed_contract_projects():
    async with SessionLocal() as session:
        session: AsyncSession
        try:
            result = await session.execute(select(ContractProject.nombre))
            existing_names = {row[0] for row in result.all()}

            new_count = 0
            for nombre in CONTRACT_PROJECTS:
                if nombre not in existing_names:
                    contract_project = ContractProject(nombre=nombre)
                    session.add(contract_project)
                    new_count += 1

            if new_count > 0:
                await session.commit()
                log.info(
                    f"Seeded {new_count} new contract projects, total: {len(CONTRACT_PROJECTS)}",
                )
            else:
                log.info("All contract projects already exist")

        except Exception as e:
            await session.rollback()
            log.error(
                f"Error seeding contract projects",
                extra={
                    "error": str(e),
                },
            )


if __name__ == "__main__":
    log.info("Beginning seed of contract projects...")
    asyncio.run(seed_contract_projects())
    log.info("Process completed")
