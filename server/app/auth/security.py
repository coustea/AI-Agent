"""认证安全模块：密码哈希、JWT 签发及身份依赖注入。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from fastapi import Depends, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.schemas import UserClaims
from app.config import JWT_ALGO, JWT_EXPIRE, JWT_SECRET
from app.infra.database import get_session
from app.infra.logging import get_logger
from app.infra.models import User

logger = get_logger(__name__)


class AuthError(Exception):
    """认证业务异常，支持携带字段名以供前端表单绑定。"""

    def __init__(self, message: str, field: str = "", code: int = 401) -> None:
        """初始化认证异常。"""
        self.message = message
        self.field = field
        self.code = code
        super().__init__(message)


def hash_password(password: str) -> str:
    """使用 bcrypt 生成加盐密码哈希。"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """验证明文密码与哈希值是否匹配。"""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_token(user: User | UserClaims) -> str:
    """签发包含常用用户信息的 JWT Token（纯无状态，不访问数据库）。"""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=JWT_EXPIRE)
    payload = {
        "sub": str(user.id),
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": getattr(user, "role", "user"),
        "onboarding_completed": bool(user.onboarding_completed),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(
        payload,
        JWT_SECRET or "dev-secret-change-in-production-long-enough",
        algorithm=JWT_ALGO,
    )


def decode_token(token: str) -> UserClaims:
    """解码并校验 JWT Token，返回 UserClaims。"""
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET or "dev-secret-change-in-production-long-enough",
            algorithms=[JWT_ALGO],
        )
        return UserClaims.model_validate(payload)
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Token 已过期", code=401) from exc
    except (jwt.PyJWTError, Exception) as exc:
        raise AuthError("无效 Token", code=401) from exc


def get_current_user(request: Request) -> UserClaims:
    """FastAPI 核心依赖项：从请求上下文直接获取当前用户 Claims（0 次数据库 I/O）。"""
    user: UserClaims | None = getattr(request.state, "user", None)
    if user is None:
        raise AuthError("未登录或登录已过期", code=401)
    return user


async def get_current_user_entity(
    claims: UserClaims = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> User:
    """按需从数据库加载完整 User ORM 实体（仅在需要修改或读取全量扩展字段时使用）。"""
    user = await session.get(User, claims.id)
    if not user:
        raise AuthError("用户不存在", code=404)
    return user


__all__ = [
    "AuthError",
    "hash_password",
    "verify_password",
    "create_token",
    "decode_token",
    "get_current_user",
    "get_current_user_entity",
]
