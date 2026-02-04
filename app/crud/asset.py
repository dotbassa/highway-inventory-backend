from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import and_, desc, asc, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError, DataError, DBAPIError
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime, timezone, date

from app.models.asset import Asset
from app.models.conflictive_asset import ConflictiveAsset
from app.schemas.asset import AssetCreate, AssetUpdate, AssetBulkCreate
from app.schemas.conflictive_asset import ConflictiveAssetCreate
from app.enums.enums import AssetStatus
from app.decorators.sqlalchemy_error_handler import sqlalchemy_error_handler
from app.utils.logger import logger_instance as log


async def _check_uniqueness(
    db: AsyncSession,
    id_interno: Optional[int] = None,
    tag_bim: Optional[str] = None,
    exclude_id: Optional[int] = None,
) -> bool:
    query_conditions = []

    if id_interno is not None:
        query_conditions.append(Asset.id_interno == id_interno)

    if tag_bim is not None:
        query_conditions.append(Asset.tag_bim == tag_bim)

    if not query_conditions:
        return False

    query = select(Asset.id).where(and_(*query_conditions))

    if exclude_id:
        query = query.where(Asset.id != exclude_id)

    result = await db.execute(query)
    return result.scalar_one_or_none() is not None


@sqlalchemy_error_handler
async def create_asset(
    db: AsyncSession,
    asset: AssetCreate,
) -> Asset:
    existing_asset = await _check_uniqueness(db, id_interno=asset.id_interno)
    if existing_asset:
        log.error(
            f"Asset already exists",
            extra={
                "asset_id_interno": asset.id_interno,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Asset with id_interno {asset.id_interno} already exists",
        )

    now = datetime.now(timezone.utc)
    asset_data = asset.model_dump()
    asset_data.update(
        {
            "version": 1,
            "created_at": now,
            "updated_at": now,
        }
    )

    db_asset = Asset(**asset_data)
    db.add(db_asset)
    return db_asset


async def create_assets_bulk(
    db: AsyncSession,
    assets_data: AssetBulkCreate,
    batch_size: int = 200,
) -> Dict[str, Any]:
    """
    Optimized bulk asset creation using PostgreSQL ON CONFLICT DO NOTHING.

    Strategy:
    1. Use PostgreSQL's ON CONFLICT DO NOTHING to handle duplicates efficiently
    2. Collect conflictive id_internos from the conflict detection
    3. Insert conflictive assets into conflictive_asset table after processing
    4. Comprehensive logging to track all operations and potential issues

    Returns:
    - created: Number of successfully inserted assets
    - conflictive: Number of assets moved to conflictive table
    - total: Total number of assets processed
    """
    assets = assets_data.assets
    total_assets = len(assets)

    if total_assets == 0:
        log.info("Bulk asset creation called with empty asset list")
        return {
            "created": 0,
            "conflictive": 0,
            "total": 0,
        }

    log.info(
        "Starting bulk asset creation",
        extra={
            "total_assets": total_assets,
            "batch_size": batch_size,
            "num_batches": (total_assets + batch_size - 1) // batch_size,
        },
    )

    try:
        now = datetime.now(timezone.utc)
        insert_data = []

        # Extract unique FK values for logging
        unique_contract_ids = set()
        unique_element_ids = set()
        unique_installer_ids = set()

        for asset in assets:
            asset_dict = asset.model_dump()
            asset_dict.update(
                {
                    "version": 1,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            insert_data.append(asset_dict)

            # Track FK values for validation logging
            unique_contract_ids.add(asset.contract_project_id)
            unique_element_ids.add(asset.element_type_id)
            unique_installer_ids.add(asset.installer_id)

        log.info(
            "Asset data prepared for insertion",
            extra={
                "unique_contract_project_ids": sorted(list(unique_contract_ids)),
                "unique_element_type_ids": sorted(list(unique_element_ids)),
                "unique_installer_ids": sorted(list(unique_installer_ids)),
            },
        )

        all_conflictive_id_internos = []
        all_inserted_id_internos = set()
        all_failed_id_internos = []
        batch_number = 0

        # Process in batches using ON CONFLICT DO NOTHING with RETURNING
        for i in range(0, len(insert_data), batch_size):
            batch = insert_data[i : i + batch_size]
            batch_number += 1

            log.debug(
                f"Processing batch {batch_number}",
                extra={
                    "batch_number": batch_number,
                    "batch_size": len(batch),
                    "offset": i,
                },
            )

            try:
                stmt = pg_insert(Asset).values(batch)
                stmt = stmt.on_conflict_do_nothing(index_elements=["id_interno"])
                stmt = stmt.returning(Asset.id_interno)

                result = await db.execute(stmt)
                inserted_id_internos = set(result.scalars().all())
                all_inserted_id_internos.update(inserted_id_internos)

                # Find conflictive id_internos by comparing batch with inserted ones
                batch_id_internos = {record["id_interno"] for record in batch}
                conflictive_in_batch = batch_id_internos - inserted_id_internos

                if conflictive_in_batch:
                    all_conflictive_id_internos.extend(conflictive_in_batch)
                    log.info(
                        f"Batch {batch_number}: Detected unique constraint conflicts",
                        extra={
                            "batch_number": batch_number,
                            "conflictive_count": len(conflictive_in_batch),
                            "conflictive_id_internos": sorted(
                                list(conflictive_in_batch)
                            ),
                            "inserted_count": len(inserted_id_internos),
                        },
                    )
                else:
                    log.debug(
                        f"Batch {batch_number}: All assets inserted successfully",
                        extra={
                            "batch_number": batch_number,
                            "inserted_count": len(inserted_id_internos),
                        },
                    )

            except IntegrityError as ie:
                # This should NOT happen for unique constraints (handled by ON CONFLICT)
                # This indicates FK, NOT NULL, or CHECK constraint violation
                orig_error = getattr(ie, "orig", ie)
                error_code = getattr(orig_error, "sqlstate", "unknown")
                error_detail = getattr(orig_error, "pgerror", str(ie))

                # Extract constraint name if available
                constraint_name = None
                if hasattr(orig_error, "diag"):
                    constraint_name = getattr(orig_error.diag, "constraint_name", None)

                # Track all assets in this batch as failed
                batch_id_internos = {record["id_interno"] for record in batch}
                all_failed_id_internos.extend(batch_id_internos)

                log.error(
                    f"Batch {batch_number}: IntegrityError during asset insert - marking batch as failed",
                    extra={
                        "batch_number": batch_number,
                        "batch_size": len(batch),
                        "error_code": error_code,
                        "constraint_name": constraint_name,
                        "error_type": type(orig_error).__name__,
                        "error_detail": error_detail,
                        "failed_id_internos": sorted(list(batch_id_internos)),
                    },
                    exc_info=True,
                )
                # Don't re-raise, continue processing other batches

            except DataError as de:
                # Data validation errors (enum, length, type mismatches)
                orig_error = getattr(de, "orig", de)
                error_code = getattr(orig_error, "sqlstate", "unknown")

                # Track all assets in this batch as failed
                batch_id_internos = {record["id_interno"] for record in batch}
                all_failed_id_internos.extend(batch_id_internos)

                log.error(
                    f"Batch {batch_number}: DataError during asset insert - marking batch as failed",
                    extra={
                        "batch_number": batch_number,
                        "batch_size": len(batch),
                        "error_code": error_code,
                        "error_type": type(orig_error).__name__,
                        "error": str(de),
                        "failed_id_internos": sorted(list(batch_id_internos)),
                    },
                    exc_info=True,
                )
                # Don't re-raise, continue processing other batches

        # Insert conflictive assets into conflictive_asset table using upsert
        conflictive_count = 0
        if all_conflictive_id_internos:
            log.info(
                "Preparing to insert conflictive assets",
                extra={
                    "conflictive_count": len(all_conflictive_id_internos),
                    "conflictive_id_internos": sorted(all_conflictive_id_internos),
                },
            )

            # Get the original asset objects for conflictive assets
            conflictive_assets = [
                asset
                for asset in assets
                if asset.id_interno in all_conflictive_id_internos
            ]

            cleaned_conflictive_data = []
            for asset in conflictive_assets:
                conflictive_schema = ConflictiveAssetCreate(**asset.model_dump())
                conflictive_dict = conflictive_schema.model_dump()
                conflictive_dict.update(
                    {
                        "created_at": now,
                        "updated_at": now,
                    }
                )
                cleaned_conflictive_data.append(conflictive_dict)

            try:
                # Use ON CONFLICT DO UPDATE for upsert behavior
                stmt = pg_insert(ConflictiveAsset).values(cleaned_conflictive_data)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["id_interno"],
                    set_=dict(stmt.excluded),
                )
                await db.execute(stmt)
                conflictive_count = len(cleaned_conflictive_data)

                log.info(
                    "Conflictive assets inserted successfully",
                    extra={
                        "conflictive_count": conflictive_count,
                        "operation": "upsert",
                    },
                )

            except IntegrityError as ie:
                # This should NEVER happen unless there's corrupted data
                # FK violations on conflictive table indicate serious data issues
                orig_error = getattr(ie, "orig", ie)
                error_code = getattr(orig_error, "sqlstate", "unknown")
                constraint_name = None
                if hasattr(orig_error, "diag"):
                    constraint_name = getattr(orig_error.diag, "constraint_name", None)

                # Mark all conflictive assets as failed since insert failed
                all_failed_id_internos.extend(all_conflictive_id_internos)

                log.critical(
                    "CRITICAL: IntegrityError during conflictive asset insert - marking all as failed",
                    extra={
                        "error_code": error_code,
                        "constraint_name": constraint_name,
                        "error_type": type(orig_error).__name__,
                        "error": str(ie),
                        "failed_id_internos": sorted(all_conflictive_id_internos),
                        "conflictive_data_sample": (
                            cleaned_conflictive_data[0]
                            if cleaned_conflictive_data
                            else None
                        ),
                    },
                    exc_info=True,
                )
                # Don't re-raise, return partial success with failed list

            except DataError as de:
                orig_error = getattr(de, "orig", de)
                error_code = getattr(orig_error, "sqlstate", "unknown")

                # Mark all conflictive assets as failed since insert failed
                all_failed_id_internos.extend(all_conflictive_id_internos)

                log.critical(
                    "CRITICAL: DataError during conflictive asset insert - marking all as failed",
                    extra={
                        "error_code": error_code,
                        "error_type": type(orig_error).__name__,
                        "error": str(de),
                        "failed_id_internos": sorted(all_conflictive_id_internos),
                        "conflictive_data_sample": (
                            cleaned_conflictive_data[0]
                            if cleaned_conflictive_data
                            else None
                        ),
                    },
                    exc_info=True,
                )
                # Don't re-raise, return partial success with failed list

        log.info(
            "Bulk asset creation completed successfully",
            extra={
                "total_assets": total_assets,
                "assets_created": len(all_inserted_id_internos),
                "assets_conflictive": conflictive_count,
                "assets_failed": len(all_failed_id_internos),
                "success_rate": f"{((len(all_inserted_id_internos) + conflictive_count) / total_assets * 100):.2f}%",
            },
        )

        return {
            "created": len(all_inserted_id_internos),
            "conflictive": conflictive_count,
            "total": total_assets,
            "failed": len(all_failed_id_internos),
            "failed_id_internos": sorted(all_failed_id_internos),
        }

    except (IntegrityError, DataError, DBAPIError) as db_error:
        # Database-specific errors already logged above with detail
        # Re-raise as HTTPException
        orig_error = getattr(db_error, "orig", db_error)
        error_code = getattr(orig_error, "sqlstate", "unknown")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database integrity error during asset creation (code: {error_code})",
        )

    except Exception as e:
        # Unexpected errors (should be very rare)
        log.error(
            "Unexpected error in bulk asset creation",
            extra={
                "error_type": type(e).__name__,
                "error": str(e),
                "total_assets": total_assets,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during asset creation: {str(e)}",
        )


@sqlalchemy_error_handler
async def update_asset(
    db: AsyncSession,
    db_asset: Asset,
    asset: AssetUpdate,
) -> Asset:
    if (asset.id_interno is not None and asset.id_interno != db_asset.id_interno) or (
        asset.tag_bim is not None and asset.tag_bim != db_asset.tag_bim
    ):
        existing_asset = await _check_uniqueness(
            db,
            id_interno=asset.id_interno,
            tag_bim=asset.tag_bim,
            exclude_id=db_asset.id,
        )
        if existing_asset:
            log.error(
                f"Asset with id_interno {asset.id_interno} or tag_bim {asset.tag_bim} already exists",
                extra={
                    "asset_id": db_asset.id,
                    "tag_bim": db_asset.tag_bim,
                    "update_id_interno": asset.id_interno,
                    "update_tag_bim": asset.tag_bim,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Asset with id_interno {asset.id_interno} or tag_bim {asset.tag_bim} already exists",
            )

    update_data = asset.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_asset, field, value)

    db_asset.version += 1

    return db_asset


@sqlalchemy_error_handler
async def delete_asset(
    db: AsyncSession,
    db_asset: Asset,
) -> Asset:
    db_asset.estado = AssetStatus.retirado
    db_asset.version += 1
    await db.flush()
    return db_asset


@sqlalchemy_error_handler
async def get_asset_by_id(
    db: AsyncSession,
    asset_id: int,
) -> Optional[Asset]:
    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    return result.scalar_one_or_none()


@sqlalchemy_error_handler
async def get_asset_by_id_interno(
    db: AsyncSession,
    id_interno: int,
) -> Optional[Asset]:
    result = await db.execute(select(Asset).where(Asset.id_interno == id_interno))
    return result.scalar_one_or_none()


@sqlalchemy_error_handler
async def get_asset_by_tag_bim(
    db: AsyncSession,
    tag_bim: str,
) -> Optional[Asset]:
    result = await db.execute(select(Asset).where(Asset.tag_bim == tag_bim))
    return result.scalar_one_or_none()


@sqlalchemy_error_handler
async def get_asset_details_by_id_interno(
    db: AsyncSession,
    asset_id_interno: int,
) -> Optional[Asset]:
    result = await db.execute(
        select(Asset)
        .options(
            selectinload(Asset.contract_project),
            selectinload(Asset.element_type),
            selectinload(Asset.installer),
            selectinload(Asset.macro_location),
        )
        .where(Asset.id_interno == asset_id_interno)
    )
    return result.scalar_one_or_none()


def _build_asset_filters(
    id_interno: Optional[int] = None,
    tag_bim: Optional[str] = None,
    fecha_instalacion_desde: Optional[date] = None,
    fecha_instalacion_hasta: Optional[date] = None,
    installer_id: Optional[int] = None,
    contract_project_id: Optional[int] = None,
    element_type_id: Optional[int] = None,
    macro_location_id: Optional[int] = None,
) -> List:
    filters = []

    if id_interno is not None:
        filters.append(Asset.id_interno == id_interno)

    if tag_bim is not None:
        filters.append(Asset.tag_bim == tag_bim)

    if fecha_instalacion_desde is not None:
        filters.append(Asset.fecha_instalacion >= fecha_instalacion_desde)

    if fecha_instalacion_hasta is not None:
        filters.append(Asset.fecha_instalacion <= fecha_instalacion_hasta)

    if installer_id is not None:
        filters.append(Asset.installer_id == installer_id)

    if contract_project_id is not None:
        filters.append(Asset.contract_project_id == contract_project_id)

    if element_type_id is not None:
        filters.append(Asset.element_type_id == element_type_id)

    if macro_location_id is not None:
        filters.append(Asset.macro_location_id == macro_location_id)

    filters.append(Asset.estado != AssetStatus.retirado)

    return filters


@sqlalchemy_error_handler
async def get_assets(
    db: AsyncSession,
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
) -> Tuple[int, List[Asset]]:

    filters = _build_asset_filters(
        id_interno=id_interno,
        tag_bim=tag_bim,
        fecha_instalacion_desde=fecha_instalacion_desde,
        fecha_instalacion_hasta=fecha_instalacion_hasta,
        installer_id=installer_id,
        contract_project_id=contract_project_id,
        element_type_id=element_type_id,
        macro_location_id=macro_location_id,
    )

    query = select(Asset)
    count_query = select(func.count(Asset.id))

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    if include_relationships:
        query = query.options(
            selectinload(Asset.contract_project),
            selectinload(Asset.element_type),
            selectinload(Asset.installer),
            selectinload(Asset.macro_location),
        )

    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    if total == 0:
        return 0, []

    query = query.order_by(desc(Asset.created_at))
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    assets = result.scalars().all()

    return total, list(assets)


@sqlalchemy_error_handler
async def get_assets_for_mobile_sync(
    db: AsyncSession,
    fecha_instalacion_desde: date,
    exclude_ids_internos: Optional[List[int]] = None,
    limit: int = 1000,
    offset: int = 0,
) -> Tuple[List[Asset], int]:
    """
    Get assets for mobile app synchronization based on installation date range
    and excluding assets the client already has.

    Args:
        db: Database session
        fecha_instalacion_desde: Start date for filtering (inclusive)
        fecha_instalacion_hasta: End date for filtering (inclusive), defaults to desde if not provided
        exclude_ids_internos: List of id_internos to exclude from results
        limit: Maximum number of assets to return
        offset: Number of assets to skip for pagination

    Returns:
        Tuple of (assets_list, total_count)
    """
    # Default end date to start date if not provided
    if fecha_instalacion_hasta is None:
        fecha_instalacion_hasta = fecha_instalacion_desde

    # Base query - no relationships loaded for performance
    query = select(Asset)
    count_query = select(func.count(Asset.id))

    # Date range filter
    date_conditions = [
        Asset.fecha_instalacion >= fecha_instalacion_desde,
        Asset.fecha_instalacion <= fecha_instalacion_hasta,
    ]

    # Exclude assets client already has
    if exclude_ids_internos:
        exclude_condition = ~Asset.id_interno.in_(exclude_ids_internos)
        date_conditions.append(exclude_condition)

    # Apply filters
    filter_condition = and_(*date_conditions)
    query = query.where(filter_condition)
    count_query = count_query.where(filter_condition)

    # Apply ordering (installation date, then id for consistency)
    query = query.order_by(Asset.fecha_instalacion.asc(), Asset.id.asc())

    # Apply pagination
    query = query.offset(offset).limit(limit)

    # Execute queries
    result = await db.execute(query)
    count_result = await db.execute(count_query)

    assets = list(result.scalars().all())
    total = count_result.scalar()

    return assets, total


@sqlalchemy_error_handler
async def get_assets_by_datetime_range(
    db: AsyncSession,
    contract_project_id: int,
    fecha_desde: datetime,
    fecha_hasta: datetime,
    element_type_id: Optional[int] = None,
    asset_status: Optional[AssetStatus] = None,
) -> List[Asset]:

    filters = [
        Asset.contract_project_id == contract_project_id,
        Asset.created_at >= fecha_desde,
        Asset.created_at <= fecha_hasta,
    ]

    if element_type_id is not None:
        filters.append(Asset.element_type_id == element_type_id)

    if asset_status is not None:
        filters.append(Asset.estado == asset_status)

    query = (
        select(Asset)
        .options(
            selectinload(Asset.contract_project),
            selectinload(Asset.element_type),
            selectinload(Asset.installer),
            selectinload(Asset.macro_location),
        )
        .where(and_(*filters))
        .order_by(desc(Asset.created_at))
    )

    result = await db.execute(query)
    assets = list(result.scalars().all())

    return assets
