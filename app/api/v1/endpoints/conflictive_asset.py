from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.conflictive_asset import ConflictiveAssetResponse
from app.schemas.shared_pagination_response import PaginatedResponse
from app.crud.conflictive_asset import (
    delete_conflictive_asset,
    get_conflictive_asset_by_id,
    get_conflictive_assets,
)
from app.api.deps import get_db, require_admin
from app.utils.logger import logger_instance as log


router = APIRouter()


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_conflictive_asset_route(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete an element type by id"""
    try:
        db_conflictive_asset = await get_conflictive_asset_by_id(db, id=id)
        await delete_conflictive_asset(db, db_conflictive_asset)
        await db.commit()
        log.info(
            "Element type deleted successfully",
            extra={
                "conflictive_asset_id": id,
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
                "conflictive_asset_id": id,
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
    "/",
    response_model=PaginatedResponse[ConflictiveAssetResponse],
    dependencies=[Depends(require_admin)],
)
async def read_conflictive_assets_route(
    db: AsyncSession = Depends(get_db),
):
    """Get a list of all element types"""
    try:
        total_count, conflictive_assets = await get_conflictive_assets(db)
        return PaginatedResponse[ConflictiveAssetResponse].create_unpaginated(
            items=conflictive_assets,
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
