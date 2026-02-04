from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Tuple, Optional

from app.models.conflictive_asset import ConflictiveAsset
from app.decorators.sqlalchemy_error_handler import sqlalchemy_error_handler


@sqlalchemy_error_handler
async def delete_conflictive_asset(
    db: AsyncSession,
    db_conflictive_asset: ConflictiveAsset,
) -> None:
    await db.delete(db_conflictive_asset)


@sqlalchemy_error_handler
async def get_conflictive_asset_by_id(
    db: AsyncSession,
    asset_id: int,
) -> Optional[ConflictiveAsset]:
    result = await db.execute(
        select(ConflictiveAsset).where(ConflictiveAsset.id == asset_id)
    )
    return result.scalar_one_or_none()


@sqlalchemy_error_handler
async def get_conflictive_assets(
    db: AsyncSession,
) -> Tuple[List[ConflictiveAsset], int]:
    result = await db.execute(
        select(ConflictiveAsset).order_by(ConflictiveAsset.id.desc())
    )
    conflictive_asset = result.scalars().all()

    return len(conflictive_asset), conflictive_asset
