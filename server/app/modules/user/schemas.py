from datetime import datetime

from pydantic import BaseModel


# 请求
class UserRegister(BaseModel):
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserUpdate(BaseModel):
    email: str | None = None
    avatar: str | None = None
    major: str | None = None
    grade: str | None = None
    school: str | None = None


# 响应
class UserRead(BaseModel):
    id: str
    username: str
    email: str | None
    avatar: str | None
    major: str | None
    grade: str | None
    school: str | None
    created_at: datetime


class LoginResponse(BaseModel):
    token: str
    user: UserRead
