from datetime import datetime
from uuid import uuid4

from sqlmodel import Field, SQLModel


class TokenBlacklist(SQLModel, table=True):
    __tablename__ = "token_blacklist"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    token: str = Field(max_length=500, index=True)
    created_at: datetime = Field(default_factory=datetime.now)
