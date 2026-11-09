"""认证安全模块：密码哈希、JWT 签发及身份上下文访问。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from fastapi import Request

from app.auth.schemas import UserClaims
from app.config import JWT_ALGO, JWT_EXPIRE, JWT_SECRET
from app.infra.logging import get_logger
from app.infra.models import User
from app.middleware.jwt import current_user_ctx

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


def get_current_user(request: Request | None = None) -> UserClaims:
    """从协程上下文中获取当前用户 UserClaims（0 次数据库 I/O，无需传参）。"""
    user = current_user_ctx.get()
    if user is None and request is not None:
        user = getattr(request.state, "user", None)
    if user is None:
        raise AuthError("未登录或登录已过期", code=401)
    return user


__all__ = [
    "AuthError",
    "hash_password",
    "verify_password",
    "create_token",
    "decode_token",
    "get_current_user",
]
