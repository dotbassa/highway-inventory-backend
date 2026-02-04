from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Tuple, Optional
from argon2 import PasswordHasher
from pydantic import EmailStr

from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    LoginRequest,
)
from app.decorators.sqlalchemy_error_handler import sqlalchemy_error_handler
from app.utils.logger import logger_instance as log
from app.utils.string_generator import generate_temporary_password

ph = PasswordHasher()


async def _check_uniqueness(
    db: AsyncSession,
    rut: Optional[str] = None,
    email: Optional[EmailStr] = None,
) -> bool:
    if rut:
        result = await db.execute(select(User).where(User.rut == rut))
        if result.scalar_one_or_none():
            return True
        return False
    if email:
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            return True
        return False
    return False


@sqlalchemy_error_handler
async def create_user(
    db: AsyncSession,
    user: UserCreate,
) -> Tuple[User, str]:

    existing_user = await _check_uniqueness(db, rut=user.rut, email=user.email)
    if existing_user:
        log.error(
            f"User already exists",
            extra={
                "user_rut": user.rut,
                "user_email": user.email,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with rut {user.rut} or email {user.email} already exists",
        )

    temporary_password = generate_temporary_password()

    user_data = user.model_dump()
    user_data["contrasena"] = ph.hash(temporary_password)
    user_data["tiene_contrasena_temporal"] = True

    db_user = User(**user_data)
    db.add(db_user)

    return db_user, temporary_password


@sqlalchemy_error_handler
async def update_user(
    db: AsyncSession,
    db_user: User,
    user: UserUpdate,
) -> User:
    existing_user = await _check_uniqueness(db, rut=user.rut, email=user.email)
    if existing_user:
        log.error(
            f"User already exists",
            extra={
                "user_rut": user.rut,
                "user_email": user.email,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with rut {user.rut} or email {user.email} already exists",
        )

    if user.contrasena is not None:
        user.contrasena = ph.hash(user.contrasena)

    update_data = user.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_user, field, value)

    return db_user


@sqlalchemy_error_handler
async def delete_user(
    db: AsyncSession,
    db_user: User,
) -> None:
    db_user.activo = False
    await db.flush()


@sqlalchemy_error_handler
async def get_user_by_id_or_rut_or_email(
    db: AsyncSession,
    id: Optional[int] = None,
    rut: Optional[str] = None,
    email: Optional[EmailStr] = None,
) -> User:
    query = select(User)
    if id:
        query = query.where(User.id == id)
    elif rut:
        query = query.where(User.rut == rut.strip())
    elif email:
        query = query.where(User.email == email.strip())
    else:
        log.error(
            "Either id or rut or email must be provided to retrieve a user",
            extra={
                "user_id": id,
                "user_rut": rut,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either id or rut or email must be provided to retrieve a user",
        )

    result = await db.execute(query)
    db_user = result.scalar_one_or_none()
    if not db_user:
        log.error(
            "User not found",
            extra={
                "user_id": id,
                "user_rut": rut,
                "user_email": email,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return db_user


@sqlalchemy_error_handler
async def get_users(
    db: AsyncSession,
) -> Tuple[int, List[User]]:
    result = await db.execute(select(User).order_by(User.id.desc()))
    users = result.scalars().all()

    return len(users), users


@sqlalchemy_error_handler
async def change_password(
    db: AsyncSession,
    db_user: User,
    new_password: str,
) -> User:
    db_user.contrasena = ph.hash(new_password)
    db_user.tiene_contrasena_temporal = False

    await db.flush()

    return db_user


@sqlalchemy_error_handler
async def reset_password(
    db: AsyncSession,
    db_user: User,
) -> tuple[User, str]:
    temporary_password = generate_temporary_password()
    db_user.contrasena = ph.hash(temporary_password)
    db_user.tiene_contrasena_temporal = True

    await db.flush()

    return db_user, temporary_password


@sqlalchemy_error_handler
async def login(
    db: AsyncSession,
    login_data: LoginRequest,
) -> User:
    db_user = await get_user_by_id_or_rut_or_email(
        db,
        email=login_data.user_email,
    )

    if not db_user.activo:
        log.error(
            "Inactive user attempted to log in",
            extra={
                "user_email": login_data.user_email,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    ph.verify(db_user.contrasena, login_data.contrasena)
    if ph.check_needs_rehash(db_user.contrasena):
        db_user.contrasena = ph.hash(login_data.contrasena)

    await db.commit()

    return db_user
