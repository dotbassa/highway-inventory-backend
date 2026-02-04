import asyncio
from datetime import datetime, timedelta
import random
from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.db.database import SessionLocal
from app.utils.logger import logger_instance as log
from app.enums.enums import RoadDirection, AssetStatus, BarcodePosition


fake = Faker("es_ES")


async def seed_fake_assets(num_assets: int = 1000):
    """
    Seeds the database with fake assets.

    Args:
        num_assets: Number of assets to create (default: 1000)
    """
    async with SessionLocal() as session:
        session: AsyncSession
        try:
            log.info(f"Starting seed of {num_assets} assets...")

            # Enum values lists for random selection
            road_directions = list(RoadDirection)
            asset_statuses = list(AssetStatus)
            barcode_positions = list(BarcodePosition)

            assets_to_create = []

            # Generate unique id_interno values starting from a high number to avoid conflicts
            base_id_interno = 1000000

            for i in range(num_assets):
                # Generate installation date in the last 2 years
                days_ago = random.randint(0, 730)
                fecha_instalacion = datetime.now().date() - timedelta(days=days_ago)

                # Generate GPS coordinates (Chile coordinates range approximately)
                # Latitude: -18 to -56, Longitude: -66 to -75
                lat = round(random.uniform(-56, -18), 6)
                lon = round(random.uniform(-75, -66), 6)
                georeferenciacion = f"{lat},{lon}"

                asset = Asset(
                    tag_bim=(
                        f"BIM-{base_id_interno + i}" if random.random() > 0.3 else None
                    ),
                    id_interno=base_id_interno + i,
                    descripcion=fake.sentence(nb_words=6),
                    fecha_instalacion=fecha_instalacion,
                    estado=random.choice(asset_statuses),
                    ubicacion_via=random.choice(road_directions),
                    ubicacion_codigo_barra=random.choice(barcode_positions),
                    nombre_foto_codigo_barra=(
                        "test.jpg" if random.random() > 0.2 else None
                    ),
                    georeferenciacion=georeferenciacion,
                    version=1,
                    contract_project_id=1,
                    element_type_id=1,
                    installer_id=1,
                    macro_location_id=None,
                )

                assets_to_create.append(asset)

                # Batch insert every 100 assets to avoid memory issues
                if len(assets_to_create) >= 100:
                    session.add_all(assets_to_create)
                    await session.flush()
                    log.info(f"Inserted batch: {i + 1}/{num_assets} assets")
                    assets_to_create = []

            # Insert remaining assets
            if assets_to_create:
                session.add_all(assets_to_create)

            await session.commit()
            log.info(f"Successfully seeded {num_assets} assets!")

        except Exception as e:
            await session.rollback()
            log.error(
                f"Error seeding assets",
                extra={
                    "error": str(e),
                },
            )
            raise


if __name__ == "__main__":
    log.info("Beginning seed of assets...")
    asyncio.run(seed_fake_assets(1000))
