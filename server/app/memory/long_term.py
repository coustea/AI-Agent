"""
长期记忆服务。

从 MemoryService 拆分：UserMemory 读写、去重/合并、按类型查询。
"""

from collections import defaultdict
from typing import Iterable

from sqlalchemy import or_
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.database import engine
from app.infra.logging import get_logger
from app.infra.models import UserMemory
from app.memory.helpers import normalize_text, now

logger = get_logger(__name__)

DEFAULT_MEMORY_TYPE_LIMITS: dict[str, int] = {
    "preference": 3,
    "goal": 2,
    "weakness": 3,
    "fact": 3,
    "background": 2,
}


class LongTermMemoryService:
    """长期记忆（UserMemory）的读写、去重/合并、按类型查询。"""

    def __init__(self) -> None:
        self.engine = engine

    @staticmethod
    def _should_merge_fact(memory_type: str, new_text: str, existing_text: str) -> bool:
        """同类长期记忆的轻量合并策略，避免重复堆叠。"""
        if memory_type not in {"goal", "preference", "weakness"}:
            return False
        if not existing_text:
            return False
        normalized_new = normalize_text(new_text)
        normalized_existing = normalize_text(existing_text)
        if not normalized_new or not normalized_existing:
            return False
        return normalized_new in normalized_existing or normalized_existing in normalized_new

    async def save_user_fact(
        self,
        user_id: int,
        content: str,
        memory_type: str,
        session_id: str | None = None,
        expires_at=None,
    ) -> UserMemory:
        """保存单条用户事实/偏好到 UserMemory 表（带去重/合并/计数）。"""
        async with AsyncSession(self.engine) as session:
            _now = now()
            normalized_content = normalize_text(content)

            # 1) 精确重复去重
            exact_stmt = (
                select(UserMemory)
                .where(
                    UserMemory.user_id == user_id,
                    UserMemory.source == "fact_agent",
                    UserMemory.memory_type == memory_type,
                    or_(UserMemory.expires_at == None, UserMemory.expires_at > _now),  # noqa: E711
                )
                .order_by(UserMemory.created_at.desc())
            )
            candidates = list((await session.exec(exact_stmt)).all())

            for duplicate in candidates:
                if normalize_text(duplicate.content) == normalized_content:
                    duplicate.evidence_count = max(1, duplicate.evidence_count) + 1
                    duplicate.last_seen_at = _now
                    duplicate.session_id = session_id or duplicate.session_id
                    if expires_at:
                        duplicate.expires_at = expires_at
                    session.add(duplicate)
                    await session.commit()
                    await session.refresh(duplicate)
                    return duplicate

            # 2) 同类型语义近似合并（规则）
            for candidate in candidates:
                if self._should_merge_fact(memory_type, content, candidate.content):
                    merged_content = candidate.content
                    if len(content) > len(candidate.content):
                        merged_content = content
                    candidate.content = merged_content
                    candidate.evidence_count = max(1, candidate.evidence_count) + 1
                    candidate.last_seen_at = _now
                    candidate.session_id = session_id or candidate.session_id
                    if expires_at:
                        candidate.expires_at = expires_at
                    session.add(candidate)
                    await session.commit()
                    await session.refresh(candidate)
                    return candidate

            memory = UserMemory(
                user_id=user_id,
                session_id=session_id or "",
                content=content,
                memory_type=memory_type,
                source="fact_agent",
                expires_at=expires_at,
                evidence_count=1,
                last_seen_at=_now,
            )
            session.add(memory)
            await session.commit()
            await session.refresh(memory)
            return memory

    async def get_user_facts(self, user_id: int, limit: int = 50) -> list[UserMemory]:
        """兼容旧接口：获取用户长期事实。"""
        memories_by_type = await self.get_user_context_memories(
            user_id=user_id,
            per_type_limits={"fact": limit, "preference": limit, "goal": limit, "weakness": limit, "background": limit},
        )
        flat: list[UserMemory] = []
        for _, items in memories_by_type.items():
            flat.extend(items)
        flat.sort(key=lambda x: x.last_seen_at or x.created_at, reverse=True)
        return flat[:limit]

    async def get_user_context_memories(
        self,
        user_id: int,
        memory_types: Iterable[str] | None = None,
        per_type_limits: dict[str, int] | None = None,
        only_unexpired: bool = True,
    ) -> dict[str, list[UserMemory]]:
        """按类型返回用于上下文注入的长期记忆，自动去重与限量。"""
        target_types = list(memory_types) if memory_types else list(DEFAULT_MEMORY_TYPE_LIMITS.keys())
        limits = dict(DEFAULT_MEMORY_TYPE_LIMITS)
        if per_type_limits:
            limits.update(per_type_limits)

        async with AsyncSession(self.engine) as session:
            _now = now()
            stmt = select(UserMemory).where(
                UserMemory.user_id == user_id,
                UserMemory.source == "fact_agent",
            )
            if target_types:
                stmt = stmt.where(UserMemory.memory_type.in_(target_types))
            if only_unexpired:
                stmt = stmt.where(or_(UserMemory.expires_at == None, UserMemory.expires_at > _now))  # noqa: E711
            stmt = stmt.order_by(UserMemory.last_seen_at.desc(), UserMemory.created_at.desc())
            result = await session.exec(stmt)
            memories = list(result.all())

        grouped: dict[str, list[UserMemory]] = defaultdict(list)
        seen_by_type: dict[str, set[str]] = defaultdict(set)
        for item in memories:
            m_type = item.memory_type or "fact"
            if m_type not in target_types:
                continue
            normalized = normalize_text(item.content)
            if not normalized or normalized in seen_by_type[m_type]:
                continue
            limit = max(0, limits.get(m_type, 2))
            if len(grouped[m_type]) >= limit:
                continue
            seen_by_type[m_type].add(normalized)
            grouped[m_type].append(item)

        return {m_type: grouped.get(m_type, []) for m_type in target_types}

    async def get_long_term_memories(
        self,
        user_id: int,
        module: str | None = None,
        limit: int = 10,
        only_unexpired: bool = True,
    ) -> list[UserMemory]:
        """获取用户长期记忆列表。"""
        async with AsyncSession(self.engine) as session:
            stmt = select(UserMemory).where(UserMemory.user_id == user_id)
            if module is not None:
                stmt = stmt.where(UserMemory.source == module)
            if only_unexpired:
                _now = now()
                stmt = stmt.where(or_(UserMemory.expires_at == None, UserMemory.expires_at > _now))  # noqa: E711
            stmt = stmt.order_by(UserMemory.created_at.desc()).limit(limit)
            result = await session.exec(stmt)
            return list(result.all())

    async def save_long_term_memory(
        self,
        user_id: int,
        session_id: str,
        content: str,
        memory_type: str,
        dimension: str | None = None,
        importance: float = 0.5,
        source: str = "conversation",
        source_message_count: int = 0,
    ) -> UserMemory:
        """将 LLM 提炼的长期记忆条目写入 user_memory 表。"""
        async with AsyncSession(self.engine) as session:
            memory = UserMemory(
                user_id=user_id,
                session_id=session_id,
                content=content,
                memory_type=memory_type,
                dimension=dimension,
                importance=importance,
                source=source,
                source_message_count=source_message_count,
                evidence_count=1,
                last_seen_at=now(),
            )
            session.add(memory)
            await session.commit()
            await session.refresh(memory)
            logger.info(f"[LongTermMemory] 保存长期记忆: user={user_id}, type={memory_type}")
            return memory


long_term_service = LongTermMemoryService()
