from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.macro_location import (
    MacroLocationCreate,
    MacroLocationUpdate,
    MacroLocationResponse,
)
from app.schemas.shared_pagination_response import PaginatedResponse
from app.crud.macro_location import (
    create_macro_location,
    update_macro_location,
    delete_macro_location,
    get_macro_location_by_id_or_nombre,
    get_macro_locations,
)
from app.api.deps import get_db, require_admin
from app.utils.logger import logger_instance as log


router = APIRouter()


@router.post(
    "/",
    response_model=MacroLocationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_macro_location_route(
    macro_location: MacroLocationCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        db_macro_location = await create_macro_location(db, macro_location)
        await db.commit()
        log.info(
            "Macro location created successfully",
            extra={
                "macro_location_id": db_macro_location.id,
                "macro_location_nombre": db_macro_location.nombre,
            },
        )
        return db_macro_location
    except HTTPException as e:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        log.error(
            "Error creating macro location",
            extra={
                "operation": "create",
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating macro location",
        )


@router.patch(
    "/{id}",
    response_model=MacroLocationResponse,
    dependencies=[Depends(require_admin)],
)
async def update_macro_location_route(
    macro_location: MacroLocationUpdate,
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Update a macro location by id, allows partial updates"""
    try:
        db_macro_location = await get_macro_location_by_id_or_nombre(db, id=id)
        updated_macro_location = await update_macro_location(
            db, db_macro_location, macro_location
        )
        await db.commit()
        log.info(
            "Macro location updated successfully",
            extra={
                "macro_location_id": id,
            },
        )
        return updated_macro_location
    except HTTPException as e:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        log.error(
            f"Error updating macro location",
            extra={
                "operation": "update",
                "macro_location_id": id,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating macro location",
        )


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_macro_location_route(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a macro location by id"""
    try:
        db_macro_location = await get_macro_location_by_id_or_nombre(db, id=id)
        await delete_macro_location(db, db_macro_location)
        await db.commit()
        log.info(
            "Macro location deleted successfully",
            extra={
                "macro_location_id": id,
            },
        )
    except HTTPException as e:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        log.error(
            f"Error deleting macro location",
            extra={
                "operation": "delete",
                "macro_location_id": id,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting macro location",
        )


@router.get(
    "/{id}",
    response_model=MacroLocationResponse,
    dependencies=[Depends(require_admin)],
)
async def read_macro_location_by_id_route(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a macro location by id"""
    try:
        macro_location = await get_macro_location_by_id_or_nombre(db, id=id)
        return macro_location
    except HTTPException as e:
        raise
    except Exception as e:
        log.error(
            f"Error fetching macro location by id",
            extra={
                "operation": "read one by id",
                "macro_location_id": id,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching macro location",
        )


@router.get(
    "/nombre/{nombre}",
    response_model=MacroLocationResponse,
    dependencies=[Depends(require_admin)],
)
async def read_macro_location_by_nombre_route(
    nombre: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a macro location by nombre"""
    try:
        macro_location = await get_macro_location_by_id_or_nombre(db, nombre=nombre)
        return macro_location
    except HTTPException as e:
        raise
    except Exception as e:
        log.error(
            f"Error fetching macro location by nombre",
            extra={
                "operation": "read one by nombre",
                "macro_location_nombre": nombre,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching macro location",
        )


@router.get(
    "/",
    response_model=PaginatedResponse[MacroLocationResponse],
    dependencies=[Depends(require_admin)],
)
async def read_macro_locations_route(
    db: AsyncSession = Depends(get_db),
):
    """Get a list of all macro locations"""
    try:
        total_count, macro_locations = await get_macro_locations(db)
        return PaginatedResponse[MacroLocationResponse].create_unpaginated(
            items=macro_locations,
            total=total_count,
        )
    except HTTPException as e:
        raise
    except Exception as e:
        log.error(
            f"Error fetching macro locations",
            extra={
                "operation": "read all",
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching macro locations",
        )
