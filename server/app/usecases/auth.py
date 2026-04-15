"""Auth use cases."""

from __future__ import annotations

from sqlmodel.ext.asyncio.session import AsyncSession

from app.adapters.auth.security import revoke_token
from app.adapters.repositories.user_account_store import UserAccountStore
from app.ports.runtime import ProfileRuntime


class AuthUseCases:
    def __init__(self, account_store: UserAccountStore, profile_runtime: ProfileRuntime) -> None:
        self.account_store = account_store
        self.profile_runtime = profile_runtime

    async def register(self, session: AsyncSession, data):
        return await self.account_store.register(session, data)

    async def login(self, session: AsyncSession, data):
        return await self.account_store.authenticate(session, data.username, data.password)

    async def update_me(self, session: AsyncSession, user_id: int, data):
        return await self.account_store.update(session, user_id, data)

    async def logout(self, session: AsyncSession, token: str) -> None:
        await revoke_token(token, session)

    async def build_profile_on_logout(self, user_id: int) -> None:
        await self.profile_runtime.build_profile(user_id=user_id)
