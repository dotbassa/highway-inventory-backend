from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.element_type import (
    ElementTypeCreate,
    ElementTypeUpdate,
    ElementTypeResponse,
)
from app.schemas.shared_pagination_response import PaginatedResponse
from app.crud.element_type import (
    create_element_type,
    update_element_type,
    delete_element_type,
    get_element_type_by_id_or_nombre,
    get_element_types,
)
from app.api.deps import get_db, require_admin
from app.utils.logger import logger_instance as log


router = APIRouter()


@router.post(
    "/",
    response_model=ElementTypeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_element_type_route(
    element_type: ElementTypeCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        db_element_type = await create_element_type(db, element_type)
        await db.commit()
        log.info(
            "Element type created successfully",
            extra={
                "element_type_id": db_element_type.id,
                "element_type_nombre": db_element_type.nombre,
            },
        )
        return db_element_type
    except HTTPException as e:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        log.error(
            "Error element type",
            extra={
                "operation": "create",
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error element type",
        )


@router.patch(
    "/{id}",
    response_model=ElementTypeResponse,
    dependencies=[Depends(require_admin)],
)
async def update_element_type_route(
    element_type: ElementTypeUpdate,
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Update an element type by id, allows partial updates"""
    try:
        db_element_type = await get_element_type_by_id_or_nombre(db, id=id)
        updated_element_type = await update_element_type(
            db, db_element_type, element_type
        )
        await db.commit()
        log.info(
            "Element type updated successfully",
            extra={
                "element_type_id": id,
            },
        )
        return updated_element_type
    except HTTPException as e:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        log.error(
            f"Error updating element type",
            extra={
                "operation": "update",
                "element_type_id": id,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating element type",
        )


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_element_type_route(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete an element type by id"""
    try:
        db_element_type = await get_element_type_by_id_or_nombre(db, id=id)
        await delete_element_type(db, db_element_type)
        await db.commit()
        log.info(
            "Element type deleted successfully",
            extra={
                "element_type_id": id,
            },
        )
    except HTTPException as e:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        log.error(
            f"Error deleting element type",
            extra={
                "operation": "delete",
                "element_type_id": id,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting element type",
        )


@router.get(
    "/{id}",
    response_model=ElementTypeResponse,
    dependencies=[Depends(require_admin)],
)
async def read_element_type_by_id_route(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get an element type by id"""
    try:
        element_type = await get_element_type_by_id_or_nombre(db, id=id)
        return element_type
    except HTTPException as e:
        raise
    except Exception as e:
        log.error(
            f"Error fetching element type by id",
            extra={
                "operation": "read one by id",
                "element_type_id": id,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching element type",
        )


@router.get(
    "/nombre/{nombre}",
    response_model=ElementTypeResponse,
    dependencies=[Depends(require_admin)],
)
async def read_element_type_by_nombre_route(
    nombre: str,
    db: AsyncSession = Depends(get_db),
):
    """Get an element type by nombre"""
    try:
        element_type = await get_element_type_by_id_or_nombre(db, nombre=nombre)
        return element_type
    except HTTPException as e:
        raise
    except Exception as e:
        log.error(
            f"Error fetching element type by nombre",
            extra={
                "operation": "read one by nombre",
                "element_type_nombre": nombre,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching element type",
        )


@router.get(
    "/",
    response_model=PaginatedResponse[ElementTypeResponse],
    dependencies=[Depends(require_admin)],
)
async def read_element_types_route(
    db: AsyncSession = Depends(get_db),
):
    """Get a list of all element types"""
    try:
        total_count, element_types = await get_element_types(db)
        return PaginatedResponse[ElementTypeResponse].create_unpaginated(
            items=element_types,
            total=total_count,
        )
    except HTTPException as e:
        raise
    except Exception as e:
        log.error(
            f"Error fetching element types",
            extra={
                "operation": "read all",
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching element types",
        )
