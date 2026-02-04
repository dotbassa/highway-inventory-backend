from fastapi import UploadFile, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from pathlib import Path

from app.models.asset import Asset
from app.models.conflictive_asset import ConflictiveAsset
from app.schemas.asset import (
    PhotoUploadResponse,
    BulkPhotoUploadResponse,
)
from app.utils.photo_validation import (
    validate_photo_extensions,
    validate_photo_sizes,
    validate_request_limits,
    validate_photo_and_asset_length,
    generate_photo_name,
)
from app.core.config import (
    ASSET_PHOTOS_DIR,
    CONFLICTIVE_ASSET_PHOTOS_DIR,
)
from app.utils.logger import logger_instance as log


class PhotoUploadService:
    @staticmethod
    async def _get_assets_by_ids_internos(
        db: AsyncSession,
        ids_interno: List[int],
    ) -> List[Asset]:
        """
        Get multiple assets by their internal IDs.

        Args:
            db: Database session
            ids_interno: List of internal IDs

        Returns:
            List of Asset objects
        """
        query = select(Asset).where(Asset.id_interno.in_(ids_interno))
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def _get_conflictive_assets_by_ids_internos(
        db: AsyncSession,
        ids_interno: List[int],
    ) -> List[ConflictiveAsset]:
        """
        Get multiple conflictive assets by their internal IDs.

        Args:
            db: Database session
            ids_interno: List of internal IDs

        Returns:
            List of ConflictiveAsset objects
        """
        query = select(ConflictiveAsset).where(
            ConflictiveAsset.id_interno.in_(ids_interno)
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def _save_photo_to_filesystem_with_exception(
        photo: UploadFile,
        photo_name: str,
        conflictive_asset: bool = False,
    ) -> None:
        """
        Save photo to the filesystem (raises exception on error).
        Used for single photo upload where we want to rollback the entire transaction.

        Args:
            photo: Uploaded photo file
            photo_name: Name to save the photo as
            directory_path: Directory to save the photo in

        Raises:
            HTTPException: If there's an error saving the photo
        """
        try:
            if conflictive_asset:
                dir_path = Path(CONFLICTIVE_ASSET_PHOTOS_DIR)
            else:
                dir_path = Path(ASSET_PHOTOS_DIR)

            file_path = dir_path / photo_name

            content = await photo.read()

            with open(file_path, "wb") as f:
                f.write(content)

            await photo.seek(0)

        except Exception as e:
            log.error(
                "Error saving photo to filesystem",
                extra={
                    "photo_name": photo_name,
                    "directory": dir_path,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error saving photo to filesystem: {str(e)}",
            )

    @staticmethod
    async def _save_photo_to_filesystem_safe(
        photo: UploadFile,
        photo_name: str,
        conflictive_asset: bool = False,
    ) -> tuple[bool, Optional[str]]:
        """
        Save photo to the filesystem (returns success status, no exception).
        Used for bulk photo upload where we want to continue processing other photos.

        Args:
            photo: Uploaded photo file
            photo_name: Name to save the photo as
            directory_path: Directory to save the photo in

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            if conflictive_asset:
                dir_path = Path(CONFLICTIVE_ASSET_PHOTOS_DIR)
            else:
                dir_path = Path(ASSET_PHOTOS_DIR)

            file_path = dir_path / photo_name
            content = await photo.read()
            with open(file_path, "wb") as f:
                f.write(content)

            await photo.seek(0)

            return True, None

        except Exception as e:
            error_msg = f"Error saving photo: {str(e)}"
            log.error(
                "Error saving photo to filesystem (safe mode)",
                extra={
                    "photo_name": photo_name,
                    "directory": dir_path,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
                exc_info=True,
            )
            return False, error_msg

    @staticmethod
    async def _update_asset_photo(
        db: AsyncSession,
        photo_name: str | None,
        asset: Asset | ConflictiveAsset,
    ) -> Asset | ConflictiveAsset:
        asset.nombre_foto_codigo_barra = photo_name
        await db.flush()

        return asset

    @staticmethod
    async def _bulk_update_asset_photos(
        db: AsyncSession, updates: List[Dict[str, Any]], is_conflictive: bool = False
    ) -> List[int]:
        """
        Perform bulk update of photo names using PostgreSQL-style bulk operations.

        Args:
            db: Database session
            updates: List of dictionaries with 'id_interno' and 'photo_name'
            is_conflictive: Whether to update ConflictiveAsset table or Asset table

        Returns:
            List of successfully updated id_internos
        """
        if not updates:
            return []

        model_class = ConflictiveAsset if is_conflictive else Asset
        updated_ids = []

        try:
            for update_item in updates:
                stmt = (
                    update(model_class)
                    .where(model_class.id_interno == update_item["id_interno"])
                    .values(nombre_foto_codigo_barra=update_item["photo_name"])
                    .returning(model_class.id_interno)
                )
                result = await db.execute(stmt)
                updated_id = result.scalar_one_or_none()
                if updated_id:
                    updated_ids.append(updated_id)

        except Exception as e:
            log.error(
                f"Error in bulk update ({'conflictive' if is_conflictive else 'regular'} assets)",
                extra={"error": str(e), "update_count": len(updates)},
                exc_info=True,
            )
            raise

        return updated_ids

    @staticmethod
    async def single_photo_upload(
        db: AsyncSession,
        photo: UploadFile,
        asset: Asset | ConflictiveAsset,
    ) -> Asset | ConflictiveAsset:
        """
        Upload a single photo for an asset.

        This method:
        1. Validates the photo (extension and size)
        2. Generates the photo name
        3. Saves the photo to the filesystem
        4. Updates the asset's photo field in the database

        Args:
            db: Database session
            photo: Uploaded photo file
            asset: Asset object to associate the photo with
            directory_path: Directory to save the photo in

        Returns:
            Updated Asset object

        Raises:
            HTTPException: If validation fails or there's an error saving
        """
        try:
            photo_name = generate_photo_name(
                fecha_instalacion=asset.fecha_instalacion,
                id_interno=asset.id_interno,
                extension=photo.filename.split(".")[-1].lower(),
            )

            conflictive_asset = False
            if isinstance(asset, ConflictiveAsset):
                conflictive_asset = True

            await PhotoUploadService._save_photo_to_filesystem_with_exception(
                photo=photo,
                photo_name=photo_name,
                conflictive_asset=conflictive_asset,
            )

            updated_asset = await PhotoUploadService._update_asset_photo(
                db=db,
                asset=asset,
                photo_name=photo_name,
            )

            return updated_asset

        except HTTPException:
            raise
        except Exception as e:
            log.error(
                "Error in single photo upload",
                extra={
                    "asset_id": asset.id,
                    "id_interno": asset.id_interno,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error uploading photo: {str(e)}",
            )

    @staticmethod
    async def bulk_photo_upload(
        db: AsyncSession,
        ids_internos: List[int],
        photos: List[UploadFile],
    ) -> BulkPhotoUploadResponse:
        """
        Upload multiple photos for multiple assets in bulk.

        PHASE 1: Preparation & Validation
            - Validate request
            - Fetch all assets and conflictive assets
            - Build upload plan with photo names

        PHASE 2: Filesystem Operations
            - Save all photos to filesystem
            - Singular failures allowed
            - Track success/failure per photo

        PHASE 3: Bulk Database Updates
            - Use PostgreSQL bulk updates for better performance
            - Separate updates for regular assets and conflictive assets
            - Handle failures gracefully without rolling back successful operations

        PHASE 4: Reconciliation & Response
            - Ensure filesystem and database consistency
            - Build detailed response with per-item status

        Args:
            db: Database session
            ids_internos: List of asset internal IDs
            photos: List of UploadFile photos (must match ids_internos length and order)

        Returns:
            BulkPhotoUploadResponse with detailed results
        """

        # ==================== INPUT VALIDATION ====================
        validate_request_limits(photos)
        validate_photo_and_asset_length(ids_internos, photos)
        validate_photo_extensions(photos)
        await validate_photo_sizes(photos)

        log.info("Validation done, starting bulk photo upload")

        total_processed = len(ids_internos)
        results: List[PhotoUploadResponse] = []

        # ==================== PHASE 1: PREPARATION ====================

        # Fetch assets and conflictive assets
        assets = await PhotoUploadService._get_assets_by_ids_internos(db, ids_internos)
        conflictive_assets = (
            await PhotoUploadService._get_conflictive_assets_by_ids_internos(
                db, ids_internos
            )
        )

        assets_dict = {asset.id_interno: asset for asset in assets}
        conflictive_assets_dict = {
            asset.id_interno: asset for asset in conflictive_assets
        }

        # Build upload plan
        upload_plan: List[Dict[str, Any]] = []
        asset_not_found_ids = []

        for id_interno, photo in zip(ids_internos, photos):
            # Try regular asset first
            asset = assets_dict.get(id_interno)
            is_conflictive = False

            if not asset:
                # Try conflictive asset if not found in regular table
                asset = conflictive_assets_dict.get(id_interno)
                is_conflictive = True

                if not asset:
                    # Asset not found in either table
                    asset_not_found_ids.append(id_interno)
                    results.append(
                        PhotoUploadResponse(
                            success=False,
                            id_interno=id_interno,
                            photo_name=None,
                            error_message="Asset not found in regular or conflictive tables",
                        )
                    )
                    continue

            # Generate photo name
            photo_name = generate_photo_name(
                fecha_instalacion=asset.fecha_instalacion,
                id_interno=asset.id_interno,
                extension=photo.filename.split(".")[-1].lower(),
            )

            upload_plan.append(
                {
                    "asset": asset,
                    "photo": photo,
                    "photo_name": photo_name,
                    "is_conflictive": is_conflictive,
                    "id_interno": id_interno,
                }
            )

        log.info(
            f"Preparation phase completed. Planning to upload {len(upload_plan)} photos"
        )

        # ==================== PHASE 2: FILESYSTEM OPERATIONS ====================

        log.info("Starting filesystem save phase")

        successful_uploads: List[Dict[str, Any]] = []
        failed_filesystem_ids = []

        for plan_item in upload_plan:
            success, error_msg = (
                await PhotoUploadService._save_photo_to_filesystem_safe(
                    photo=plan_item["photo"],
                    photo_name=plan_item["photo_name"],
                    conflictive_asset=plan_item["is_conflictive"],
                )
            )

            if success:
                successful_uploads.append(plan_item)
            else:
                failed_filesystem_ids.append(plan_item["id_interno"])
                results.append(
                    PhotoUploadResponse(
                        success=False,
                        id_interno=plan_item["id_interno"],
                        photo_name=None,
                        error_message=error_msg,
                    )
                )

        log.info(
            f"Filesystem save phase completed. {len(successful_uploads)} photos saved successfully"
        )

        # ==================== PHASE 3: BULK DATABASE UPDATES ====================

        # Track which updates succeeded (initialize before conditional)
        successful_db_updates = set()
        failed_db_updates = []

        if not successful_uploads:
            log.info("No successful uploads to update in database")
        else:
            log.info("Starting bulk database update phase")

            # Separate regular assets from conflictive assets
            regular_assets_data = []
            conflictive_assets_data = []

            for item in successful_uploads:
                update_data = {
                    "id_interno": item["id_interno"],
                    "photo_name": item["photo_name"],
                }

                if item["is_conflictive"]:
                    conflictive_assets_data.append(update_data)
                else:
                    regular_assets_data.append(update_data)

            try:
                # Bulk update regular assets
                if regular_assets_data:
                    updated_regular_ids = (
                        await PhotoUploadService._bulk_update_asset_photos(
                            db=db, updates=regular_assets_data, is_conflictive=False
                        )
                    )
                    successful_db_updates.update(updated_regular_ids)

                    # Track failed updates
                    expected_regular_ids = {
                        item["id_interno"] for item in regular_assets_data
                    }
                    failed_regular_ids = expected_regular_ids - set(updated_regular_ids)
                    failed_db_updates.extend(failed_regular_ids)

                # Bulk update conflictive assets
                if conflictive_assets_data:
                    updated_conflictive_ids = (
                        await PhotoUploadService._bulk_update_asset_photos(
                            db=db, updates=conflictive_assets_data, is_conflictive=True
                        )
                    )
                    successful_db_updates.update(updated_conflictive_ids)

                    # Track failed updates
                    expected_conflictive_ids = {
                        item["id_interno"] for item in conflictive_assets_data
                    }
                    failed_conflictive_ids = expected_conflictive_ids - set(
                        updated_conflictive_ids
                    )
                    failed_db_updates.extend(failed_conflictive_ids)

                await db.commit()
                log.info(
                    f"Database update phase completed. {len(successful_db_updates)} records updated successfully"
                )

            except Exception as e:
                await db.rollback()
                log.error(
                    "Critical error in database update phase",
                    extra={"error": str(e)},
                    exc_info=True,
                )
                # Mark all successful filesystem uploads as failed due to DB error
                failed_db_updates.extend(
                    [item["id_interno"] for item in successful_uploads]
                )
                successful_db_updates.clear()

        # ==================== PHASE 4: RECONCILIATION & RESPONSE ====================

        # Build success responses for items that succeeded in both filesystem and DB
        for item in successful_uploads:
            if item["id_interno"] in successful_db_updates:
                results.append(
                    PhotoUploadResponse(
                        success=True,
                        id_interno=item["id_interno"],
                        photo_name=item["photo_name"],
                    )
                )
            else:
                # Filesystem succeeded but DB failed - this is inconsistent state
                results.append(
                    PhotoUploadResponse(
                        success=False,
                        id_interno=item["id_interno"],
                        photo_name=None,
                        error_message="Photo saved to filesystem but database update failed",
                    )
                )

        # Calculate final statistics
        total_successful = sum(1 for r in results if r.success)
        total_failed = total_processed - total_successful

        log.info(
            "Bulk photo upload completed",
            extra={
                "total_processed": total_processed,
                "total_successful": total_successful,
                "total_failed": total_failed,
                "asset_not_found": len(asset_not_found_ids),
                "filesystem_failures": len(failed_filesystem_ids),
                "database_failures": len(failed_db_updates),
            },
        )

        return BulkPhotoUploadResponse(
            total_processed=total_processed,
            total_successful=total_successful,
            total_failed=total_failed,
            results=results,
        )
