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
