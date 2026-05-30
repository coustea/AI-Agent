"""Authentication adapter."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import JWT_ALGO, JWT_EXPIRE, JWT_SECRET
from app.infra.database import session_scope
from app.infra.logging import get_logger
from app.infra.models import ActiveToken, User
from app.infra.response import HttpResponse

logger = get_logger(__name__)
bearer_scheme = HTTPBearer()
optional_bearer_scheme = HTTPBearer(auto_error=False)


class AuthError(Exception):
    """Authentication error that the global handler converts to HttpResponse envelope."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def hash_password(password: str) -> str:
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
    expire = datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRE)
    payload = {"sub": str(user_id), "exp": expire}
    token = jwt.encode(
        payload,
        JWT_SECRET or "dev-secret-change-in-production-long-enough",
        algorithm=JWT_ALGO,
    )
    session.add(ActiveToken(user_id=user_id, token=token, expires_at=expire))
    await session.commit()
    logger.debug("[Auth] Token 创建: user_id=%s expires=%s", user_id, expire.isoformat())
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
    active_token = (await session.exec(select(ActiveToken).where(ActiveToken.token == token))).first()
    if not active_token:
        return False
    if _is_expired(active_token.expires_at):
        await session.delete(active_token)
        await session.commit()
        return False
    return True


async def revoke_token(token: str, session: AsyncSession) -> None:
    active_token = (await session.exec(select(ActiveToken).where(ActiveToken.token == token))).first()
    if active_token:
        await session.delete(active_token)
        await session.commit()


async def _resolve_current_user_from_token(token: str) -> User:
    async with session_scope() as session:
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
) -> User:
    if not credentials:
        raise AuthError("缺少 Token")
    return await _resolve_current_user_from_token(credentials.credentials)


async def get_current_user_flexible(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer_scheme),
    token: str | None = Query(default=None),
) -> User:
    resolved_token = credentials.credentials if credentials else token
    if not resolved_token:
        raise AuthError("缺少 Token")
    return await _resolve_current_user_from_token(resolved_token)
