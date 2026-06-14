"""Authentication adapter."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
import jwt
from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import JWT_ALGO, JWT_EXPIRE, JWT_SECRET
from app.infra.database import get_session
from app.infra.logging import get_logger
from app.infra.models import ActiveToken, User
from app.infra.response import HttpResponse

logger = get_logger(__name__)
bearer_scheme = HTTPBearer()
optional_bearer_scheme = HTTPBearer(auto_error=False)


class AuthError(Exception):
    """Authentication error that the global handler converts to HttpResponse envelope."""

    def __init__(self, message: str) -> None:
        self.message = message  # 错误消息，会被全局异常处理器捕获并返回给前端
        super().__init__(message)


def hash_password(password: str) -> str:
    """使用 bcrypt 对密码进行哈希，自动加盐。"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _is_expired(expires_at: datetime | None) -> bool:
    if expires_at is None:
        return True
    return _as_utc(expires_at) <= datetime.now(timezone.utc)


async def create_token(user_id: int, session: AsyncSession) -> str:
    """签发 JWT Token 并写入白名单表，支持登出失效。"""
    expire = datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRE)  # 计算过期时间
    payload = {"sub": str(user_id), "exp": expire, "jti": uuid4().hex}  # sub=用户ID, jti=唯一标识
    token = jwt.encode(
        payload,
        JWT_SECRET or "dev-secret-change-in-production-long-enough",  # 开发环境兜底密钥
        algorithm=JWT_ALGO,
    )
    session.add(ActiveToken(user_id=user_id, token=token, expires_at=expire))  # 写入白名单
    await session.commit()  # 持久化 Token 记录
    return token


def decode_token(token: str) -> int:
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET or "dev-secret-change-in-production-long-enough",
            algorithms=[JWT_ALGO],
        )
        return int(payload["sub"])
    except jwt.ExpiredSignatureError as exc:
        logger.warning("[Auth] Token 已过期")
        raise AuthError("Token 已过期") from exc
    except jwt.InvalidTokenError as exc:
        logger.warning("[Auth] 无效 Token")
        raise AuthError("无效 Token") from exc


async def is_token_valid(token: str, session: AsyncSession) -> bool:
    """检查 Token 是否在白名单中且未过期，过期则自动清理。"""
    active_token = (await session.exec(select(ActiveToken).where(ActiveToken.token == token))).first()  # 查询白名单
    if not active_token:
        return False  # Token 不在白名单（已登出或从未签发）
    if _is_expired(active_token.expires_at):
        await session.delete(active_token)  # 清理过期记录
        await session.commit()
        return False
    return True


async def revoke_token(token: str, session: AsyncSession) -> None:
    active_token = (await session.exec(select(ActiveToken).where(ActiveToken.token == token))).first()
    if active_token:
        await session.delete(active_token)
        await session.commit()


async def _resolve_current_user_from_token(
    token: str, session: AsyncSession
) -> User:
    if not await is_token_valid(token, session):
        raise AuthError("Token 已失效或已退出登录")
    user_id = decode_token(token)
    user = await session.get(User, user_id)
    if not user:
        raise AuthError("用户不存在")
    await session.refresh(user)
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    if not credentials:
        raise AuthError("缺少 Token")
    return await _resolve_current_user_from_token(credentials.credentials, session)


async def get_current_user_flexible(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer_scheme),
    token: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> User:
    resolved_token = credentials.credentials if credentials else token
    if not resolved_token:
        raise AuthError("缺少 Token")
    return await _resolve_current_user_from_token(resolved_token, session)
