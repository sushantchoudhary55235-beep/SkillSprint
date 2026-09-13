"""Standardized API response envelope and error helpers.

Every endpoint returns:
    { "success": bool, "message": str, "data": ... }
per docs/API_Specification.md §6.
"""
from typing import Any

from fastapi import status
from fastapi.responses import JSONResponse


def success_response(data: Any = None, message: str = "Operation completed successfully", status_code: int = status.HTTP_200_OK) -> dict[str, Any]:
    return JSONResponse(
        status_code=status_code,
        content={"success": True, "message": message, "data": data},
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
