"""Unified response schemas."""

from typing import Optional, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Response(BaseModel, Generic[T]):
    code: int = 200
    message: str = "success"
    data: Optional[T] = None


class EmptyData(BaseModel):
    pass
