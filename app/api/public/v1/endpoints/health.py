from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from datetime import datetime, timezone

from app.db.database import get_db

router = APIRouter()


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Public Health Check",
    description="Checks API status and database connection without authentication",
)
async def public_health_check(db: AsyncSession = Depends(get_db)):
    """
    Public health check endpoint that verifies:
    - API is running correctly
    - Database connection is active
    - Does NOT require authentication (public)

    Returns:
        dict: API and database health status
    """
    db_status = "healthy"
    db_message = "Database connection successful"

    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()

    except Exception as e:
        db_status = "unhealthy"
        db_message = f"Database connection failed: {str(e)}"

    # Determine overall status
    overall_status = "healthy" if db_status == "healthy" else "degraded"

    return {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "api": {"status": "healthy", "message": "API is running"},
        "database": {
            "status": db_status,
            "message": db_message,
        },
    }
