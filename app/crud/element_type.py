from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Tuple, Optional

from app.models.element_type import ElementType
from app.schemas.element_type import ElementTypeCreate, ElementTypeUpdate
from app.decorators.sqlalchemy_error_handler import sqlalchemy_error_handler
from app.utils.logger import logger_instance as log


async def _check_uniqueness(
    db: AsyncSession,
    nombre: Optional[str] = None,
) -> bool:
    if not nombre:
        return None
    result = await db.execute(select(ElementType).where(ElementType.nombre == nombre))
    if result.scalar_one_or_none():
        return True
    return False


@sqlalchemy_error_handler
async def create_element_type(
    db: AsyncSession,
    element_type: ElementTypeCreate,
) -> ElementType:
    existing_element_type = await _check_uniqueness(db, element_type.nombre)
    if existing_element_type:
        log.error(
            f"Element type already exists",
            extra={
                "element_type_nombre": element_type.nombre,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Element type with nombre {element_type.nombre} already exists",
        )

    db_element_type = ElementType(**element_type.model_dump())
    db.add(db_element_type)
    return db_element_type


@sqlalchemy_error_handler
async def update_element_type(
    db: AsyncSession,
    db_element_type: ElementType,
    element_type: ElementTypeUpdate,
) -> ElementType:
    existing_element_type = await _check_uniqueness(db, element_type.nombre)
    if existing_element_type:
        log.error(
            f"Element type already exists",
            extra={
                "element_type_nombre": element_type.nombre,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Element type with nombre {element_type.nombre} already exists",
        )

    update_data = element_type.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_element_type, field, value)

    return db_element_type


@sqlalchemy_error_handler
async def delete_element_type(
    db: AsyncSession,
    db_element_type: ElementType,
) -> None:
    db_element_type.activo = False
    await db.flush()


@sqlalchemy_error_handler
async def get_element_type_by_id_or_nombre(
    db: AsyncSession,
    id: Optional[int] = None,
    nombre: Optional[str] = None,
) -> ElementType:
    query = select(ElementType)
    if id:
        query = query.where(ElementType.id == id)
    elif nombre:
        query = query.where(ElementType.nombre == nombre.strip())
    else:
        log.error(
            "Either id or nombre must be provided to retrieve a element_type",
            extra={
                "element_type_id": id,
                "element_type_nombre": nombre,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either id or nombre must be provided to retrieve a element_type",
        )

    result = await db.execute(query)
    db_element_type = result.scalar_one_or_none()
    if not db_element_type:
        log.error(
            "Element type not found",
            extra={
                "element_type_id": id,
                "element_type_nombre": nombre,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Element type not found",
        )

    return db_element_type


@sqlalchemy_error_handler
async def get_element_types(
    db: AsyncSession,
) -> Tuple[int, List[ElementType]]:
    result = await db.execute(
        select(ElementType).order_by(
            ElementType.activo.desc(), ElementType.nombre.asc()
        )
    )
    element_types = result.scalars().all()

    return len(element_types), element_types
