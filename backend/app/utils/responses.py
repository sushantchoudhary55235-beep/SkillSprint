"""Standardized API response envelope and error helpers.

Every endpoint returns:
    { "success": bool, "message": str, "data": ... }
per docs/API_Specification.md §6.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import status
from fastapi.responses import JSONResponse
from pydantic import BaseModel


def _serialize(data: Any) -> Any:
    """Convert pydantic models (and collections of them) to JSON-safe values."""
    if isinstance(data, BaseModel):
        return data.model_dump(mode="json")
    if isinstance(data, (list, tuple)):
        return [_serialize(item) for item in data]
    if isinstance(data, dict):
        return {key: _serialize(value) for key, value in data.items()}
    if isinstance(data, datetime):
        return data.isoformat()
    if isinstance(data, date):
        return data.isoformat()
    if isinstance(data, Decimal):
        return float(data)
    return data


def success_response(data: Any = None, message: str = "Operation completed successfully", status_code: int = status.HTTP_200_OK) -> dict[str, Any]:
    return JSONResponse(
        status_code=status_code,
        content={"success": True, "message": message, "data": _serialize(data)},
    )


def error_response(
    message: str = "Invalid request",
    error_code: str = "INVALID_REQUEST",
    status_code: int = status.HTTP_400_BAD_REQUEST,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "message": message, "error_code": error_code},
    )
