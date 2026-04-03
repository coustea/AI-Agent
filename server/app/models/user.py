from datetime import datetime
from uuid import uuid4

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    username: str = Field(max_length=50, index=True)
    password: str = Field(max_length=255)
    email: str | None = Field(default=None, max_length=100)
    avatar: str | None = Field(default=None, max_length=500)
    major: str | None = Field(default=None, max_length=100)
    grade: str | None = Field(default=None, max_length=20)
    school: str | None = Field(default=None, max_length=100)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
