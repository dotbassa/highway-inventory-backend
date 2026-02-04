from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Tuple, Optional

from app.models.installer import Installer
from app.schemas.installer import InstallerCreate, InstallerUpdate
from app.decorators.sqlalchemy_error_handler import sqlalchemy_error_handler
from app.utils.logger import logger_instance as log


async def _check_uniqueness(
    db: AsyncSession,
    rut: Optional[str] = None,
) -> bool:
    if not rut:
        return None
    result = await db.execute(select(Installer).where(Installer.rut == rut))
    if result.scalar_one_or_none():
        return True
    return False


@sqlalchemy_error_handler
async def create_installer(
    db: AsyncSession,
    installer: InstallerCreate,
) -> Installer:
    existing_installer = await _check_uniqueness(db, installer.rut)
    if existing_installer:
        log.error(
            f"Installer already exists",
            extra={
                "installer_rut": installer.rut,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Installer with rut {installer.rut} already exists",
        )

    db_installer = Installer(**installer.model_dump())
    db.add(db_installer)
    return db_installer


@sqlalchemy_error_handler
async def update_installer(
    db: AsyncSession,
    db_installer: Installer,
    installer: InstallerUpdate,
) -> Installer:
    existing_installer = await _check_uniqueness(db, installer.rut)
    if existing_installer:
        log.error(
            f"Installer already exists",
            extra={
                "installer_rut": installer.rut,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Installer with rut {installer.rut} already exists",
        )

    update_data = installer.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_installer, field, value)

    return db_installer


@sqlalchemy_error_handler
async def delete_installer(
    db: AsyncSession,
    db_installer: Installer,
) -> None:
    db_installer.activo = False
    await db.flush()


@sqlalchemy_error_handler
async def get_installer_by_id_or_rut(
    db: AsyncSession,
    id: Optional[int] = None,
    rut: Optional[str] = None,
) -> Installer:
    query = select(Installer)
    if id:
        query = query.where(Installer.id == id)
    elif rut:
        query = query.where(Installer.rut == rut.strip())
    else:
        log.error(
            "Either id or rut must be provided to retrieve a installer",
            extra={
                "installer_id": id,
                "installer_rut": rut,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either id or rut must be provided to retrieve a installer",
        )

    result = await db.execute(query)
    db_installer = result.scalar_one_or_none()
    if not db_installer:
        log.error(
            "Installer not found",
            extra={
                "installer_id": id,
                "installer_rut": rut,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Installer not found",
        )

    return db_installer


@sqlalchemy_error_handler
async def get_installers(
    db: AsyncSession,
) -> Tuple[int, List[Installer]]:
    result = await db.execute(
        select(Installer).order_by(Installer.activo.desc(), Installer.nombre.asc())
    )
    installers = result.scalars().all()

    return len(installers), installers


@sqlalchemy_error_handler
async def get_active_installers(
    db: AsyncSession,
) -> Tuple[int, List[Installer]]:
    result = await db.execute(
        select(Installer).where(Installer.activo == True).order_by(Installer.id.desc())
    )
    installers = result.scalars().all()

    return len(installers), installers
