"""Auth service — 用户账号存储 + 认证用例。"""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.schemas import UserLogin, UserRead, UserRegister, UserUpdate
from app.auth.security import create_token, hash_password, revoke_token, verify_password
from app.infra.models import User


def _read_user(user: User) -> UserRead:
    return UserRead.model_validate(user)


class UserAccountStore:
    """用户账号持久化。"""

    async def register(self, session: AsyncSession, data: UserRegister) -> dict[str, UserRead] | None:
        existing = (await session.exec(select(User).where(User.username == data.username))).first()
        if existing:
            return None
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
            return None
        await session.refresh(user)
        return {"user": _read_user(user)}

    async def authenticate(self, session: AsyncSession, username: str, password: str) -> dict[str, str | UserRead] | None:
        user = (await session.exec(select(User).where(User.username == username))).first()
        if not user:
            return None
        await session.refresh(user)
        if not verify_password(password, user.password):
            return None
        # 记录首次登录状态，返回给前端判断是否弹窗
        is_first_login = user.is_first_login
        user_read = _read_user(user)
        token = await create_token(user.id, session)
        # 首次登录后标记为 False
        if is_first_login:
            user.is_first_login = False
            session.add(user)
            await session.commit()
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
        """登出后触发画像构建（懒加载 memory runtime）。"""
        from app.memory import MemoryService

        await MemoryService(module="mentor").upsert_profile(user_id=user_id, reason="logout")


# 模块级单例
account_store = UserAccountStore()
auth_usecases = AuthUseCases(account_store)
