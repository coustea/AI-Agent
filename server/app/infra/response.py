"""HTTP response envelope for API responses."""

from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse
from pydantic import BaseModel


class HttpResponse(BaseModel):
    """HTTP response envelope with code, message, and data."""

    code: int = 200
    message: str = "success"
    data: Any = None

    @staticmethod
    def success(data: Any = None, message: str = "success") -> dict[str, Any]:
        """Create a successful response (HTTP 200)."""
        return HttpResponse(code=200, message=message, data=data).model_dump()

    @staticmethod
    def error(
        code: int = 500,
        message: str = "error",
        data: Any = None,
    ) -> JSONResponse:
        """Create an error response with the correct HTTP status code.

        Returns a JSONResponse so FastAPI uses the business code as the
        HTTP status code, keeping the envelope format {code, message, data}.
        """
        body = HttpResponse(code=code, message=message, data=data).model_dump()
        return JSONResponse(status_code=code, content=body)
