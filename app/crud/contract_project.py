from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Tuple, Optional

from app.models.contract_project import ContractProject
from app.schemas.contract_project import ContractProjectCreate, ContractProjectUpdate
from app.decorators.sqlalchemy_error_handler import sqlalchemy_error_handler
from app.utils.logger import logger_instance as log


async def _check_uniqueness(
    db: AsyncSession,
    nombre: Optional[str] = None,
) -> bool:
    if not nombre:
        return None
    result = await db.execute(
        select(ContractProject).where(ContractProject.nombre == nombre)
    )
    if result.scalar_one_or_none():
        return True
    return False


@sqlalchemy_error_handler
async def create_contract_project(
    db: AsyncSession,
    contract_project: ContractProjectCreate,
) -> ContractProject:
    existing_contract_project = await _check_uniqueness(db, contract_project.nombre)
    if existing_contract_project:
        log.error(
            f"Contract project already exists",
            extra={
                "contract_project_nombre": contract_project.nombre,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Contract project with nombre {contract_project.nombre} already exists",
        )

    db_contract_project = ContractProject(**contract_project.model_dump())
    db.add(db_contract_project)
    return db_contract_project


@sqlalchemy_error_handler
async def update_contract_project(
    db: AsyncSession,
    db_contract_project: ContractProject,
    contract_project: ContractProjectUpdate,
) -> ContractProject:
    existing_contract_project = await _check_uniqueness(db, contract_project.nombre)
    if existing_contract_project:
        log.error(
            f"Contract project already exists",
            extra={
                "contract_project_nombre": contract_project.nombre,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Contract project with nombre {contract_project.nombre} already exists",
        )

    update_data = contract_project.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_contract_project, field, value)

    return db_contract_project


@sqlalchemy_error_handler
async def delete_contract_project(
    db: AsyncSession,
    db_contract_project: ContractProject,
) -> None:
    db_contract_project.activo = False
    await db.flush()


@sqlalchemy_error_handler
async def get_contract_project_by_id_or_nombre(
    db: AsyncSession,
    id: Optional[int] = None,
    nombre: Optional[str] = None,
) -> ContractProject:
    query = select(ContractProject)
    if id:
        query = query.where(ContractProject.id == id)
    elif nombre:
        query = query.where(ContractProject.nombre == nombre.strip())
    else:
        log.error(
            "Either id or nombre must be provided to retrieve a contract_project",
            extra={
                "contract_project_id": id,
                "contract_project_nombre": nombre,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either id or nombre must be provided to retrieve a contract_project",
        )

    result = await db.execute(query)
    db_contract_project = result.scalar_one_or_none()
    if not db_contract_project:
        log.error(
            "Contract project not found",
            extra={
                "contract_project_id": id,
                "contract_project_nombre": nombre,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract project not found",
        )

    return db_contract_project


@sqlalchemy_error_handler
async def get_contract_projects(
    db: AsyncSession,
) -> Tuple[int, List[ContractProject]]:
    result = await db.execute(
        select(ContractProject).order_by(
            ContractProject.activo.desc(), ContractProject.nombre.asc()
        )
    )
    contract_projects = result.scalars().all()

    return len(contract_projects), contract_projects
