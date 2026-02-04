from fastapi import APIRouter

from app.api.v1.endpoints import (
    asset,
    conflictive_asset,
    contract_project,
    element_type,
    installer,
    macro_location,
    master_data,
    user,
    health,
)

api_router = APIRouter()

api_router.include_router(
    asset.router,
    prefix="/assets",
    tags=["Assets"],
)
api_router.include_router(
    conflictive_asset.router,
    prefix="/conflictive-assets",
    tags=["Conflictive Assets"],
)
api_router.include_router(
    user.router,
    prefix="/users",
    tags=["Users"],
)
api_router.include_router(
    contract_project.router,
    prefix="/contract-projects",
    tags=["Contract Projects"],
)
api_router.include_router(
    element_type.router,
    prefix="/element-types",
    tags=["Element Types"],
)
api_router.include_router(
    installer.router,
    prefix="/installers",
    tags=["Installers"],
)
api_router.include_router(
    macro_location.router,
    prefix="/macro-locations",
    tags=["Macro Locations"],
)
api_router.include_router(
    master_data.router,
    prefix="/master-data",
    tags=["Master Data"],
)
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["Health Check"],
)
api_router.include_router(
    user.router,
    prefix="/auth",
    tags=["Auth"],
)
