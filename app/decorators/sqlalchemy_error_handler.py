import functools
from fastapi import HTTPException, status
from sqlalchemy.exc import (
    SQLAlchemyError,
    IntegrityError,
    DataError,
    OperationalError,
    ProgrammingError,
)
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.logger import logger_instance as log


def sqlalchemy_error_handler(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        db = next(
            (arg for arg in args if isinstance(arg, AsyncSession)), kwargs.get("db")
        )

        try:
            return await func(*args, **kwargs)
        except IntegrityError as e:
            if db:
                await db.rollback()
            log.error(
                "Database integrity error",
                extra={
                    "error": str(e),
                    "error_type": "integrity",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A database constraint was violated. The operation cannot be completed.",
            )
        except DataError as e:
            if db:
                await db.rollback()
            log.error(
                "Data format error",
                extra={
                    "error": str(e),
                    "error_type": "data_format",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The data provided has an invalid format or is out of acceptable range.",
            )
        except OperationalError as e:
            if db:
                await db.rollback()
            log.error(
                "Database operational error",
                extra={
                    "error": str(e),
                    "error_type": "operational",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The database is currently unavailable.",
            )
        except ProgrammingError as e:
            if db:
                await db.rollback()
            log.error(
                "SQL programming error",
                extra={
                    "error": str(e),
                    "error_type": "programming",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred in the database query.",
            )
        except SQLAlchemyError as e:
            if db:
                await db.rollback()
            log.error(
                "Unexpected database error",
                extra={
                    "error": str(e),
                    "error_type": "unexpected",
                },
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected database error occurred.",
            )

    return wrapper
