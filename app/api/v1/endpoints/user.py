from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    ChangePasswordRequest,
)
from app.schemas.shared_pagination_response import PaginatedResponse
from app.crud.user import (
    create_user,
    update_user,
    delete_user,
    get_user_by_id_or_rut_or_email,
    get_users,
    change_password,
    reset_password,
)
from app.services.email import send_email
from app.api.deps import get_db, require_admin, require_any_authenticated
from app.utils.logger import logger_instance as log
from app.enums.enums import EmailType


router = APIRouter()


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_user_route(
    user: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    try:
        db_user, temporary_password = await create_user(db, user)

        await db.commit()

        user_id = db_user.id

        log.info(
            "User created successfully",
            extra={
                "user_id": db_user.id,
                "user_rut": db_user.rut,
            },
        )

        background_tasks.add_task(send_email, user_id, temporary_password)

        return db_user
    except HTTPException as e:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        log.error(
            "Error creating user",
            extra={
                "operation": "create",
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user",
        )


@router.patch(
    "/{id}",
    response_model=UserResponse,
    dependencies=[Depends(require_admin)],
)
async def update_user_route(
    user: UserUpdate,
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Update an user by id, allows partial updates"""
    try:
        db_user = await get_user_by_id_or_rut_or_email(db, id=id)
        updated_user = await update_user(db, db_user, user)
        await db.commit()
        log.info(
            "User updated successfully",
            extra={
                "user_id": id,
            },
        )
        return updated_user
    except HTTPException as e:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        log.error(
            f"Error updating user",
            extra={
                "operation": "update",
                "user_id": id,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating user",
        )


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_user_route(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete an user by id"""
    try:
        db_user = await get_user_by_id_or_rut_or_email(db, id=id)
        await delete_user(db, db_user)
        await db.commit()
        log.info(
            "User deleted successfully",
            extra={
                "user_id": id,
            },
        )
    except HTTPException as e:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        log.error(
            f"Error deleting user",
            extra={
                "operation": "delete",
                "user_id": id,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting user",
        )


@router.get(
    "/{id}",
    response_model=UserResponse,
    dependencies=[Depends(require_admin)],
)
async def read_user_by_id_route(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get an user by id"""
    try:
        user = await get_user_by_id_or_rut_or_email(db, id=id)
        return user
    except HTTPException as e:
        raise
    except Exception as e:
        log.error(
            f"Error fetching user by id",
            extra={
                "operation": "read one by id",
                "user_id": id,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching user",
        )


@router.get(
    "/rut/{rut}",
    response_model=UserResponse,
    dependencies=[Depends(require_any_authenticated)],
)
async def read_user_by_rut_route(
    rut: str,
    db: AsyncSession = Depends(get_db),
):
    """Get an user by rut"""
    try:
        user = await get_user_by_id_or_rut_or_email(db, rut=rut)
        return user
    except HTTPException as e:
        raise
    except Exception as e:
        log.error(
            f"Error fetching user by rut",
            extra={
                "operation": "read one by rut",
                "user_rut": rut,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching user",
        )


@router.get(
    "/",
    response_model=PaginatedResponse[UserResponse],
    dependencies=[Depends(require_admin)],
)
async def read_users_route(
    db: AsyncSession = Depends(get_db),
):
    """Get a list of all users"""
    try:
        total_count, users = await get_users(db)
        return PaginatedResponse[UserResponse].create_unpaginated(
            items=users,
            total=total_count,
        )
    except HTTPException as e:
        raise
    except Exception as e:
        log.error(
            f"Error fetching users",
            extra={
                "operation": "read all",
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching users",
        )


@router.post(
    "/{id}/change-password",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_any_authenticated)],
)
async def change_password_route(
    id: int,
    password_data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Allows an user with any role a to change their temporary password"""
    try:
        db_user = await get_user_by_id_or_rut_or_email(db, id=id)

        if not db_user.tiene_contrasena_temporal:
            log.error(
                "User does not have a temporary password",
                extra={"user_id": id},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User does not have a temporary password",
            )

        from argon2 import PasswordHasher
        from argon2.exceptions import VerifyMismatchError

        ph = PasswordHasher()
        try:
            ph.verify(db_user.contrasena, password_data.current_password)
        except VerifyMismatchError:
            log.error(
                "Invalid current password",
                extra={"user_id": id},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect",
            )

        updated_user = await change_password(db, db_user, password_data.new_password)
        await db.commit()

        log.info(
            "User password changed successfully",
            extra={"user_id": id},
        )

        return updated_user

    except HTTPException as e:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        log.error(
            "Error changing user password",
            extra={
                "operation": "change_password",
                "user_id": id,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error changing password",
        )


@router.post(
    "/{id}/reset-password",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_admin)],
)
async def reset_password_route(
    id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Allows and admin user to reset another user's password"""
    try:
        db_user = await get_user_by_id_or_rut_or_email(db, id=id)

        updated_user, temporary_password = await reset_password(db, db_user)
        await db.commit()

        log.info(
            "User password reset successfully",
            extra={"user_id": id},
        )

        background_tasks.add_task(send_email, id, temporary_password, "reset_password")

        return updated_user

    except HTTPException as e:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        log.error(
            "Error resetting user password",
            extra={
                "operation": "reset_password",
                "user_id": id,
                "error_type": type(e).__name__,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error resetting password",
        )
