"""Auth response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class UserRead(BaseModel):
    id: int
    username: str
    email: str | None = None
    avatar: str | None = None
    created_at: datetime | None = None
    is_first_login: bool = False

    model_config = {"from_attributes": True}
