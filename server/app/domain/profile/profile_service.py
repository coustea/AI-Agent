"""
用户画像服务。

从 MemoryService 拆分：UserProfile 读写 + 历史版本管理。
"""

import json

from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.engine import engine
from app.core.logging import get_logger
from app.models.profile import UserProfile, UserProfileHistory

logger = get_logger(__name__)


class ProfileService:
    """用户画像（UserProfile）的读写与版本快照。"""

    def __init__(self) -> None:
        self.engine = engine

    async def get_user_profile(self, user_id: int) -> UserProfile | None:
        """获取用户的完整画像记录。"""
        async with AsyncSession(self.engine) as session:
            stmt = select(UserProfile).where(UserProfile.user_id == user_id)
            result = await session.exec(stmt)
            return result.first()

    async def update_user_profile(
        self,
        user_id: int,
        features: dict,
        change_reason: str = "系统自动更新",
        source_memory_ids: list[int] | None = None,
    ) -> UserProfile:
        """更新用户的画像特征，并自动记录快照历史。"""
        async with AsyncSession(self.engine) as session:
            stmt = select(UserProfile).where(UserProfile.user_id == user_id).with_for_update()
            result = await session.exec(stmt)
            profile = result.first()

            if not profile:
                profile = UserProfile(user_id=user_id)

            for key, value in features.items():
                if hasattr(profile, key) and value is not None:
                    setattr(profile, key, value)

            session.add(profile)
            await session.commit()
            await session.refresh(profile)

            full_profile_data = profile.model_dump(exclude={"user_id", "updated_at", "created_at"})

            history_stmt = select(func.max(UserProfileHistory.version)).where(UserProfileHistory.user_id == user_id)
            result = await session.exec(history_stmt)
            max_version = result.one_or_none() or 0

            snapshot = UserProfileHistory(
                user_id=user_id,
                version=max_version + 1,
                change_reason=change_reason,
                source_memory_ids=json.dumps(source_memory_ids) if source_memory_ids else None,
                **full_profile_data,
            )
            session.add(snapshot)
            await session.commit()
            return profile

    async def get_profile_history(
        self, user_id: int, limit: int = 20
    ) -> list[UserProfileHistory]:
        """获取用户画像的变更历史快照列表。"""
        async with AsyncSession(self.engine) as session:
            stmt = (
                select(UserProfileHistory)
                .where(UserProfileHistory.user_id == user_id)
                .order_by(UserProfileHistory.version.desc())
                .limit(limit)
            )
            result = await session.exec(stmt)
            return list(result.all())


profile_service = ProfileService()
