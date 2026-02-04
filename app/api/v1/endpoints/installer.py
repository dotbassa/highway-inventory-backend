from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.installer import (
    InstallerCreate,
    InstallerUpdate,
    InstallerResponse,
)
from app.schemas.shared_pagination_response import PaginatedResponse
from app.crud.installer import (
    create_installer,
    update_installer,
    delete_installer,
    get_installer_by_id_or_rut,
    get_installers,
)
from app.api.deps import get_db, require_admin
from app.utils.logger import logger_instance as log


router = APIRouter()


@router.post(
    "/",
    response_model=InstallerResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_installer_route(
    installer: InstallerCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        db_installer = await create_installer(db, installer)
        await db.commit()
        log.info(
            "Installer created successfully",
            extra={
                "installer_id": db_installer.id,
                "installer_rut": db_installer.rut,
            },
        )
        return db_installer
    except HTTPException as e:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        log.error(
            "Error creating installer",
            extra={
                "operation": "create",
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating installer",
        )


@router.patch(
    "/{id}",
    response_model=InstallerResponse,
    dependencies=[Depends(require_admin)],
)
async def update_installer_route(
    installer: InstallerUpdate,
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Update a installer by id, allows partial updates"""
    try:
        db_installer = await get_installer_by_id_or_rut(db, id=id)
        updated_installer = await update_installer(db, db_installer, installer)
        await db.commit()
        log.info(
            "Installer updated successfully",
            extra={
                "installer_id": id,
            },
        )
        return updated_installer
    except HTTPException as e:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        log.error(
            f"Error updating installer",
            extra={
                "operation": "update",
                "installer_id": id,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating installer",
        )


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_installer_route(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a installer by id"""
    try:
        db_installer = await get_installer_by_id_or_rut(db, id=id)
        await delete_installer(db, db_installer)
        await db.commit()
        log.info(
            "Installer deleted successfully",
            extra={
                "installer_id": id,
            },
        )
    except HTTPException as e:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        log.error(
            f"Error deleting installer",
            extra={
                "operation": "delete",
                "installer_id": id,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting installer",
        )


@router.get(
    "/{id}",
    response_model=InstallerResponse,
    dependencies=[Depends(require_admin)],
)
async def read_installer_by_id_route(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a installer by id"""
    try:
        installer = await get_installer_by_id_or_rut(db, id=id)
        return installer
    except HTTPException as e:
        raise
    except Exception as e:
        log.error(
            f"Error fetching installer by id",
            extra={
                "operation": "read one by id",
                "installer_id": id,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching installer",
        )


@router.get(
    "/rut/{rut}",
    response_model=InstallerResponse,
    dependencies=[Depends(require_admin)],
)
async def read_installer_by_rut_route(
    rut: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a installer by rut"""
    try:
        installer = await get_installer_by_id_or_rut(db, rut=rut)
        return installer
    except HTTPException as e:
        raise
    except Exception as e:
        log.error(
            f"Error fetching installer by rut",
            extra={
                "operation": "read one by rut",
                "installer_rut": rut,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching installer",
        )


@router.get(
    "/",
    response_model=PaginatedResponse[InstallerResponse],
    dependencies=[Depends(require_admin)],
)
async def read_installers_route(
    db: AsyncSession = Depends(get_db),
):
    """Get a list of all installers"""
    try:
        total_count, installers = await get_installers(db)
        return PaginatedResponse[InstallerResponse].create_unpaginated(
            items=installers,
            total=total_count,
        )
    except HTTPException as e:
        raise
    except Exception as e:
        log.error(
            f"Error fetching installers",
            extra={
                "operation": "read all",
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching installers",
        )
