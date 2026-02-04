from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Tuple, Optional

from app.models.macro_location import MacroLocation
from app.schemas.macro_location import MacroLocationCreate, MacroLocationUpdate
from app.decorators.sqlalchemy_error_handler import sqlalchemy_error_handler
from app.utils.logger import logger_instance as log


async def _check_uniqueness(
    db: AsyncSession,
    nombre: Optional[str] = None,
) -> bool:
    if not nombre:
        return None
    result = await db.execute(
        select(MacroLocation).where(MacroLocation.nombre == nombre)
    )
    if result.scalar_one_or_none():
        return True
    return False


@sqlalchemy_error_handler
async def create_macro_location(
    db: AsyncSession,
    macro_location: MacroLocationCreate,
) -> MacroLocation:
    existing_macro_location = await _check_uniqueness(db, macro_location.nombre)
    if existing_macro_location:
        log.error(
            f"Macro location already exists",
            extra={
                "macro_location_nombre": macro_location.nombre,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Macro location with nombre {macro_location.nombre} already exists",
        )

    db_macro_location = MacroLocation(**macro_location.model_dump())
    db.add(db_macro_location)
    return db_macro_location


@sqlalchemy_error_handler
async def update_macro_location(
    db: AsyncSession,
    db_macro_location: MacroLocation,
    macro_location: MacroLocationUpdate,
) -> MacroLocation:
    existing_macro_location = await _check_uniqueness(db, macro_location.nombre)
    if existing_macro_location:
        log.error(
            f"Macro location already exists",
            extra={
                "macro_location_nombre": macro_location.nombre,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Macro location with nombre {macro_location.nombre} already exists",
        )

    update_data = macro_location.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_macro_location, field, value)

    return db_macro_location


@sqlalchemy_error_handler
async def delete_macro_location(
    db: AsyncSession,
    db_macro_location: MacroLocation,
) -> None:
    db_macro_location.activo = False
    await db.flush()


@sqlalchemy_error_handler
async def get_macro_location_by_id_or_nombre(
    db: AsyncSession,
    id: Optional[int] = None,
    nombre: Optional[str] = None,
) -> MacroLocation:
    query = select(MacroLocation)
    if id:
        query = query.where(MacroLocation.id == id)
    elif nombre:
        query = query.where(MacroLocation.nombre == nombre.strip())
    else:
        log.error(
            "Either id or nombre must be provided to retrieve a macro_location",
            extra={
                "macro_location_id": id,
                "macro_location_nombre": nombre,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either id or nombre must be provided to retrieve a macro_location",
        )

    result = await db.execute(query)
    db_macro_location = result.scalar_one_or_none()
    if not db_macro_location:
        log.error(
            "Macro location not found",
            extra={
                "macro_location_id": id,
                "macro_location_nombre": nombre,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Macro location not found",
        )

    return db_macro_location


@sqlalchemy_error_handler
async def get_macro_locations(
    db: AsyncSession,
) -> Tuple[int, List[MacroLocation]]:
    result = await db.execute(
        select(MacroLocation).order_by(
            MacroLocation.activo.desc(), MacroLocation.nombre.asc()
        )
    )
    macro_locations = result.scalars().all()

    return len(macro_locations), macro_locations
