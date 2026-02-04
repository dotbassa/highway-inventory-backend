from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.contract_project import (
    ContractProjectCreate,
    ContractProjectUpdate,
    ContractProjectResponse,
)
from app.schemas.shared_pagination_response import PaginatedResponse
from app.crud.contract_project import (
    create_contract_project,
    update_contract_project,
    delete_contract_project,
    get_contract_project_by_id_or_nombre,
    get_contract_projects,
)
from app.api.deps import get_db, require_admin
from app.utils.logger import logger_instance as log


router = APIRouter()


@router.post(
    "/",
    response_model=ContractProjectResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_contract_project_route(
    contract_project: ContractProjectCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        db_contract_project = await create_contract_project(db, contract_project)
        await db.commit()
        log.info(
            "Contract project created successfully",
            extra={
                "contract_project_id": db_contract_project.id,
                "contract_project_nombre": db_contract_project.nombre,
            },
        )
        return db_contract_project
    except HTTPException as e:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        log.error(
            "Error creating contract project",
            extra={
                "operation": "create",
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating contract project",
        )


@router.get(
    "/nombre/{nombre}",
    response_model=ContractProjectResponse,
    dependencies=[Depends(require_admin)],
)
async def read_contract_project_by_nombre_route(
    nombre: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a contract project by nombre"""
    try:
        contract_project = await get_contract_project_by_id_or_nombre(db, nombre=nombre)
        return contract_project
    except HTTPException as e:
        raise
    except Exception as e:
        log.error(
            f"Error fetching contract project by nombre",
            extra={
                "operation": "read one by nombre",
                "contract_project_nombre": nombre,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching contract project",
        )


@router.get(
    "/{id}",
    response_model=ContractProjectResponse,
    dependencies=[Depends(require_admin)],
)
async def read_contract_project_by_id_route(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a contract project by id"""
    try:
        contract_project = await get_contract_project_by_id_or_nombre(db, id=id)
        return contract_project
    except HTTPException as e:
        raise
    except Exception as e:
        log.error(
            f"Error fetching contract project by id",
            extra={
                "operation": "read one by id",
                "contract_project_id": id,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching contract project",
        )


@router.get(
    "/",
    response_model=PaginatedResponse[ContractProjectResponse],
    dependencies=[Depends(require_admin)],
)
async def read_contract_projects_route(
    db: AsyncSession = Depends(get_db),
):
    """Get a list of all contract projects"""
    try:
        total_count, contract_projects = await get_contract_projects(db)
        return PaginatedResponse[ContractProjectResponse].create_unpaginated(
            items=contract_projects,
            total=total_count,
        )
    except HTTPException as e:
        raise
    except Exception as e:
        log.error(
            f"Error fetching contract projects",
            extra={
                "operation": "read all",
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching contract projects",
        )


@router.patch(
    "/{id}",
    response_model=ContractProjectResponse,
    dependencies=[Depends(require_admin)],
)
async def update_contract_project_route(
    contract_project: ContractProjectUpdate,
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Update a contract project by id, allows partial updates"""
    try:
        db_contract_project = await get_contract_project_by_id_or_nombre(db, id=id)
        updated_contract_project = await update_contract_project(
            db, db_contract_project, contract_project
        )
        await db.commit()
        log.info(
            "Contract project updated successfully",
            extra={
                "contract_project_id": id,
            },
        )
        return updated_contract_project
    except HTTPException as e:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        log.error(
            f"Error updating contract project",
            extra={
                "operation": "update",
                "contract_project_id": id,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating contract project",
        )


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_contract_project_route(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a contract project by id"""
    try:
        db_contract_project = await get_contract_project_by_id_or_nombre(db, id=id)
        await delete_contract_project(db, db_contract_project)
        await db.commit()
        log.info(
            "Contract project deleted successfully",
            extra={
                "contract_project_id": id,
            },
        )
    except HTTPException as e:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        log.error(
            f"Error deleting contract project",
            extra={
                "operation": "delete",
                "contract_project_id": id,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting contract project",
        )
