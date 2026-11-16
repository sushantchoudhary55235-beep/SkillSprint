"""Health check endpoints with liveness and readiness probes."""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db

router = APIRouter(prefix="/health", tags=["health"])

logger = logging.getLogger("skillsprint.health")


@router.get("/liveness")
def liveness_check() -> dict:
    """Liveness probe: application is running (no dependency checks)."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/readiness")
def readiness_check(db: Session = Depends(get_db)) -> dict:
    """Readiness probe: application can serve requests (checks DB connectivity)."""
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        logger.error("Database connectivity check failed: %s", e)
        db_status = "error"

    overall_status = "ok" if db_status == "ok" else "degraded"

    return {
        "status": overall_status,
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "checks": {
            "database": db_status,
        },
    }


@router.get("")
def health_check() -> dict:
    """Legacy health check endpoint."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
    }
