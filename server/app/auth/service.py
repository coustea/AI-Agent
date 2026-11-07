"""认证业务服务层。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.schemas import UserLogin, UserRead, UserRegister, UserUpdate
from app.auth.security import AuthError, create_token, hash_password, verify_password
from app.infra.logging import get_logger
from app.infra.models import User, UserDailyActivity

logger = get_logger(__name__)
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


async def record_daily_login_activity(
    session: AsyncSession,
    *,
    user_id: int,
    logged_in_at: datetime | None = None,
) -> None:
    """记录用户当天首次登录事实，重复登录不重复计数。"""
    occurred_at = logged_in_at or datetime.now(timezone.utc)
    activity_date = occurred_at.astimezone(SHANGHAI_TZ).date()
    existing = await session.scalar(
        select(UserDailyActivity).where(
            UserDailyActivity.user_id == user_id,
            UserDailyActivity.activity_date == activity_date,
        )
    )
    if existing is not None:
        return

    session.add(
        UserDailyActivity(
            user_id=user_id,
            activity_date=activity_date,
            first_login_at=occurred_at,
        )
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()


class AuthService:
    """用户认证与账号业务逻辑。"""

    async def register(self, session: AsyncSession, data: UserRegister) -> UserRead:
        """注册新用户，用户名重复时直接抛出 AuthError。"""
        existing = (await session.exec(select(User).where(User.username == data.username))).first()
        if existing:
            logger.warning("[Auth] 注册失败，用户名已存在: %s", data.username)
            raise AuthError("该用户名已被注册，请换一个试试", field="username", code=400)

        user = User(
            username=data.username,
            password=hash_password(data.password),
            email=data.email,
        )
        session.add(user)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            logger.warning("[Auth] 注册并发冲突: %s", data.username)
            raise AuthError("该用户名已被注册，请换一个试试", field="username", code=400)

        await session.refresh(user)
        logger.info("[Auth] 注册成功: username=%s user_id=%s", user.username, user.id)
        return UserRead.model_validate(user)

    async def login(self, session: AsyncSession, data: UserLogin) -> dict[str, Any]:
        """验证用户名密码并签发包含常用信息的 JWT Token。"""
        user = (await session.exec(select(User).where(User.username == data.username))).first()
        if not user:
            logger.warning("[Auth] 登录失败，用户不存在: %s", data.username)
            raise AuthError("该用户名未注册", field="username", code=401)

        await session.refresh(user)
        if not verify_password(data.password, user.password):
            logger.warning("[Auth] 登录失败，密码错误: user_id=%s", user.id)
            raise AuthError("密码不正确，请重新输入", field="password", code=401)

        token = create_token(user)
        await record_daily_login_activity(session, user_id=user.id)
        logger.info("[Auth] 登录成功: user_id=%s username=%s", user.id, user.username)
        return {
            "token": token,
            "user": UserRead.model_validate(user),
        }

    async def update_profile(
        self, session: AsyncSession, user_id: int, data: UserUpdate
    ) -> UserRead:
        """更新当前用户的基本信息。"""
        user = await session.get(User, user_id)
        if not user:
            raise AuthError("用户不存在", code=404)

        await session.refresh(user)
        update_data = data.model_dump(exclude_unset=True)
        if update_data:
            user.sqlmodel_update(update_data)
            session.add(user)
            await session.commit()
            await session.refresh(user)

        logger.info("[Auth] 更新用户信息成功: user_id=%s fields=%s", user_id, list(update_data.keys()))
        return UserRead.model_validate(user)


auth_service = AuthService()

__all__ = ["AuthService", "auth_service", "record_daily_login_activity"]
