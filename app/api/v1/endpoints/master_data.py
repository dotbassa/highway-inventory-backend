from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_any_authenticated
from app.schemas.master_data import MasterDataResponse
from app.crud import element_type as element_type_crud
from app.crud import installer as installer_crud

# from app.crud import macro_location as macro_location_crud
from app.crud import contract_project as contract_project_crud

router = APIRouter()


@router.get(
    "/",
    response_model=MasterDataResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_any_authenticated)],
    summary="Get all master data",
    description="Retrieve all records from master data tables",
)
async def get_master_data(
    db: AsyncSession = Depends(get_db),
):
    _, element_types = await element_type_crud.get_element_types(db)

    _, installers = await installer_crud.get_active_installers(db)

    # _, macro_locations = await macro_location_crud.get_macro_locations(db)

    _, contract_projects = await contract_project_crud.get_contract_projects(db)

    return MasterDataResponse(
        element_types=element_types,
        installers=installers,
        # macro_locations=macro_locations,
        contract_projects=contract_projects,
    )
