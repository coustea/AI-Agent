"""HTTP response envelope for API responses."""

from typing import Any

from pydantic import BaseModel


class HttpResponse(BaseModel):
    """HTTP response envelope with code, message, and data."""

    code: int = 200
    message: str = "success"
    data: Any = None

    @staticmethod
    def success(data: Any = None, message: str = "success") -> "HttpResponse":
        """Create a successful response."""
        return HttpResponse(code=200, message=message, data=data)

    @staticmethod
    def error(code: int = 500, message: str = "error", data: Any = None) -> "HttpResponse":
        """Create an error response."""
        return HttpResponse(code=code, message=message, data=data)
