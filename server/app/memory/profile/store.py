"""画像存储层。

模块职责：
- 画像 CRUD 操作
- 画像历史管理
"""

from __future__ import annotations

from typing import Any

from sqlmodel import func, select

from app.infra.models import UserProfile, UserProfileHistory
from app.memory.core.base_store import BaseStore
from app.memory.core.utils import now
from app.memory.profile.types import make_default_profile_json, make_default_score_json


class ProfileStore(BaseStore):
    """画像存储。"""

    async def get_or_create(
        self,
        user_id: int,
        module: str = "mentor",
    ) -> UserProfile:
        """获取或创建画像。

        使用数据库唯一约束处理并发创建冲突：
        - 先尝试创建，如果违反唯一约束则回滚并查询现有记录
        - 避免"先查后插"的竞态条件
        """
        from sqlalchemy.exc import IntegrityError

        async with await self._get_session() as session:
            # 先尝试直接创建（乐观策略）
            profile = UserProfile(
                user_id=user_id,
                module=module,
                profile_json=make_default_profile_json(),
                profile_score_json=make_default_score_json(),
            )
            session.add(profile)
            try:
                await session.commit()
                await session.refresh(profile)
                return profile
            except IntegrityError:
                # 唯一约束冲突，说明已存在，回滚并查询
                await session.rollback()
                stmt = select(UserProfile).where(
                    UserProfile.user_id == user_id,
                    UserProfile.module == module,
                )
                existing = (await session.exec(stmt)).first()
                if existing:
                    return existing
                # 如果查询不到，重新抛出异常（不应发生）
                raise

    async def get(self, user_id: int, module: str = "mentor") -> UserProfile | None:
        """获取画像。"""
        async with await self._get_session() as session:
            stmt = select(UserProfile).where(
                UserProfile.user_id == user_id,
                UserProfile.module == module,
            )
            return (await session.exec(stmt)).first()

    async def update(
        self,
        user_id: int,
        module: str,
        profile_json: dict[str, Any] | None = None,
        score_json: dict[str, Any] | None = None,
        updated_reason: str | None = None,
        source_session_ids: list[str] | None = None,
        confidence: float = 0.7,
    ) -> UserProfile:
        """更新画像并创建历史快照。"""
        async with await self._get_session() as session:
            async with session.begin():
                stmt = select(UserProfile).where(
                    UserProfile.user_id == user_id,
                    UserProfile.module == module,
                )
                profile = (await session.exec(stmt)).first()

                if not profile:
                    profile = UserProfile(
                        user_id=user_id,
                        module=module,
                        profile_json=profile_json or make_default_profile_json(),
                        profile_score_json=score_json or make_default_score_json(),
                        confidence=confidence,
                    )
                else:
                    if profile_json is not None:
                        profile.profile_json = profile_json
                    if score_json is not None:
                        profile.profile_score_json = score_json
                    profile.version = (profile.version or 1) + 1
                    profile.confidence = confidence

                if updated_reason:
                    profile.updated_reason = updated_reason
                if source_session_ids:
                    profile.source_session_ids = source_session_ids

                session.add(profile)
                await session.flush()

                # 创建历史快照
                latest_version = (await session.exec(
                    select(func.max(UserProfileHistory.version)).where(
                        UserProfileHistory.user_id == user_id,
                        UserProfileHistory.module == module,
                    )
                )).one()

                history = UserProfileHistory(
                    user_id=user_id,
                    module=module,
                    version=0 if latest_version is None else int(latest_version) + 1,
                    profile_json=profile_json or make_default_profile_json(),
                    profile_score_json=score_json or make_default_score_json(),
                    change_reason=updated_reason,
                    source_session_ids=source_session_ids,
                )
                session.add(history)

            await session.refresh(profile)
            return profile

    async def get_history(
        self,
        user_id: int,
        module: str = "mentor",
        limit: int = 20,
    ) -> list[UserProfileHistory]:
        """获取画像历史。"""
        async with await self._get_session() as session:
            stmt = (
                select(UserProfileHistory)
                .where(
                    UserProfileHistory.user_id == user_id,
                    UserProfileHistory.module == module,
                )
                .order_by(UserProfileHistory.created_at.desc())
                .limit(limit)
            )
            result = await session.exec(stmt)
            return list(result.all())
