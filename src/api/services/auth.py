"""Authentication service using MySQL for users and Redis for tokens."""

from datetime import datetime, timezone
from typing import Optional, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.core.security import get_password_hash, verify_password
from api.core.redis import get_redis
from api.utils.jwt import create_access_token, verify_token


TOKEN_EXPIRE_SECONDS = 7 * 24 * 60 * 60


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, username: str, password: str) -> dict:
        username = username.lower()

        result = await self.db.execute(select(User).where(User.username == username))
        if result.scalar_one_or_none():
            raise ValueError("Username already registered")

        user = User(username=username, password_hash=get_password_hash(password))
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        return user.to_dict()

    async def login(self, username: str, password: str) -> dict:
        username = username.lower()

        result = await self.db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            raise ValueError("Invalid username or password")

        token = create_access_token(username)

        redis = get_redis()
        redis.set(f"{username}:{token}", token, ex=TOKEN_EXPIRE_SECONDS)

        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": TOKEN_EXPIRE_SECONDS,
            "user": user.to_dict(),
        }

    async def logout(self, username: str, token: str) -> bool:
        redis = get_redis()
        redis.delete(f"{username}:{token}")
        return True

    async def change_password(
        self, username: str, old_password: str, new_password: str
    ) -> bool:
        username = username.lower()

        result = await self.db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError("User not found")

        if not verify_password(old_password, user.password_hash):
            raise ValueError("Invalid old password")

        user.password_hash = get_password_hash(new_password)
        user.updated_at = datetime.now(timezone.utc)
        await self.db.commit()

        return True

    async def get_user(self, username: str) -> Optional[dict]:
        username = username.lower()

        result = await self.db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        return user.to_dict() if user else None

    async def verify_token_valid(self, token: str) -> Dict:
        payload = verify_token(token)
        if not payload:
            raise ValueError("Invalid token")

        username = payload.get("sub")
        if not username:
            raise ValueError("Invalid token payload")

        redis = get_redis()
        if not redis.exists(f"{username}:{token}"):
            raise ValueError("Token expired or revoked")

        user = await self.get_user(username)
        if not user:
            raise ValueError("User not found")

        return user
