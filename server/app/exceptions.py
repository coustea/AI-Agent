"""Application exception handlers."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.auth.security import AuthError
from app.infra.response import HttpResponse


async def auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
    """Convert AuthError to HttpResponse envelope with HTTP 401."""
    return HttpResponse.error(code=401, message=exc.message)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Convert FastAPI's built-in HTTPException to the app response envelope."""
    return HttpResponse.error(code=exc.status_code, message=str(exc.detail))


def install_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AuthError, auth_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
