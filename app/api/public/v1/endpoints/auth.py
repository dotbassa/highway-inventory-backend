from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta
import jwt

from app.api.deps import get_db
from app.schemas.user import LoginRequest, TokenData, TokenResponse
from app.crud.user import login
from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES, JWT_SECRET_KEY, ALGORITHM
from app.utils.logger import logger_instance as log

router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
async def login_route(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        db_user = await login(db, login_data)
        if not db_user:
            log.error(
                "Invalid credentials provided",
                extra={
                    "user_email": login_data.user_email,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        to_encode = TokenData(
            user_name=db_user.nombres + " " + db_user.apellidos,
            user_rut=db_user.rut,
            user_email=db_user.email,
            user_role=db_user.rol,
            has_temporary_password=db_user.tiene_contrasena_temporal,
            exp=datetime.now(timezone.utc)
            + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )

        encoded_jwt = jwt.encode(
            to_encode.model_dump(),
            JWT_SECRET_KEY,
            algorithm=ALGORITHM,
        )

        return TokenResponse(access_token=encoded_jwt, token_type="bearer")
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        log.error(
            "Error during user login",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "user_email": login_data.user_email,
                "error": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error logging in user",
        )
