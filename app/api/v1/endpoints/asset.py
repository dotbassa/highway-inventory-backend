from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
)
import openpyxl
from openpyxl.utils.exceptions import InvalidFileException
from fastapi.responses import Response, FileResponse
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date, timezone
from io import BytesIO
import json

from app.schemas.asset import (
    AssetCreate,
    AssetUpdate,
    AssetResponse,
    AssetDetailResponse,
    AssetBulkCreate,
    AssetSyncResponse,
    AssetSyncRequest,
    AssetSyncDataResponse,
    AssetSyncItem,
    BulkPhotoUploadResponse,
    AssetsReportRequest,
    ReportTaskResponse,
    ReportStatusResponse,
)
from app.schemas.shared_pagination_response import PaginatedResponse
from app.crud.asset import (
    create_asset,
    create_assets_bulk,
    update_asset,
    delete_asset,
    get_asset_by_id,
    get_asset_by_tag_bim,
    get_assets,
    get_assets_for_mobile_sync,
    get_assets_by_datetime_range,
)
from app.crud.contract_project import get_contract_project_by_id_or_nombre
from app.crud.element_type import get_element_type_by_id_or_nombre
from app.services.photo_upload import PhotoUploadService
from app.services.asset_report import (
    generate_excel_report,
    generate_installers_excel_report,
    generate_kmz_report,
)
from app.services.background_reports import (
    generate_excel_report_background,
    generate_installers_excel_report_background,
)
from app.utils.async_report_manager import (
    generate_task_id,
    create_pending_report,
    get_report_status,
    get_report_file_path,
    can_start_new_report,
    ReportStatus,
)
from app.api.deps import get_db, require_admin, require_any_authenticated
from app.utils.logger import logger_instance as log

router = APIRouter()


