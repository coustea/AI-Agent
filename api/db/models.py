from datetime import datetime
from typing import Optional

from pydantic import EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlmodel import Field, SQLModel


class Settings(BaseSettings):
    openai_api_key: str = Field(default="")
    openai_base_url: str = Field(default="")

    db_host: str = Field(default="localhost")
    db_port: int = Field(default=3306)
    db_name: str = Field(default="agent")
    db_user: str = Field(default="root")
    db_password: str = Field(default="")

    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0)
    redis_password: Optional[str] = Field(default=None)

    secret_key: str = Field(default="")
    algorithm: str = Field(default="HS256")
    access_token_expire_hours: int = Field(default=24)

    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=9999)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()

SYNC_DATABASE_URL = (
    f"mysql+pymysql://{settings.db_user}:{settings.db_password}@"
    f"{settings.db_host}:{settings.db_port}/{settings.db_name}"
)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, min_length=3, max_length=20)
    email: EmailStr = Field(index=True, unique=True, max_length=100)
    password_hash: str = Field(max_length=255)
    full_name: Optional[str] = Field(default=None, max_length=50)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
