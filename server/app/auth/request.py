"""Auth request schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class UserRegister(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=6, max_length=100)
    email: str | None = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserUpdate(BaseModel):
    username: str | None = None
    email: str | None = None
    avatar: str | None = None
    is_first_login: bool | None = None
