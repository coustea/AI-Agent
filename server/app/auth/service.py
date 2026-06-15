"""Auth service — 用户账号存储 + 认证用例。"""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.schemas import UserLogin, UserRead, UserRegister, UserUpdate
from app.auth.security import create_token, hash_password, revoke_token, verify_password
from app.infra.logging import get_logger
from app.infra.models import User

logger = get_logger(__name__)


def _read_user(user: User) -> UserRead:
    return UserRead.model_validate(user)


class UserAccountStore:
    """用户账号持久化 — 负责 CRUD 操作。"""

    async def register(self, session: AsyncSession, data: UserRegister) -> dict[str, UserRead] | None:
        """注册新用户，返回 {"user": UserRead} 或 None（用户名已存在）。"""
        existing = (await session.exec(select(User).where(User.username == data.username))).first()  # 检查用户名唯一性
        if existing:
            logger.warning("[Auth] 注册失败，用户名已存在: %s", data.username)
            return None
        user = User(
            username=data.username,
            password=hash_password(data.password),  # bcrypt 哈希密码
            email=data.email,
        )
        session.add(user)  # 标记待插入
        try:
            await session.commit()  # 提交事务
        except IntegrityError:  # 并发注册导致唯一约束冲突
            await session.rollback()
            logger.warning("[Auth] 注册并发冲突: %s", data.username)
            return None
        await session.refresh(user)  # 刷新获取数据库生成的默认值（id, created_at）
        return {"user": _read_user(user)}

    async def authenticate(self, session: AsyncSession, username: str, password: str) -> dict[str, str | UserRead] | None:
        """验证用户名密码，成功返回 {"token": str, "user": UserRead}。"""
        user = (await session.exec(select(User).where(User.username == username))).first()  # 按用户名查询
        if not user:
            logger.warning("[Auth] 登录失败，用户不存在: %s", username)
            return None
        await session.refresh(user)  # 确保 password 字段已加载（exclude=True 可能延迟加载）
        if not verify_password(password, user.password):  # bcrypt 校验密码
            logger.warning("[Auth] 登录失败，密码错误: user_id=%s", user.id)
            return None
        is_first_login = user.is_first_login  # 记录首次登录状态，返回给前端判断是否弹窗
        user_read = _read_user(user)
        token = await create_token(user.id, session)  # 签发 JWT 并写入白名单
        # is_first_login 由引导页面或用户选择不再弹出时调用接口设置，不在登录时自动重置
        logger.info("[Auth] 登录成功: user_id=%s", user.id)
        return {"token": token, "user": user_read}

    async def update(self, session: AsyncSession, user_id: int, data: UserUpdate) -> User | None:
        user = await session.get(User, user_id)
        if not user:
            return None
        await session.refresh(user)
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return user
        user.sqlmodel_update(update_data)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


class AuthUseCases:
    """认证相关用例：注册、登录、登出、更新。"""

    def __init__(self, account_store: UserAccountStore) -> None:
        self.account_store = account_store

    async def register(self, session: AsyncSession, data: UserRegister) -> dict[str, UserRead] | None:
        return await self.account_store.register(session, data)

    async def login(self, session: AsyncSession, data: UserLogin) -> dict[str, str | UserRead] | None:
        return await self.account_store.authenticate(session, data.username, data.password)

    async def update_me(self, session: AsyncSession, user_id: int, data: UserUpdate) -> User | None:
        return await self.account_store.update(session, user_id, data)

    async def logout(self, session: AsyncSession, token: str) -> None:
        await revoke_token(token, session)

    async def upsert_profile_on_logout(self, user_id: int) -> None:
        """Profile V2 has no logout-triggered compatibility update."""
        return None


# 模块级单例
account_store = UserAccountStore()
auth_usecases = AuthUseCases(account_store)
