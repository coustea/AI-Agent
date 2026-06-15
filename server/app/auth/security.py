"""认证安全模块。

负责 JWT Token 的签发、验证、撤销，以及密码哈希和用户身份解析。
是整个认证体系的核心适配层。
"""

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

# 获取当前模块的日志记录器
logger = get_logger(__name__)

# Bearer Token 认证方案：从 Authorization: Bearer <token> 头中提取 Token
bearer_scheme = HTTPBearer()
# 可选的 Bearer 认证方案：当 Token 缺失时不报错，返回 None
optional_bearer_scheme = HTTPBearer(auto_error=False)


class AuthError(Exception):
    """认证错误异常。

    当 Token 无效、过期、用户不存在等情况时抛出，
    会被全局异常处理器捕获并转换为标准 JSON 响应。
    """

    def __init__(self, message: str) -> None:
        # 错误消息，会被全局异常处理器读取并返回给前端
        self.message = message
        super().__init__(message)


def hash_password(password: str) -> str:
    """使用 bcrypt 对密码进行哈希，自动加盐。

    Args:
        password: 明文密码

    Returns:
        bcrypt 哈希后的密码字符串
    """
    # bcrypt.gensalt() 生成随机盐值，hashpw 执行哈希运算
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """验证明文密码与哈希密码是否匹配。

    Args:
        plain: 用户输入的明文密码
        hashed: 数据库中存储的哈希密码

    Returns:
        密码匹配返回 True，否则返回 False
    """
    # bcrypt.checkpw 自动提取盐值并进行比对
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _as_utc(value: datetime) -> datetime:
    """将 datetime 对象统一转为 UTC 时区。

    如果输入没有时区信息，假设为 UTC；如果有时区信息则转换为 UTC。
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _is_expired(expires_at: datetime | None) -> bool:
    """检查给定时间是否已过期。

    Args:
        expires_at: 过期时间，None 表示已过期

    Returns:
        已过期返回 True
    """
    if expires_at is None:
        return True
    # 将过期时间转为 UTC 后与当前 UTC 时间比较
    return _as_utc(expires_at) <= datetime.now(timezone.utc)


async def create_token(user_id: int, session: AsyncSession) -> str:
    """签发 JWT Token 并写入白名单表。

    流程：
    1. 计算 Token 过期时间
    2. 构建 Payload（sub=用户ID, exp=过期时间, jti=唯一标识）
    3. 使用密钥签名生成 Token
    4. 将 Token 写入 ActiveToken 白名单表（支持登出失效）
    5. 提交事务持久化

    Args:
        user_id: 用户 ID
        session: 数据库会话

    Returns:
        签发的 JWT Token 字符串
    """
    # 计算过期时间：当前 UTC 时间 + 配置的天数
    expire = datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRE)
    # 构建 Payload：sub=用户ID, exp=过期时间, jti=唯一标识（用于白名单管理）
    payload = {"sub": str(user_id), "exp": expire, "jti": uuid4().hex}
    # 使用密钥和算法签名生成 Token
    token = jwt.encode(
        payload,
        JWT_SECRET or "dev-secret-change-in-production-long-enough",  # 开发环境兜底密钥
        algorithm=JWT_ALGO,
    )
    # 将 Token 写入白名单表，支持后续验证和登出撤销
    session.add(ActiveToken(user_id=user_id, token=token, expires_at=expire))
    # 持久化 Token 记录到数据库
    await session.commit()
    return token


def decode_token(token: str) -> int:
    """解码并验证 JWT Token，返回用户 ID。

    Args:
        token: JWT Token 字符串

    Returns:
        用户 ID

    Raises:
        AuthError: Token 过期或无效时抛出
    """
    try:
        # 使用密钥和算法验证 Token 签名并解码 Payload
        payload = jwt.decode(
            token,
            JWT_SECRET or "dev-secret-change-in-production-long-enough",
            algorithms=[JWT_ALGO],
        )
        # 从 Payload 中提取用户 ID（sub 字段）
        return int(payload["sub"])
    except jwt.ExpiredSignatureError as exc:
        # Token 签名已过期
        logger.warning("[Auth] Token 已过期")
        raise AuthError("Token 已过期") from exc
    except jwt.InvalidTokenError as exc:
        # Token 签名无效或格式错误
        logger.warning("[Auth] 无效 Token")
        raise AuthError("无效 Token") from exc


async def is_token_valid(token: str, session: AsyncSession) -> bool:
    """检查 Token 是否在白名单中且未过期。

    白名单机制：签发时写入 ActiveToken 表，登出时删除。
    如果 Token 不在表中（已登出）或已过期，返回 False 并自动清理过期记录。

    Args:
        token: JWT Token 字符串
        session: 数据库会话

    Returns:
        Token 有效返回 True
    """
    # 从白名单表中查询该 Token
    active_token = (await session.exec(select(ActiveToken).where(ActiveToken.token == token))).first()
    if not active_token:
        # Token 不在白名单中（已登出或从未签发）
        return False
    if _is_expired(active_token.expires_at):
        # Token 已过期，清理过期记录
        await session.delete(active_token)
        await session.commit()
        return False
    return True


async def revoke_token(token: str, session: AsyncSession) -> None:
    """撤销 Token：从白名单表中删除，使其立即失效。

    用于登出操作，删除后该 Token 将无法通过验证。

    Args:
        token: 要撤销的 JWT Token
        session: 数据库会话
    """
    # 从白名单表中查找该 Token
    active_token = (await session.exec(select(ActiveToken).where(ActiveToken.token == token))).first()
    if active_token:
        # 删除白名单记录，Token 立即失效
        await session.delete(active_token)
        await session.commit()


async def _resolve_current_user_from_token(
    token: str, session: AsyncSession
) -> User:
    """从 Token 解析当前用户（内部方法）。

    验证 Token 有效性 → 解码获取用户 ID → 查询用户记录。

    Args:
        token: JWT Token 字符串
        session: 数据库会话

    Returns:
        当前用户对象

    Raises:
        AuthError: Token 失效或用户不存在时抛出
    """
    # 检查 Token 是否在白名单中且未过期
    if not await is_token_valid(token, session):
        raise AuthError("Token 已失效或已退出登录")
    # 从 Token 中解码用户 ID
    user_id = decode_token(token)
    # 根据用户 ID 查询用户记录
    user = await session.get(User, user_id)
    if not user:
        raise AuthError("用户不存在")
    # 刷新用户对象，确保所有字段已从数据库加载
    await session.refresh(user)
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    """FastAPI 依赖项：获取当前登录用户。

    从 Authorization 头中提取 Bearer Token，验证后返回用户对象。
    用于需要认证的接口，通过 Depends(get_current_user) 注入。

    Args:
        credentials: HTTP Bearer Token 凭证（由 FastAPI 自动解析）
        session: 数据库会话（由 Depends 自动注入）

    Returns:
        当前登录用户对象

    Raises:
        AuthError: Token 缺失或无效时抛出
    """
    if not credentials:
        raise AuthError("缺少 Token")
    return await _resolve_current_user_from_token(credentials.credentials, session)


async def get_current_user_flexible(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer_scheme),
    token: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> User:
    """FastAPI 依赖项：灵活获取当前用户（支持 Header 或 Query 参数）。

    同时支持从 Authorization 头和 URL query 参数中提取 Token。
    用于 WebSocket 等不支持自定义 Header 的场景。

    Args:
        credentials: HTTP Bearer Token 凭证（可选）
        token: URL query 参数中的 Token（可选）
        session: 数据库会话

    Returns:
        当前登录用户对象

    Raises:
        AuthError: 两种方式都没有提供有效 Token 时抛出
    """
    # 优先使用 Header 中的 Token，其次使用 Query 参数中的 Token
    resolved_token = credentials.credentials if credentials else token
    if not resolved_token:
        raise AuthError("缺少 Token")
    return await _resolve_current_user_from_token(resolved_token, session)
