from pydantic import BaseModel, ConfigDict
from typing import List

from app.schemas.element_type import ElementTypeResponse
from app.schemas.installer import InstallerResponse

# from app.schemas.macro_location import MacroLocationResponse
from app.schemas.contract_project import ContractProjectResponse


class MasterDataResponse(BaseModel):
    element_types: List[ElementTypeResponse]
    installers: List[InstallerResponse]
    # macro_locations: List[MacroLocationResponse]
    contract_projects: List[ContractProjectResponse]

    model_config = ConfigDict(
        extra="ignore",
        from_attributes=True,
    )
