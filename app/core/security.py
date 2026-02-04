from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from app.core.config import JWT_SECRET_KEY, ALGORITHM
from app.schemas.user import TokenData

security = HTTPBearer()


class PermissionValidator:
    """
    Global authentication validator that decodes JWT tokens.
    Applied to all private API endpoints via the router dependency.
    Stores the decoded token data in request.state for role-based authorization.
    """

    def __init__(self):
        pass

    async def __call__(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials = Depends(security),
    ) -> TokenData:
        token = credentials.credentials
        try:
            payload = jwt.decode(
                token,
                JWT_SECRET_KEY,
                algorithms=[ALGORITHM],
            )
            token_data = TokenData.model_validate(payload)
            request.state.user = token_data
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        return token_data
