"""SQLAlchemy models for database using SQLModel."""

from datetime import datetime
from typing import Optional

from pydantic import EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlmodel import Field, SQLModel, create_engine, Session, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column


class Settings(BaseSettings):
    """Application settings."""

    # LLM / OpenAI
    openai_api_key: str = Field(default="")
    openai_base_url: str = Field(default="")

    # Database
    db_host: str = Field(default="localhost")
    db_port: int = Field(default=3306)
    db_name: str = Field(default="agent")
    db_user: str = Field(default="root")
    db_password: str = Field(default="")

    # Redis
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0)
    redis_password: Optional[str] = Field(default=None)

    # JWT
    secret_key: str = Field(default="")
    algorithm: str = Field(default="HS256")
    access_token_expire_hours: int = Field(default=24)

    # API
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=9999)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Global settings instance
settings = Settings()


# Database URLs
SYNC_DATABASE_URL = (
    f"mysql+pymysql://{settings.db_user}:{settings.db_password}@"
    f"{settings.db_host}:{settings.db_port}/{settings.db_name}"
)


class User(SQLModel, table=True):
    """User model for database table."""

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, min_length=3, max_length=20)
    email: EmailStr = Field(index=True, unique=True, max_length=100)
    password_hash: str = Field(max_length=255)
    full_name: Optional[str] = Field(default=None, max_length=50)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserBase(SQLModel):
    """Base model for User without table configuration."""

    username: str = Field(min_length=3, max_length=20)
    email: EmailStr = Field(max_length=100)
    full_name: Optional[str] = Field(default=None, max_length=50)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserCreate(SQLModel):
    """Schema for creating a user (includes password)."""

    username: str = Field(min_length=3, max_length=20)
    email: EmailStr = Field(max_length=100)
    password: str = Field(min_length=8, max_length=20)
    full_name: Optional[str] = Field(default=None, max_length=50)


class UserUpdate(SQLModel):
    """Schema for updating a user."""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(default=None, max_length=50)
    password: Optional[str] = Field(default=None, min_length=8, max_length=20)
    is_active: Optional[bool] = None


class UserRead(UserBase):
    """Schema for reading a user (excludes password and sensitive data)."""

    id: int
    created_at: datetime
    updated_at: datetime


class UserLogin(SQLModel):
    """Schema for user login."""

    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=8, max_length=20)


class Token(SQLModel):
    """Schema for JWT token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead


class Token(SQLModel):
    """Schema for JWT token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead


class PasswordChange(SQLModel):
    """Schema for password change."""

    old_password: str = Field(min_length=8, max_length=20)
    new_password: str = Field(min_length=8, max_length=20)


# ================= 会话管理 Schema =================

class SessionCreate(SQLModel):
    """创建会话请求."""

    title: Optional[str] = Field(default="新会话", max_length=200)


class SessionRead(SQLModel):
    """会话读取模型."""

    session_id: str
    title: str
    created_at: str
    updated_at: str


class MessageBase(SQLModel):
    """消息基础模型."""

    role: str = Field(max_length=20)
    content: str = Field(max_length=10000)


class MessageRead(SQLModel):
    """消息读取模型."""

    id: int
    role: str
    content: str
    created_at: str


class ChatRequest(SQLModel):
    """聊天请求."""

    message: str = Field(min_length=1, max_length=5000)


class ChatResponse(SQLModel):
    """聊天响应."""

    message_id: int
    role: str
    content: str
    created_at: str
