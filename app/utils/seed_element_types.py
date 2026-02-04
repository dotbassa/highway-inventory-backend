import asyncio
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.element_type import ElementType
from app.db.database import SessionLocal
from app.utils.logger import logger_instance as log


ELEMENT_TYPES = [
    "Alcantarillas (cabezal de alcantarilla)",
    "Amortiguador de impacto",
    "Áreas de servicio y estacionamientos",
    "Arte público",
    "Bajadas de agua",
    "Barreras de contención",
    "Bermas",
    "Cámara de inspección (o de registro)",
    "Cercos",
    "Ciclovías",
    "Circuito cerrado de televisión (CCTV)",
    "Enlaces",
    "Faja vial",
    "Fosos y contrafosos",
    "Gabinete de emergencia",
    "Galerías en túnel",
    "Guardaganado",
    "Luminaria continua",
    "Luminarias",
    "Mallas antivandálicas",
    "Meteorológicos y ambientales",
    "Pantallas acústicas",
    "Paraderos de transporte público",
    "Pasarelas",
    "Pasos",
    "Pistas en áreas de servicio y estacionamiento",
    "Pistas en calles de servicio",
    "Pistas en lazos y ramales",
    "Pistas en troncal y vías secundarias",
    "Pistas en vía secundaria del enlace, cuello, retorno, conexión u otro",
    "Pistas en zona de cobro",
    "Postes SOS",
    "Puentes",
    "Casetas y pórticos (ex puntos de cobro)",
    "Sala eléctrica (shelter)",
    "Señales",
    "Señal de mensaje variable tipo bandera",
    "Señal de mensaje variable tipo pórtico",
    "Señalización vertical",
    "Sumideros",
    "Túnel",
    "Vallas peatonales",
    "Vehículos",
    "Ventilación en túnel y trincheras",
    "Ventilador a chorro",
    "Ventilador axial",
    "Vereda",
]


async def seed_element_types():
    async with SessionLocal() as session:
        session: AsyncSession
        try:
            result = await session.execute(select(ElementType.nombre))
            existing_names = {row[0] for row in result.all()}

            new_count = 0
            for nombre in ELEMENT_TYPES:
                if nombre not in existing_names:
                    element_type = ElementType(nombre=nombre)
                    session.add(element_type)
                    new_count += 1

            if new_count > 0:
                await session.commit()
                log.info(
                    f"Seeded {new_count} new element types, total: {len(ELEMENT_TYPES)}",
                )
            else:
                log.info("All element types already exist")

        except Exception as e:
            await session.rollback()
            log.error(
                f"Error seeding element types",
                extra={
                    "error": str(e),
                },
            )


if __name__ == "__main__":
    log.info("Seeding element types...")
    asyncio.run(seed_element_types())
    log.info("Proccess completed")
