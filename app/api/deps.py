from fastapi import Depends, HTTPException, status, Request

from app.db.database import get_db
from app.schemas.user import TokenData
from app.enums.enums import RoleType


def get_current_user(request: Request) -> TokenData:
    """
    Retrieves the current authenticated user's token data from request.state.
    This data is set by the PermissionValidator in core/security.py.

    Raises: HTTPException If user data is not found.
    """
    if not hasattr(request.state, "user"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return request.state.user


def require_admin(
    current_user: TokenData = Depends(get_current_user),
) -> TokenData:
    """
    Dependency that ensures the current user has admin role.

    Raises: HTTPException If user doesn't have admin role.
    """
    if current_user.user_role != RoleType.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


def require_any_authenticated(
    current_user: TokenData = Depends(get_current_user),
) -> TokenData:
    """
    Dependency that ensures the user is authenticated (any role).
    """
    return current_user
