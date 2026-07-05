"""认证业务服务层。

负责用户账号的持久化存储（CRUD）以及认证相关用例的编排，
包括注册、登录、登出、用户信息更新等操作。"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.schemas import UserLogin, UserRead, UserRegister, UserUpdate
from app.auth.security import create_token, hash_password, revoke_token, verify_password
from app.infra.logging import get_logger
from app.infra.models import User

logger = get_logger(__name__)


def _read_user(user: User) -> UserRead:
    """将 User ORM 对象转换为 UserRead 响应模型。"""
    return UserRead.model_validate(user)


@dataclass
class AuthResult:
    """认证操作结果 — 统一成功/失败的数据载体。

    成功时 data 有值，失败时 error_field + error_message 有值。
    前端可根据 error_field 将错误绑定到对应表单字段。
    """
    success: bool = False
    data: dict | None = None
    # 失败时：错误对应的表单字段（username / password / email / "" 表示全局）
    error_field: str = ""
    # 失败时：面向用户的精确错误提示
    error_message: str = ""


class UserAccountStore:
    """用户账号持久化 — 负责 CRUD 操作。"""

    async def register(self, session: AsyncSession, data: UserRegister) -> AuthResult:
        """注册新用户，返回 AuthResult。"""
        existing = (await session.exec(select(User).where(User.username == data.username))).first()
        if existing:
            logger.warning("[Auth] 注册失败，用户名已存在: %s", data.username)
            return AuthResult(error_field="username", error_message="该用户名已被注册，请换一个试试")

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
            return AuthResult(error_field="username", error_message="该用户名已被注册，请换一个试试")
        await session.refresh(user)
        return AuthResult(success=True, data={"user": _read_user(user)})

    async def authenticate(self, session: AsyncSession, username: str, password: str) -> AuthResult:
        """验证用户名密码，返回 AuthResult。

        失败时 error_field 指向具体的表单字段，error_message 提供精确原因。
        """
        user = (await session.exec(select(User).where(User.username == username))).first()
        if not user:
            logger.warning("[Auth] 登录失败，用户不存在: %s", username)
            return AuthResult(error_field="username", error_message="该用户名未注册")

        await session.refresh(user)
        if not verify_password(password, user.password):
            logger.warning("[Auth] 登录失败，密码错误: user_id=%s", user.id)
            return AuthResult(error_field="password", error_message="密码不正确，请重新输入")

        logger.info("[Auth] 登录成功: user_id=%s", user.id)
        user_read = _read_user(user)
        token = await create_token(user.id, session)
        return AuthResult(success=True, data={"token": token, "user": user_read})

    async def update(self, session: AsyncSession, user_id: int, data: UserUpdate) -> User | None:
        """更新用户信息，仅更新提交的非空字段。"""
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

    async def register(self, session: AsyncSession, data: UserRegister) -> AuthResult:
        """注册新用户。"""
        return await self.account_store.register(session, data)

    async def login(self, session: AsyncSession, data: UserLogin) -> AuthResult:
        """用户登录，验证凭据并签发 Token。"""
        return await self.account_store.authenticate(session, data.username, data.password)

    async def update_me(self, session: AsyncSession, user_id: int, data: UserUpdate) -> User | None:
        """更新当前用户信息。"""
        return await self.account_store.update(session, user_id, data)

    async def logout(self, session: AsyncSession, token: str) -> None:
        """用户登出，撤销 Token。"""
        await revoke_token(token, session)

    async def upsert_profile_on_logout(self, user_id: int) -> None:
        """登出时更新用户画像（V2 版本暂无需要同步的兼容性数据）。"""
        return None


# 模块级单例
account_store = UserAccountStore()
auth_usecases = AuthUseCases(account_store)