@router.post(
    "/",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_asset_route(
    asset: str = Form(...),
    photo_upload: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new asset.

    If photo_upload is provided, the photo will be validated, saved to the filesystem,
    and the asset's photo field will be updated. Everything happens within the same
    transaction, so if photo upload fails, the entire asset creation will be rolled back.

    Args:
        asset: JSON string containing the asset data (sent as form field)
        photo_upload: Optional photo file upload
        db: Database session
    """
    try:
        asset_data = json.loads(asset)
        asset_obj = AssetCreate(**asset_data)

        db_asset = await create_asset(db, asset_obj)

        if photo_upload is not None:
            log.info(
                "Photo upload detected for new asset",
                extra={
                    "asset_id": db_asset.id,
                    "id_interno": db_asset.id_interno,
                    "photo_report_filename": photo_upload.filename,
                },
            )

            db_asset = await PhotoUploadService.single_photo_upload(
                db=db,
                photo=photo_upload,
                asset=db_asset,
            )

        await db.commit()
        await db.refresh(db_asset)

        log.info(
            "Asset created successfully",
            extra={
                "asset_id": db_asset.id,
                "asset_id_interno": db_asset.id_interno,
                "photo_uploaded": photo_upload is not None,
                "photo_name": db_asset.nombre_foto_codigo_barra,
            },
        )

        return db_asset

    except json.JSONDecodeError as e:
        await db.rollback()
        log.error(
            "Invalid JSON in asset field",
            extra={"error": str(e), "asset_data": asset},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid JSON in asset field",
        )
    except HTTPException as e:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        log.error(
            "Error creating asset",
            extra={
                "operation": "create",
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating asset",
        )


@router.post(
    "/bulk/photos",
    response_model=BulkPhotoUploadResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_admin)],
)
async def bulk_photo_upload_route(
    ids_internos: str = Form(
        ..., description="Comma-separated list of asset internal IDs (e.g., 1,2,3,4)"
    ),
    photos: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload multiple photos for multiple assets in bulk.

    This endpoint is designed for mobile apps that work offline and need to upload
    photos after syncing assets. The photos are sent as UploadFile multipart form data.

    Optimized Strategy (4 phases):
    PHASE 1: Preparation & Validation
        - Validate request limits and photo constraints
        - Fetch all assets and conflictive assets in parallel
        - Build upload plan with photo names for found assets
        - Handle asset-not-found cases gracefully

    PHASE 2: Filesystem Operations
        - Save all photos to filesystem (safe mode, continues on individual failures)
        - Track success/failure per photo independently
        - Uses appropriate directory based on asset type (regular/conflictive)

    PHASE 3: Bulk Database Updates
        - Perform individual database updates for each successfully saved photo
        - Separate updates for regular assets and conflictive assets
        - Individual failures don't rollback other successful operations
        - Better performance than single transaction, more resilient than bulk transaction

    PHASE 4: Reconciliation & Response
        - Ensure filesystem and database consistency
        - Only mark as successful if BOTH filesystem save AND database update succeed
        - Detailed response with per-item status and error messages

    The database field `nombre_foto_codigo_barra` is the source of truth for photo existence.

    Args:
        ids_internos: Comma-separated string of asset internal IDs (e.g., "1,2,3,4")
        photos: List of photo files (must match ids_internos length and order)
        db: Database session

    Returns:
        BulkPhotoUploadResponse with detailed results including success/failure per item
    """
    try:
        try:
            ids_list = [int(id_str.strip()) for id_str in ids_internos.split(",")]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="ids_internos must be a comma-separated list of integers (e.g., '1,2,3')",
            )

        if len(ids_list) == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="ids_internos cannot be empty",
            )

        if len(ids_list) > 100:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="ids_internos cannot exceed 100 items",
            )

        result = await PhotoUploadService.bulk_photo_upload(
            db=db,
            ids_internos=ids_list,
            photos=photos,
        )

        log.info(
            "Bulk photo upload completed",
            extra={
                "total_processed": result.total_processed,
                "total_successful": result.total_successful,
                "total_failed": result.total_failed,
            },
        )

        return result

    except HTTPException as e:
        raise
    except Exception as e:
        log.error(
            "Error in bulk photo upload route",
            extra={
                "operation": "bulk_photo_upload",
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing bulk photo upload",
        )


@router.post(
    "/bulk/",
    response_model=AssetSyncResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_assets_bulk_route(
    assets_data: AssetBulkCreate,
    batch_size: int = 200,
    db: AsyncSession = Depends(get_db),
):
    """
    Create multiple assets in bulk.

    Returns:
    - created: Number of assets successfully inserted into asset table
    - conflictive: Number of assets inserted into conflictive_asset table (unique constraint conflicts)
    - failed: Number of assets that failed to insert into either table
    - failed_id_internos: List of id_internos that failed - mobile apps should retry these
    - total: Total number of assets processed
    """
    try:
        result = await create_assets_bulk(db, assets_data, batch_size)
        await db.commit()

        log.info(
            "Bulk asset creation completed",
            extra={
                "assets_created": result["created"],
                "assets_conflictive": result["conflictive"],
                "assets_failed": result["failed"],
                "assets_total": result["total"],
                "failed_id_internos": result.get("failed_id_internos", []),
            },
        )

        return AssetSyncResponse.model_validate(result)
    except HTTPException as e:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        log.error(
            "Error in bulk asset creation",
            extra={
                "operation": "bulk_create",
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating assets in bulk",
        )


@router.post(
    "/sync",
    response_model=AssetSyncDataResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_admin)],
)
async def sync_assets_route(
    sync_request: AssetSyncRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Synchronize assets for mobile apps based on installation date range.

    This endpoint is designed for offline mobile apps that need to sync
    their local database with the centralized cloud database.

    Strategy:
    1. Filter assets by fecha_instalacion date range (business logic filter)
    2. Exclude assets the client already has (efficiency filter)
    3. Return lightweight asset data (no relationships, no photos)
    4. Support pagination for large datasets

    Mobile App Usage:
    - Request assets from (current_max_date - 1 day) to handle edge cases
    - Send list of id_internos already in local DB for that date range
    - Receive only new/missing assets to update local database
    - Repeat with pagination if has_more = true

    Args:
        sync_request: Contains date range, exclusion list, and pagination params
        db: Database session

    Returns:
        AssetSyncDataResponse with assets and pagination metadata
    """
    try:
        assets, total_count = await get_assets_for_mobile_sync(
            db=db,
            fecha_instalacion_desde=sync_request.fecha_instalacion_desde,
            exclude_ids_internos=sync_request.exclude_ids_internos,
            limit=sync_request.limit,
            offset=sync_request.offset,
        )

        sync_assets = [AssetSyncItem.model_validate(asset) for asset in assets]

        returned_count = len(sync_assets)
        has_more = (sync_request.offset + returned_count) < total_count
        next_offset = sync_request.offset + returned_count if has_more else None

        response = AssetSyncDataResponse(
            assets=sync_assets,
            total_available=total_count,
            returned_count=returned_count,
            has_more=has_more,
            next_offset=next_offset,
        )

        log.info(
            "Asset sync completed",
            extra={
                "date": sync_request.fecha_instalacion_desde,
                "excluded_count": len(sync_request.exclude_ids_internos or []),
                "total_available": total_count,
                "returned_count": returned_count,
                "has_more": has_more,
                "offset": sync_request.offset,
                "limit": sync_request.limit,
            },
        )

        return response

    except HTTPException as e:
        raise
    except Exception as e:
        log.error(
            "Error in asset sync",
            extra={
                "operation": "sync_assets",
                "error_type": type(e).__name__,
                "error": str(e),
                "sync_request": sync_request.model_dump() if sync_request else None,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error synchronizing assets",
        )


@router.patch(
    "/{asset_id}",
    response_model=AssetResponse,
    dependencies=[Depends(require_admin)],
)
async def update_asset_route(
    asset_id: int,
    asset: str = Form(...),
    photo_upload: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    """ "Update an asset by ID, allows partial updates.

    If photo_upload is provided, the photo will be validated, saved to the filesystem,
    and the asset's photo field will be updated. Everything happens within the same
    transaction. If a photo already exists, it will be replaced.

    Args:
        asset_id: ID of the asset to update
        asset: JSON string containing the asset data (sent as form field)
        photo_upload: Optional photo file upload
        db: Database session
    """
    try:
        asset_data = json.loads(asset, strict=False)
        asset_obj = AssetUpdate(**asset_data)

        db_asset = await get_asset_by_id(db, asset_id)
        if not db_asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset with id {asset_id} not found",
            )

        updated_asset = await update_asset(db, db_asset, asset_obj)

        if photo_upload is not None:
            log.info(
                "Photo upload detected for asset update",
                extra={
                    "asset_id": updated_asset.id,
                    "id_interno": updated_asset.id_interno,
                    "photo_filename": photo_upload.filename,
                    "old_photo": updated_asset.nombre_foto_codigo_barra,
                },
            )

            updated_asset = await PhotoUploadService.single_photo_upload(
                db=db,
                photo=photo_upload,
                asset=updated_asset,
            )

        await db.commit()
        await db.refresh(updated_asset)

        log.info(
            "Asset updated successfully",
            extra={
                "asset_id": asset_id,
                "new_version": updated_asset.version,
                "photo_updated": photo_upload is not None,
                "photo_name": updated_asset.nombre_foto_codigo_barra,
            },
        )
        return updated_asset

    except json.JSONDecodeError as e:
        await db.rollback()
        log.error(
            "Invalid JSON in asset field",
            extra={"error": str(e), "asset_data": asset},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid JSON in asset field",
        )
    except HTTPException as e:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        log.error(
            f"Error updating asset",
            extra={
                "operation": "update",
                "asset_id": asset_id,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating asset with id {asset_id}",
        )


@router.delete(
    "/{asset_id}",
    response_model=AssetResponse,
    dependencies=[Depends(require_admin)],
)
async def delete_asset_route(
    asset_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Soft delete an asset by changing its status to 'retirado'"""
    try:
        db_asset = await get_asset_by_id(db, asset_id)
        if not db_asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset with id {asset_id} not found",
            )

        deleted_asset = await delete_asset(db, db_asset)
        await db.commit()

        log.info(
            "Asset soft deleted successfully",
            extra={
                "asset_id": asset_id,
                "new_status": deleted_asset.estado,
            },
        )
        return deleted_asset
    except HTTPException as e:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        log.error(
            f"Error deleting asset",
            extra={
                "operation": "delete",
                "asset_id": asset_id,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting asset with id {asset_id}",
        )


@router.get(
    "/{asset_id}",
    response_model=AssetResponse,
    dependencies=[Depends(require_admin)],
)
async def get_asset_route(
    asset_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get asset by ID"""
    try:
        db_asset = await get_asset_by_id(db, asset_id)
        if not db_asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset with id {asset_id} not found",
            )
        return db_asset
    except HTTPException as e:
        raise
    except Exception as e:
        log.error(
            f"Error retrieving asset",
            extra={
                "operation": "get",
                "asset_id": asset_id,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving asset with id {asset_id}",
        )


@router.get(
    "/by-tag-bim/{tag_bim}",
    response_model=AssetResponse,
)
async def get_asset_by_tag_bim_route(
    tag_bim: str,
    db: AsyncSession = Depends(get_db),
):
    """Get asset by BIM tag"""
    try:
        db_asset = await get_asset_by_tag_bim(db, tag_bim)
        if not db_asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset with tag_bim {tag_bim} not found",
            )
        return db_asset
    except HTTPException as e:
        raise
    except Exception as e:
        log.error(
            f"Error retrieving asset by tag_bim",
            extra={
                "operation": "get_by_tag_bim",
                "tag_bim": tag_bim,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving asset with tag_bim {tag_bim}",
        )


@router.get(
    "/",
    dependencies=[Depends(require_any_authenticated)],
)
async def get_assets_route(
    id_interno: Optional[int] = None,
    tag_bim: Optional[str] = None,
    fecha_instalacion_desde: Optional[date] = None,
    fecha_instalacion_hasta: Optional[date] = None,
    installer_id: Optional[int] = None,
    contract_project_id: Optional[int] = None,
    element_type_id: Optional[int] = None,
    macro_location_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    include_relationships: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """
    Get assets with pagination and filters.

    Returns different schemas based on include_relationships parameter:
    - include_relationships=False: AssetResponse (optimized, no relations loaded)
    - include_relationships=True: AssetDetailResponse (full details with relations)

    Use include_relationships=False (default) when:
    - Filtering/searching assets
    - You only need IDs, not full related objects
    - Performance is critical

    Use include_relationships=True when:
    - You need to display full details of related entities
    - Building detailed views or reports
    """
    try:
        total, assets = await get_assets(
            db,
            id_interno=id_interno,
            tag_bim=tag_bim,
            fecha_instalacion_desde=fecha_instalacion_desde,
            fecha_instalacion_hasta=fecha_instalacion_hasta,
            installer_id=installer_id,
            contract_project_id=contract_project_id,
            element_type_id=element_type_id,
            macro_location_id=macro_location_id,
            skip=skip,
            limit=limit,
            include_relationships=include_relationships,
        )

        response_model = AssetDetailResponse if include_relationships else AssetResponse
        validated_assets = [response_model.model_validate(asset) for asset in assets]

        return PaginatedResponse.create_paginated(
            items=validated_assets,
            total=total,
            page=(skip // limit) + 1,
            per_page=limit,
        )
    except Exception as e:
        log.error(
            f"Error retrieving assets",
            extra={
                "operation": "get_all",
                "skip": skip,
                "limit": limit,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving assets",
        )


@router.post(
    "/report/excel",
    response_model=ReportTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_admin)],
)
async def initiate_assets_excel_report(
    report_request: AssetsReportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Initiate async generation of Excel report of assets within a datetime range.
    Returns immediately with a task_id. Use GET /report/excel/{task_id}/status to check progress.
    """
    try:
        if (
            report_request.fecha_desde.tzinfo is None
            or report_request.fecha_hasta.tzinfo is None
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Las fechas deben incluir información de timezone",
            )

        fecha_desde_utc = report_request.fecha_desde.astimezone(timezone.utc)
        fecha_hasta_utc = report_request.fecha_hasta.astimezone(timezone.utc)

        time_difference = fecha_hasta_utc - fecha_desde_utc

        max_days = 90

        if time_difference.days > max_days:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"El rango de fechas no puede exceder {max_days} días",
            )

        if time_difference.total_seconds() < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="La fecha de inicio debe ser anterior a la fecha de fin",
            )

        can_start, reason = can_start_new_report()
        if not can_start:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=reason,
            )

        contract_project = await get_contract_project_by_id_or_nombre(
            db=db,
            nombre=report_request.contract_name,
        )

        if not contract_project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Proyecto de contrato '{report_request.contract_name}' no encontrado",
            )

        if report_request.element_type is not None:
            element_type = await get_element_type_by_id_or_nombre(
                db=db,
                nombre=report_request.element_type,
            )
            if not element_type:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tipo de elemento '{report_request.element_type}' no encontrado",
                )

        task_id = generate_task_id()

        if not create_pending_report(task_id):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al iniciar la generación del reporte",
            )

        background_tasks.add_task(
            generate_excel_report_background,
            task_id=task_id,
            contract_name=report_request.contract_name,
            fecha_desde=fecha_desde_utc,
            fecha_hasta=fecha_hasta_utc,
            include_photos=report_request.include_photos or False,
            element_type=report_request.element_type,
            asset_status=report_request.asset_status,
        )

        log.info(
            f"Excel report generation initiated",
            extra={
                "task_id": task_id,
                "contract_name": report_request.contract_name,
                "date_range_days": time_difference.days,
            },
        )

        return ReportTaskResponse(
            task_id=task_id,
            status=ReportStatus.PENDING,
            message="Generando reporte, por favor espere. Use el task_id para verificar el estado.",
        )

    except HTTPException as e:
        raise
    except Exception as e:
        log.error(
            "Error initiating Excel report generation",
            extra={
                "operation": "initiate_excel_report",
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al iniciar la generación del reporte",
        )


@router.post(
    "/report/excel/installers",
    response_model=ReportTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_admin)],
)
async def initiate_installers_excel_report(
    report_request: AssetsReportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Initiate async generation of installers Excel report within a datetime range.
    Returns immediately with a task_id. Use GET /report/excel/{task_id}/status to check progress.
    """
    try:
        if (
            report_request.fecha_desde.tzinfo is None
            or report_request.fecha_hasta.tzinfo is None
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Las fechas deben incluir información de timezone",
            )

        fecha_desde_utc = report_request.fecha_desde.astimezone(timezone.utc)
        fecha_hasta_utc = report_request.fecha_hasta.astimezone(timezone.utc)

        time_difference = fecha_hasta_utc - fecha_desde_utc

        max_days = 90

        if time_difference.days > max_days:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"El rango de fechas no puede exceder {max_days} días",
            )

        if time_difference.total_seconds() < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="La fecha de inicio debe ser anterior a la fecha de fin",
            )

        can_start, reason = can_start_new_report()
        if not can_start:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=reason,
            )

        contract_project = await get_contract_project_by_id_or_nombre(
            db=db,
            nombre=report_request.contract_name,
        )

        if not contract_project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Proyecto de contrato '{report_request.contract_name}' no encontrado",
            )

        task_id = generate_task_id()

        if not create_pending_report(task_id):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al iniciar la generación del reporte",
            )

        background_tasks.add_task(
            generate_installers_excel_report_background,
            task_id=task_id,
            contract_name=report_request.contract_name,
            fecha_desde=fecha_desde_utc,
            fecha_hasta=fecha_hasta_utc,
            element_type=report_request.element_type,
        )

        log.info(
            f"Installers Excel report generation initiated",
            extra={
                "task_id": task_id,
                "contract_name": report_request.contract_name,
            },
        )

        return ReportTaskResponse(
            task_id=task_id,
            status=ReportStatus.PENDING,
            message="Generando reporte de instaladores, por favor espere. Use el task_id para verificar el estado.",
        )

    except HTTPException as e:
        raise
    except Exception as e:
        log.error(
            "Error initiating installers Excel report generation",
            extra={
                "operation": "initiate_installers_report",
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al iniciar la generación del reporte",
        )


@router.get(
    "/report/excel/{task_id}/status",
    response_model=ReportStatusResponse,
    dependencies=[Depends(require_admin)],
)
async def get_excel_report_status(
    task_id: str,
):
    """
    Check the status of an Excel report generation task.

    Returns:
        - pending: Report is still being generated
        - completed: Report is ready to download
        - failed: Report generation failed
    """
    try:
        report_status, message = get_report_status(task_id)

        if report_status is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reporte no encontrado o expirado",
            )

        return ReportStatusResponse(
            task_id=task_id,
            status=report_status,
            message=message,
        )

    except HTTPException as e:
        raise
    except Exception as e:
        log.error(
            "Error checking report status",
            extra={
                "task_id": task_id,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al verificar el estado del reporte",
        )


@router.get(
    "/report/excel/{task_id}/download",
    dependencies=[Depends(require_admin)],
)
async def download_excel_report(
    task_id: str,
):
    """
    Download a completed Excel report.

    The report must be in 'completed' status. Use GET /report/excel/{task_id}/status
    to check the status first.
    """
    try:
        # Check report status
        report_status, message = get_report_status(task_id)

        if report_status is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reporte no encontrado o expirado",
            )

        if report_status == ReportStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_425_TOO_EARLY,
                detail="El reporte aún se está generando. Por favor intente más tarde.",
            )

        if report_status == ReportStatus.FAILED:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=message or "Error al generar el reporte",
            )

        # Get report file path
        file_path = get_report_file_path(task_id)

        if not file_path or not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Archivo del reporte no encontrado",
            )

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"reporte_activos_{timestamp}.xlsx"

        log.info(
            f"Downloading Excel report",
            extra={
                "task_id": task_id,
                "file_size_bytes": file_path.stat().st_size,
            },
        )

        return FileResponse(
            path=str(file_path),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=filename,
        )

    except HTTPException as e:
        raise
    except Exception as e:
        log.error(
            "Error downloading report",
            extra={
                "task_id": task_id,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al descargar el reporte",
        )


@router.post(
    "/report/kmz",
    dependencies=[Depends(require_admin)],
)
async def download_assets_kmz_report(
    report_request: Optional[str] = Form(None),
    excel_file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate and download a KMZ report of assets within a datetime range.

    Two modes of operation (mutually exclusive):
    1. Database query mode: Provide report_request (JSON with fecha_desde, fecha_hasta, contract_name)
    2. Excel file mode: Provide excel_file (.xlsx with columns: ID Interno, Elemento, Georeferenciación)n
    """
    try:
        if report_request is None and excel_file is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Debe proporcionar report_request o excel_file",
            )

        if report_request is not None and excel_file is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="report_request y excel_file son mutuamente exclusivos. Proporcione solo uno.",
            )

        contract_project = None

        if excel_file is not None:
            log.info(
                "Processing KMZ report from Excel file",
                extra={
                    "excel_filename": excel_file.filename,
                },
            )

            if not excel_file.filename.endswith(".xlsx"):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="El archivo debe ser de formato .xlsx",
                )

            content = await excel_file.read()
            excel_buffer = BytesIO(content)

            try:
                workbook = openpyxl.load_workbook(excel_buffer, read_only=True)
                sheet = workbook.active

                headers = {}
                for idx, cell in enumerate(sheet[1], start=1):
                    if cell.value:
                        headers[cell.value.strip()] = idx

                required_columns = ["ID Interno", "Elemento", "Georeferenciación"]
                missing_columns = [
                    col for col in required_columns if col not in headers
                ]

                if missing_columns:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail=f"El archivo Excel debe contener las siguientes columnas: {', '.join(missing_columns)}",
                    )

                assets_data = []
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    try:
                        id_interno = row[headers["ID Interno"] - 1]
                        elemento = row[headers["Elemento"] - 1]
                        georef = row[headers["Georeferenciación"] - 1]

                        if id_interno is not None and georef is not None:
                            assets_data.append(
                                {
                                    "id_interno": int(id_interno),
                                    "elemento": (
                                        str(elemento)
                                        if elemento
                                        else f"Elemento {id_interno}"
                                    ),
                                    "georeferenciacion": str(georef),
                                }
                            )
                    except (ValueError, TypeError, IndexError) as e:
                        log.warning(
                            "Skipping invalid row in Excel",
                            extra={"error": str(e), "row": row},
                        )
                        continue

                workbook.close()

                log.info(
                    "Excel file processed",
                    extra={"total_rows": len(assets_data)},
                )

                kmz_buffer = generate_kmz_report(assets_data=assets_data)

            except InvalidFileException:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="El archivo no es un archivo Excel válido",
                )
            except Exception as e:
                log.error(
                    "Error processing Excel file",
                    extra={
                        "error_type": type(e).__name__,
                        "error": str(e),
                    },
                    exc_info=True,
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error al procesar el archivo Excel",
                )
        else:
            try:
                report_data = json.loads(report_request)
                report_obj = AssetsReportRequest(**report_data)
            except json.JSONDecodeError as e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Invalid JSON in report_request field",
                )

            if (
                report_obj.fecha_desde.tzinfo is None
                or report_obj.fecha_hasta.tzinfo is None
            ):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Las fechas deben incluir información de timezone",
                )

            fecha_desde_utc = report_obj.fecha_desde.astimezone(timezone.utc)
            fecha_hasta_utc = report_obj.fecha_hasta.astimezone(timezone.utc)

            time_difference = fecha_hasta_utc - fecha_desde_utc

            max_days = 90

            if time_difference.days > max_days:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"El rango de fechas no puede exceder {max_days} días",
                )

            if time_difference.total_seconds() < 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="La fecha de inicio debe ser anterior a la fecha de fin",
                )

            contract_project = await get_contract_project_by_id_or_nombre(
                db=db,
                nombre=report_obj.contract_name,
            )

            element_type = None
            if report_obj.element_type is not None:
                element_type = await get_element_type_by_id_or_nombre(
                    db=db,
                    nombre=report_obj.element_type,
                )

            assets = await get_assets_by_datetime_range(
                db=db,
                contract_project_id=contract_project.id,
                fecha_desde=fecha_desde_utc,
                fecha_hasta=fecha_hasta_utc,
                element_type_id=element_type.id if element_type else None,
            )

            kmz_buffer = generate_kmz_report(assets=assets)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        contract_name = contract_project.nombre if contract_project else "activos"
        report_filename = f"reporte_kmz_{contract_name}_{timestamp}.kmz"

        return Response(
            content=kmz_buffer.getvalue(),
            media_type="application/vnd.google-earth.kmz",
            headers={"Content-Disposition": f"attachment; filename={report_filename}"},
        )

    except HTTPException as e:
        raise
    except Exception as e:
        log.error(
            "Error generating KMZ report",
            extra={
                "operation": "excel_report",
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating KMZ report",
        )
