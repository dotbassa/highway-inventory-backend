from fastapi import APIRouter

from app.api.public.v1.endpoints import asset, auth, health

public_api_router = APIRouter()

public_api_router.include_router(
    health.router,
    prefix="/health",
    tags=["Public - Health"],
)
public_api_router.include_router(
    asset.router,
    prefix="/assets",
    tags=["Public - Asset"],
)
public_api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Public - Auth"],
)
