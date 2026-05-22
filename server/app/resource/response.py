"""Resource response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ResourceResponse(BaseModel):
    """Resource item in list response."""

    id: int
    title: str
    resource_type: str
    status: str = "pending"
    created_at: datetime | None = None


class ResourceDetailResponse(BaseModel):
    """Resource detail response with content."""

    id: int
    title: str
    resource_type: str
    status: str = "pending"
    content: str | None = None
    metadata: dict | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ResourceListResponse(BaseModel):
    """Resource list response."""

    items: list[ResourceResponse] = Field(default_factory=list)
    total: int = 0
