import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.dependencies import get_session
from app.core.logging import get_logger
from app.models.auth import ActiveToken
from app.models.user import User

logger = get_logger(__name__)

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-production-long-enough")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
EXPIRE_DAYS = int(os.getenv("JWT_EXPIRE_DAYS", "7"))

bearer_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


async def create_token(user_id: int, session: AsyncSession) -> str:
    """签发 JWT 并写入 ActiveToken 白名单"""
    expire = datetime.now(timezone.utc) + timedelta(days=EXPIRE_DAYS)
    payload = {"sub": str(user_id), "exp": expire}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    active_token = ActiveToken(
        user_id=user_id,
        token=token,
        expires_at=expire,
    )
    session.add(active_token)
    await session.commit()

    logger.info("Token created for user_id=%s", user_id)
    return token


def decode_token(token: str) -> int:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token 已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效 Token")


async def is_token_valid(token: str, session: AsyncSession) -> bool:
    """检查 token 是否在白名单中且未过期"""
    active_token = (await session.exec(
        select(ActiveToken).where(ActiveToken.token == token)
    )).first()
    if not active_token:
        return False
    if active_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        await session.delete(active_token)
        await session.commit()
        return False
    return True


async def revoke_token(token: str, session: AsyncSession) -> None:
    """从白名单中移除 token（登出）"""
    active_token = (await session.exec(
        select(ActiveToken).where(ActiveToken.token == token)
    )).first()
    if active_token:
        await session.delete(active_token)
        await session.commit()
        logger.info("Token revoked for user_id=%s", active_token.user_id)


async def cleanup_expired_tokens(session: AsyncSession) -> int:
    """清理所有已过期的 token 记录，返回清理数量"""
    now = datetime.now()
    expired = (await session.exec(
        select(ActiveToken).where(ActiveToken.expires_at < now)
    )).all()
    for t in expired:
        await session.delete(t)
    await session.commit()
    if expired:
        logger.info("Cleaned up %d expired tokens", len(expired))
    return len(expired)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    token = credentials.credentials

    if not await is_token_valid(token, session):
        raise HTTPException(status_code=401, detail="Token 已失效或已退出登录")

    user_id = decode_token(token)
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    await session.refresh(user)
    return user
