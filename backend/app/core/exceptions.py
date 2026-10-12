"""Domain exceptions raised by services and translated by API handlers.

Keeping these in core allows services to express business-rule failures
without importing FastAPI (separation of concerns).
"""
from typing import Any


class SkillSprintError(Exception):
    """Base class for all domain errors."""

    status_code = 400
    error_code = "BAD_REQUEST"

    def __init__(self, message: str = "Invalid request", details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(SkillSprintError):
    status_code = 404
    error_code = "NOT_FOUND"


class ConflictError(SkillSprintError):
    status_code = 409
    error_code = "CONFLICT"


class ValidationError(SkillSprintError):
    status_code = 422
    error_code = "VALIDATION_ERROR"


class AuthError(SkillSprintError):
    """Authentication failures (401)."""

    status_code = 401
    error_code = "UNAUTHORIZED"


class ForbiddenError(SkillSprintError):
    """Authorization failures (403): authenticated but not allowed."""

    status_code = 403
    error_code = "FORBIDDEN"


class ServiceUnavailableError(SkillSprintError):
    """A dependency (e.g. AI service) is unavailable or unconfigured (503)."""

    status_code = 503
    error_code = "SERVICE_UNAVAILABLE"
