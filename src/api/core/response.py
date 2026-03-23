"""Unified response schemas."""

from typing import Optional, Generic, TypeVar, Any

from pydantic import BaseModel, Field

T = TypeVar("T")


class Response(BaseModel, Generic[T]):
    """Unified API response."""

    code: int = Field(default=200, description="Status code")
    message: str = Field(default="success", description="Response message")
    data: Optional[T] = Field(default=None, description="Response data")
    error: Optional[str] = Field(default=None, description="Error details")

    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "success",
                "data": {},
                "error": None
            }
        }


class PaginationResponse(BaseModel, Generic[T]):
    """Paginated API response."""

    code: int = Field(default=200, description="Status code")
    message: str = Field(default="success", description="Response message")
    data: Optional[list[T]] = Field(default=None, description="Response data list")
    pagination: Optional["PaginationMeta"] = Field(
        default=None, description="Pagination metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "success",
                "data": [],
                "pagination": {
                    "total": 100,
                    "page": 1,
                    "page_size": 10,
                    "pages": 10
                }
            }
        }


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    total: int = Field(..., ge=0, description="Total items")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    pages: int = Field(..., ge=1, description="Total number of pages")
