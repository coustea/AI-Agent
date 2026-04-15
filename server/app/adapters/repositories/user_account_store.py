"""User-account repository adapter."""

from __future__ import annotations

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.adapters.auth.security import create_token, hash_password, verify_password
from app.models.user import User
from app.shared.dto.auth import UserRead


class UserAccountStore:
    async def register(self, session: AsyncSession, data) -> dict | None:
        existing = (await session.exec(select(User).where(User.username == data.username))).first()
        if existing:
            return None
        user = User(
            username=data.username,
            password=hash_password(data.password),
            email=data.email,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return {"user": UserRead.model_validate(user)}

    async def authenticate(self, session: AsyncSession, username: str, password: str) -> dict | None:
        user = (await session.exec(select(User).where(User.username == username))).first()
        if not user:
            return None
        await session.refresh(user)
        if not verify_password(password, user.password):
            return None
        token = await create_token(user.id, session)
        return {"token": token, "user": UserRead.model_validate(user)}

    async def update(self, session: AsyncSession, user_id: int, data) -> User | None:
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
