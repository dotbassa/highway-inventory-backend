import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app import models
from app.api.v1.api import api_router
from app.api.public.v1.api import public_api_router
from app.core.exception_handlers import setup_exception_handlers
from app.utils.photo_validation import ensure_upload_directories
from app.core.security import PermissionValidator
from app.utils.create_admin import create_admin_user

validate_permissions = PermissionValidator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_admin_user()
    yield


ENABLE_DEV_MODE = os.getenv("ENABLE_DEV_MODE", "false").lower() == "true"

app = FastAPI(
    title="Highway Asset Catalog API",
    root_path="/api",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if ENABLE_DEV_MODE else None,
    redoc_url="/redoc" if ENABLE_DEV_MODE else None,
    openapi_url="/openapi.json" if ENABLE_DEV_MODE else None,
)

ensure_upload_directories()

setup_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=(
        r".*" if ENABLE_DEV_MODE else r"^https://([a-z0-9-]+\.)?orgs_name\.cl$"
    ),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=3600,  # 1 hora en segundos
)

app.include_router(
    api_router,
    prefix="/v1",
    dependencies=[Depends(validate_permissions)],
)

app.include_router(
    public_api_router,
    prefix="/public/v1",
)
