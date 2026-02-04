from fastapi import HTTPException, status, UploadFile
from typing import List
from datetime import date
from pathlib import Path

from app.core.config import (
    ASSET_PHOTOS_DIR,
    CONFLICTIVE_ASSET_PHOTOS_DIR,
    MAX_PHOTOS_PER_REQUEST,
    ALLOWED_EXTENSIONS,
    MAX_PHOTO_FILE_SIZE,
)

ALLOWED_EXTENSIONS_LIST = ALLOWED_EXTENSIONS.split(",")


def ensure_upload_directories() -> None:
    Path(ASSET_PHOTOS_DIR).mkdir(parents=True, exist_ok=True)
    Path(CONFLICTIVE_ASSET_PHOTOS_DIR).mkdir(parents=True, exist_ok=True)


def validate_request_limits(
    photos: List[UploadFile],
) -> None:
    if len(photos) > MAX_PHOTOS_PER_REQUEST:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_PHOTOS_PER_REQUEST} photos allowed per request",
        )


def validate_photo_extension(
    photo: UploadFile,
) -> None:
    if not photo.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Photo filename is required",
        )

    extension = photo.filename.split(".")[-1].lower()

    if extension not in ALLOWED_EXTENSIONS_LIST:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file extension. Allowed: {', '.join(ALLOWED_EXTENSIONS_LIST)}",
        )


def validate_photo_extensions(
    photos: List[UploadFile],
) -> None:
    for photo in photos:
        validate_photo_extension(photo)


async def validate_photo_size(
    photo: UploadFile,
) -> None:
    content = await photo.read()
    file_size = len(content)

    await photo.seek(0)

    if file_size > MAX_PHOTO_FILE_SIZE:
        max_size_mb = MAX_PHOTO_FILE_SIZE / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Photo size exceeds {max_size_mb}MB limit",
        )


async def validate_photo_sizes(
    photos: List[UploadFile],
) -> None:
    for photo in photos:
        await validate_photo_size(photo)


def validate_photo_and_asset_length(
    ids_internos: List[int],
    photos: List[UploadFile],
) -> None:
    if len(ids_internos) != len(photos):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The number of ids_internos must match the number of photos",
        )


def generate_photo_name(
    fecha_instalacion: date,
    id_interno: int,
    extension: str,
) -> str:
    formatted_date = fecha_instalacion.strftime("%Y%m%d")
    return f"{formatted_date}_{id_interno}_codigo_barra.{extension}"
