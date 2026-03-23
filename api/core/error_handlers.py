"""Unified error handlers for FastAPI."""

from fastapi import Request, status
from fastapi.responses import JSONResponse

from api.core.exceptions import APIError, UserNotFoundError, InvalidCredentialsError


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """
    Handle APIError and its subclasses.
    
    Args:
        request: FastAPI Request object
        exc: APIError exception
        
    Returns:
        JSONResponse with error details
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.message,
            "error_code": exc.error_code,
        }
    )


async def http_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    Handle generic HTTP exceptions.
    
    Args:
        request: FastAPI Request object
        exc: Exception
        
    Returns:
        JSONResponse with error details
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "message": "Internal server error",
            "error_code": "INTERNAL_SERVER_ERROR",
        }
    )


async def validation_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    Handle validation exceptions from Pydantic.
    
    Args:
        request: FastAPI Request object
        exc: Validation exception
        
    Returns:
        JSONResponse with validation errors
    """
    try:
        # Pydantic v2 ValidationError
        from pydantic import ValidationError as PydanticValidationError

        if isinstance(exc, PydanticValidationError):
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "message": "Validation failed",
                    "error_code": "VALIDATION_ERROR",
                    "errors": exc.errors(),
                }
            )
    except ImportError:
        pass

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "message": "Validation failed",
            "error_code": "VALIDATION_ERROR",
            "errors": str(exc),
        }
    )
