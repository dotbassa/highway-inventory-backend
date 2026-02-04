from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
import base64

from app.schemas import AssetDetailResponse, AssetWithPhotoResponse
from app.enums.enums import AssetStatus
from app.crud.asset import get_asset_details_by_id_interno
from app.api.deps import get_db
from app.utils.logger import logger_instance as log
from app.core.config import ASSET_PHOTOS_DIR

router = APIRouter()


@router.get(
    "/by-id-interno/{id_interno}",
    response_model=AssetWithPhotoResponse,
)
async def get_asset_by_id_interno_route(
    id_interno: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get asset by internal ID with photo in base64 format.

    This endpoint is designed for mobile apps that scan barcodes.
    If the asset has an associated photo in the filesystem, it will be
    included in the response as a base64 encoded string.
    """
    try:
        db_asset = await get_asset_details_by_id_interno(db, id_interno)
        if not db_asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset with id_interno {id_interno} not found",
            )

        if db_asset.estado == AssetStatus.retirado:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Asset {id_interno} is not available for viewing, contact support",
            )

        asset = AssetDetailResponse.model_validate(db_asset)
        photo_base64 = None

        if asset.nombre_foto_codigo_barra is not None:
            photo_path = Path(ASSET_PHOTOS_DIR) / asset.nombre_foto_codigo_barra

            if photo_path.exists() and photo_path.is_file():
                try:
                    with open(photo_path, "rb") as photo_file:
                        photo_bytes = photo_file.read()
                        photo_base64 = base64.b64encode(photo_bytes).decode("utf-8")
                except Exception as photo_error:
                    log.warning(
                        "Failed to load photo for asset",
                        extra={
                            "id_interno": id_interno,
                            "photo_name": asset.nombre_foto_codigo_barra,
                            "photo_path": str(photo_path),
                            "error": str(photo_error),
                        },
                    )
            else:
                log.warning(
                    "Photo file not found in filesystem",
                    extra={
                        "id_interno": id_interno,
                        "photo_name": asset.nombre_foto_codigo_barra,
                        "photo_path": str(photo_path),
                    },
                )

        return AssetWithPhotoResponse(
            **asset.model_dump(),
            photo_base64=photo_base64,
        )

    except HTTPException as e:
        raise
    except Exception as e:
        log.error(
            f"Error retrieving asset by id_interno",
            extra={
                "operation": "get_by_id_interno",
                "id_interno": id_interno,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving asset with id_interno {id_interno}",
        )
