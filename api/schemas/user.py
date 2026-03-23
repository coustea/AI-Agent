from datetime import datetime
from typing import Optional

from pydantic import EmailStr, Field, BaseModel, ConfigDict


class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    username: str = Field(min_length=3, max_length=20)
    email: EmailStr = Field(max_length=100)
    full_name: Optional[str] = Field(default=None, max_length=50)
    is_active: bool = Field(default=True)


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    email: EmailStr = Field(max_length=100)
    password: str = Field(min_length=8, max_length=20)
    full_name: Optional[str] = Field(default=None, max_length=50)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(default=None, max_length=50)
    password: Optional[str] = Field(default=None, min_length=8, max_length=20)
    is_active: Optional[bool] = None


class UserRead(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime


class UserLogin(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=8, max_length=20)


class PasswordChange(BaseModel):
    old_password: str = Field(min_length=8, max_length=20)
    new_password: str = Field(min_length=8, max_length=20)
