from app.schemas.contract_project import ContractProjectResponse
from app.schemas.element_type import ElementTypeResponse
from app.schemas.installer import InstallerResponse
from app.schemas.macro_location import MacroLocationResponse
from app.schemas.user import UserResponse
from app.schemas.asset import AssetResponse, AssetDetailResponse, AssetWithPhotoResponse
from app.schemas.conflictive_asset import ConflictiveAssetResponse

__all__ = [
    "ContractProjectResponse",
    "ElementTypeResponse",
    "InstallerResponse",
    "MacroLocationResponse",
    "UserResponse",
    "AssetResponse",
    "AssetDetailResponse",
    "AssetWithPhotoResponse",
    "ConflictiveAssetResponse",
]

# Rebuild models used on other modules to avoid circular imports
# Order matters: rebuild base models first, then dependent models
ContractProjectResponse.model_rebuild()
ElementTypeResponse.model_rebuild()
InstallerResponse.model_rebuild()
MacroLocationResponse.model_rebuild()
UserResponse.model_rebuild()
AssetResponse.model_rebuild()
AssetDetailResponse.model_rebuild()
AssetWithPhotoResponse.model_rebuild()
ConflictiveAssetResponse.model_rebuild()
