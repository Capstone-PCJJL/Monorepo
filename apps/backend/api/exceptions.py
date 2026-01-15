"""
Custom exceptions and error handlers for the API.
"""

from typing import Any, Dict, Optional

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class APIError(HTTPException):
    """Base API error with structured error response."""

    def __init__(
        self,
        status_code: int,
        error: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.error = error
        self.message = message
        self.details = details
        super().__init__(status_code=status_code, detail=message)


class NotFoundError(APIError):
    """Resource not found error."""

    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            status_code=404,
            error="not_found",
            message=f"{resource} with ID {identifier} not found",
            details={"resource": resource, "id": identifier},
        )


class ValidationError(APIError):
    """Request validation error."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=422,
            error="validation_error",
            message=message,
            details=details,
        )


class DatabaseError(APIError):
    """Database connection/operation error."""

    def __init__(self, message: str = "Database operation failed"):
        super().__init__(
            status_code=503,
            error="database_unavailable",
            message=message,
        )


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Handle APIError exceptions and return structured JSON response."""
    content = {
        "error": exc.error,
        "message": exc.message,
    }
    if exc.details:
        content["details"] = exc.details
    return JSONResponse(status_code=exc.status_code, content=content)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "An unexpected error occurred",
        },
    )
