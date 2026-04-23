"""Memory storage and lifecycle management.  # 记忆存储与生命周期管理模块

This module owns:
- session CRUD
- short-term memory CRUD
- long-term memory CRUD
- token counters and thresholds
- memory compression
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Iterable

from sqlalchemy import or_
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.database import engine
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.models import ChatMessage, ChatSession, UserMemory
from app.memory.memory_types import (
    FACT_AGENT_MEMORY_TYPES,
    MEMORY_TYPE_BACKGROUND,
    MEMORY_TYPE_FACT,
    MEMORY_TYPE_GOAL,
    MEMORY_TYPE_PREFERENCE,
    MEMORY_TYPE_SUMMARY,
    MEMORY_TYPE_WEAKNESS,
)

logger = get_logger(__name__)

SHORT_TERM_MESSAGE_EXPIRE_DAYS = 7  # 短期记忆过期天数
MEMORY_COMPRESSION_TOKEN_THRESHOLD = 150  # 触发记忆压缩的token阈值
MEMORY_EXTRACTION_TOKEN_THRESHOLD = 80  # 触发事实提取的token阈值
PROFILE_UPDATE_TOKEN_THRESHOLD = 120  # 触发画像更新的token阈值

DEFAULT_MEMORY_TYPE_LIMITS: dict[str, int] = {  # 各类型记忆的默认数量上限
    MEMORY_TYPE_PREFERENCE: 3,
    MEMORY_TYPE_GOAL: 2,
    MEMORY_TYPE_WEAKNESS: 3,
    MEMORY_TYPE_FACT: 3,
    MEMORY_TYPE_BACKGROUND: 2,
}

_TERM_PATTERN = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]+", re.IGNORECASE)  # 用于分词的正则：匹配英文/数字或中文
_SOURCE_WEIGHTS: dict[str, float] = {"fact_agent": 1.0, "conversation": 0.94}  # 不同来源的权重系数
_INITIAL_IMPORTANCE_BY_TYPE: dict[str, float] = {  # 各类型记忆的初始重要性分数
    "preference": 0.66,
    "goal": 0.7,
    "weakness": 0.62,
    "fact": 0.58,
    "background": 0.54,
}
_MIN_OVERLAP_BY_TYPE: dict[str, float] = {  # 判断记忆重叠的最小阈值
    "preference": 0.4,
    "goal": 0.4,
    "weakness": 0.4,
    "fact": 0.45,
    "background": 0.45,
}


def normalize_text(content: str) -> str:  # 标准化文本：去首尾空白、小写、压缩空格
    return " ".join((content or "").strip().lower().split())


def now() -> datetime:  # 获取当前时间
    return datetime.now()


def message_expire_cutoff(days: int = SHORT_TERM_MESSAGE_EXPIRE_DAYS) -> datetime:  # 计算消息过期截止时间
    return now() - timedelta(days=max(days, 0))


def estimate_token_count(text: str) -> int:  # 估算文本token数（简单启发式）
    stripped = (text or "").strip()
    if not stripped:
        return 0
    return max(max(1, len(stripped) // 4), len(stripped.split()))


@dataclass(frozen=True, slots=True)
class MergeDecision:  # 记忆合并决策：候选记忆、匹配分数、关系类型
    candidate: Any
    match_score: float
    relation: str


def clamp_importance(value: float | None, *, default: float = 0.5) -> float:  # 将重要性值限制在[0,1]区间
    if value is None:
        return default
    return max(0.0, min(1.0, float(value)))


def source_weight(source: str | None) -> float:  # 获取来源权重，未知来源返回默认值
    if not source:
        return 1.0
    return _SOURCE_WEIGHTS.get(source.strip().lower(), 0.96)


def initial_fact_importance(memory_type: str, source: str | None = "fact_agent") -> float:  # 计算新记忆的初始重要性
    base = _INITIAL_IMPORTANCE_BY_TYPE.get((memory_type or "").strip().lower(), 0.55)
    return clamp_importance(base * source_weight(source))


def _extract_terms(content: str | None) -> set[str]:  # 从文本中提取术语集合（用于计算重叠度）
    normalized = normalize_text(content or "")
    if not normalized:
        return set()
    terms: set[str] = set()
    for chunk in _TERM_PATTERN.findall(normalized):
        if not chunk:
            continue
        if chunk.isascii() or len(chunk) == 1:
            terms.add(chunk)
            continue
        terms.add(chunk)
        terms.update(chunk[index : index + 2] for index in range(len(chunk) - 1))  # 中文额外提取bigram
    return terms


def content_information_score(content: str | None) -> float:  # 计算内容信息量分数（用于选择更丰富的内容）
    normalized = normalize_text(content or "")
    if not normalized:
        return 0.0
    terms = _extract_terms(normalized)
    alpha_bonus = sum(1 for char in normalized if char.isalpha())
    digit_bonus = sum(1 for char in normalized if char.isdigit())
    return float(len(normalized) + len(terms) * 4 + alpha_bonus * 0.5 + digit_bonus)


def choose_more_informative_content(existing_content: str | None, new_content: str | None) -> str:  # 选择信息量更大的内容
    existing = existing_content or ""
    incoming = new_content or ""
    if content_information_score(incoming) > content_information_score(existing):
        return incoming
    return existing


def memory_overlap_score(new_text: str | None, existing_text: str | None) -> float:  # 计算两段文本的术语重叠度（Jaccard相似度）
    normalized_new = normalize_text(new_text or "")
    normalized_existing = normalize_text(existing_text or "")
    if not normalized_new or not normalized_existing:
        return 0.0
    if normalized_new == normalized_existing:
        return 1.0

    new_terms = _extract_terms(normalized_new)
    existing_terms = _extract_terms(normalized_existing)
    if not new_terms or not existing_terms:
        return 0.0

    intersection = new_terms & existing_terms
    union = new_terms | existing_terms
    return len(intersection) / len(union)


def classify_merge_relation(memory_type: str, new_text: str | None, existing_text: str | None) -> tuple[str, float]:  # 分类两条记忆的关系：exact/containment/overlap/none
    normalized_new = normalize_text(new_text or "")
    normalized_existing = normalize_text(existing_text or "")
    if not normalized_new or not normalized_existing:
        return "none", 0.0
    if normalized_new == normalized_existing:
        return "exact", 1.0
    if normalized_new in normalized_existing or normalized_existing in normalized_new:
        return "containment", 0.95

    overlap = memory_overlap_score(normalized_new, normalized_existing)
    threshold = _MIN_OVERLAP_BY_TYPE.get((memory_type or "").strip().lower(), 0.55)
    if overlap >= threshold:
        return "overlap", 0.7 + overlap * 0.25
    return "none", 0.0


def score_merge_candidate(memory_type: str, new_text: str | None, candidate: Any) -> MergeDecision | None:  # 为候选记忆计算匹配分数
    relation, relation_score = classify_merge_relation(memory_type, new_text, getattr(candidate, "content", None))
    if relation_score <= 0:
        return None

    candidate_importance = clamp_importance(getattr(candidate, "importance", None))
    evidence_count = max(1, int(getattr(candidate, "evidence_count", 1) or 1))
    last_seen_at = getattr(candidate, "last_seen_at", None) or getattr(candidate, "created_at", None)
    recency_score = last_seen_at.timestamp() if isinstance(last_seen_at, datetime) else 0.0
    tiebreak_score = candidate_importance * 0.05 + min(evidence_count, 10) * 0.03 + recency_score / 1_000_000_000_000
    return MergeDecision(candidate=candidate, match_score=relation_score + tiebreak_score, relation=relation)


def rank_merge_candidates(memory_type: str, new_text: str | None, candidates: Iterable[Any]) -> list[MergeDecision]:  # 按匹配分数排序所有候选记忆
    ranked = [decision for candidate in candidates if (decision := score_merge_candidate(memory_type, new_text, candidate))]
    ranked.sort(
        key=lambda item: (
            item.match_score,
            clamp_importance(getattr(item.candidate, "importance", None)),
            max(1, int(getattr(item.candidate, "evidence_count", 1) or 1)),
            (getattr(item.candidate, "last_seen_at", None) or getattr(item.candidate, "created_at", None) or datetime.min),
            len(normalize_text(getattr(item.candidate, "content", None) or "")),
        ),
        reverse=True,
    )
    return ranked


def bump_importance(  # 提升记忆重要性分数（基于证据次数和匹配分数）
    importance: float | None,
    *,
    source: str | None = None,
    evidence_count: int = 1,
    match_score: float = 0.0,
) -> float:
    base = clamp_importance(importance) * source_weight(source)
    evidence_bonus = min(max(evidence_count - 1, 0), 6) * 0.04
    match_bonus = max(0.0, min(1.0, match_score)) * 0.08
    return clamp_importance(base + evidence_bonus + match_bonus)


def rank_context_memory(memory: Any) -> tuple[float, int, datetime]:  # 计算记忆在上下文中的排序分数
    importance = clamp_importance(getattr(memory, "importance", None))
    evidence_count = max(1, int(getattr(memory, "evidence_count", 1) or 1))
    quality = importance * source_weight(getattr(memory, "source", None)) + min(max(evidence_count - 1, 0), 6) * 0.06
    last_seen_at = getattr(memory, "last_seen_at", None) or getattr(memory, "created_at", None) or datetime.min
    return quality, evidence_count, last_seen_at


class MemoryStore:  # 记忆存储核心类：管理会话、短期记忆、长期记忆的CRUD
    def __init__(self) -> None:
        self.engine = engine

    async def _get_owned_session(  # 验证会话归属并返回会话对象
        self,
        session: AsyncSession,
        user_id: int,
        session_id: str,
        module: str | None = None,
    ) -> ChatSession | None:
        stmt = select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)  # 查询会话并验证归属
        if module is not None:
            stmt = stmt.where(ChatSession.module == module)
        result = await session.exec(stmt)
        return result.first()

    async def create_chat_session(self, user_id: int, module: str, title: str = "新对话") -> ChatSession:  # 创建新聊天会话
        async with AsyncSession(self.engine) as session:
            chat_session = ChatSession(user_id=user_id, module=module, title=title)
            session.add(chat_session)
            await session.commit()
            await session.refresh(chat_session)
            return chat_session

    async def get_chat_session(self, session_id: str) -> ChatSession | None:  # 根据ID获取会话
        async with AsyncSession(self.engine) as session:
            stmt = select(ChatSession).where(ChatSession.id == session_id)
            return (await session.exec(stmt)).first()

    async def get_user_chat_sessions(self, user_id: int, module: str | None = None, limit: int = 20) -> list[ChatSession]:  # 获取用户的所有会话列表
        async with AsyncSession(self.engine) as session:
            stmt = select(ChatSession).where(ChatSession.user_id == user_id, ChatSession.is_archived == False)  # noqa: E712
            if module:
                stmt = stmt.where(ChatSession.module == module)
            stmt = stmt.order_by(ChatSession.updated_at.desc()).limit(limit)
            return list((await session.exec(stmt)).all())

    async def archive_chat_session(self, session_id: str, user_id: int) -> bool:  # 归档会话（软删除）
        async with AsyncSession(self.engine) as session:
            stmt = select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
            chat_session = (await session.exec(stmt)).first()
            if not chat_session:
                return False
            chat_session.is_archived = True
            session.add(chat_session)
            await session.commit()
            return True

    async def save_message(  # 保存一条聊天消息到短期记忆
        self,
        user_id: int,
        session_id: str,
        module: str,
        role: str,
        content: str,
        attachments: str | None = None,
        tool_calls: str | None = None,
    ) -> int:
        async with AsyncSession(self.engine) as session:
            session_stmt = select(ChatSession).where(ChatSession.id == session_id)
            chat_session = (await session.exec(session_stmt)).first()
            if chat_session:
                if chat_session.user_id != user_id or chat_session.module != module:
                    raise PermissionError("会话不属于当前用户或模块，禁止写入")
                chat_session.updated_at = now()
            else:
                chat_session = ChatSession(id=session_id, user_id=user_id, module=module, title=content[:20])
            session.add(chat_session)
            session.add(
                ChatMessage(
                    user_id=user_id,
                    session_id=session_id,
                    module=module,
                    role=role,
                    content=content,
                    attachments=attachments,
                    tool_calls=tool_calls,
                )
            )
            await session.commit()
        return await self.get_message_count(user_id, session_id, module)

    async def get_recent_messages(  # 获取最近的消息列表（支持过期过滤和数量限制）
        self,
        user_id: int,
        session_id: str,
        module: str,
        limit: int | None = None,
        days: int = SHORT_TERM_MESSAGE_EXPIRE_DAYS,
        only_unexpired: bool = True,
    ) -> list[ChatMessage]:
        async with AsyncSession(self.engine) as session:
            filters = [ChatMessage.user_id == user_id, ChatMessage.session_id == session_id, ChatMessage.module == module]
            if only_unexpired:
                filters.append(ChatMessage.created_at >= message_expire_cutoff(days))
            total = (await session.exec(select(func.count()).where(*filters))).one()
            stmt = select(ChatMessage).where(*filters).order_by(ChatMessage.created_at.asc())
            if limit is not None and limit > 0 and total > limit:
                stmt = stmt.offset(total - limit)
            return list((await session.exec(stmt)).all())

    async def get_message_count(self, user_id: int, session_id: str, module: str) -> int:  # 获取消息总数
        async with AsyncSession(self.engine) as session:
            stmt = select(func.count()).where(
                ChatMessage.user_id == user_id,
                ChatMessage.session_id == session_id,
                ChatMessage.module == module,
            )
            return (await session.exec(stmt)).one()

    async def get_message_token_count(  # 计算会话中的总token数
        self,
        user_id: int,
        session_id: str,
        module: str,
        days: int = SHORT_TERM_MESSAGE_EXPIRE_DAYS,
        only_unexpired: bool = True,
    ) -> int:
        messages = await self.get_recent_messages(user_id, session_id, module, None, days, only_unexpired)
        return sum(estimate_token_count(getattr(msg, "content", "")) for msg in messages)

    async def delete_old_messages(self, user_id: int, session_id: str, module: str, keep_recent: int = 10) -> int:  # 删除旧消息，保留最近N条
        async with AsyncSession(self.engine) as session:
            total = (
                await session.exec(
                    select(func.count()).where(
                        ChatMessage.user_id == user_id,
                        ChatMessage.session_id == session_id,
                        ChatMessage.module == module,
                    )
                )
            ).one()
            if total <= keep_recent:
                return 0
            cutoff_id = (
                await session.exec(
                    select(ChatMessage.id)
                    .where(
                        ChatMessage.user_id == user_id,
                        ChatMessage.session_id == session_id,
                        ChatMessage.module == module,
                    )
                    .order_by(ChatMessage.created_at.desc())
                    .offset(keep_recent - 1)
                    .limit(1)
                )
            ).first()
            if cutoff_id is None:
                return 0
            old_msgs = (
                await session.exec(
                    select(ChatMessage).where(
                        ChatMessage.user_id == user_id,
                        ChatMessage.session_id == session_id,
                        ChatMessage.module == module,
                        ChatMessage.id < cutoff_id,
                    )
                )
            ).all()
            deleted = len(old_msgs)
            for msg in old_msgs:
                await session.delete(msg)
            await session.commit()
            return deleted

    async def cleanup_expired_short_term_messages(  # 清理过期的短期记忆消息
        self,
        user_id: int,
        session_id: str,
        module: str,
        days: int = SHORT_TERM_MESSAGE_EXPIRE_DAYS,
    ) -> int:
        cutoff = message_expire_cutoff(days)
        async with AsyncSession(self.engine) as session:
            expired_msgs = list(
                (
                    await session.exec(
                        select(ChatMessage).where(
                            ChatMessage.user_id == user_id,
                            ChatMessage.session_id == session_id,
                            ChatMessage.module == module,
                            ChatMessage.created_at < cutoff,
                        )
                    )
                ).all()
            )
            for msg in expired_msgs:
                await session.delete(msg)
            if expired_msgs:
                await session.commit()
            return len(expired_msgs)

    async def clear_session_messages(self, user_id: int, session_id: str, module: str) -> int:  # 清空会话所有消息
        async with AsyncSession(self.engine) as session:
            messages = list(
                (
                    await session.exec(
                        select(ChatMessage).where(
                            ChatMessage.user_id == user_id,
                            ChatMessage.session_id == session_id,
                            ChatMessage.module == module,
                        )
                    )
                ).all()
            )
            deleted = len(messages)
            for msg in messages:
                await session.delete(msg)
            if deleted:
                await session.commit()
            return deleted

    async def should_summarize(self, user_id: int, session_id: str, module: str, threshold: int = MEMORY_COMPRESSION_TOKEN_THRESHOLD) -> bool:  # 判断是否需要压缩摘要
        return await self.get_message_token_count(user_id, session_id, module) >= threshold

    async def accumulate_session_tokens(self, user_id: int, session_id: str, module: str, content: str) -> tuple[int, int]:  # 累加会话token计数器
        token_delta = estimate_token_count(content)
        async with AsyncSession(self.engine) as session:
            chat_session = await self._get_owned_session(session, user_id, session_id, module)
            if not chat_session:
                chat_session = ChatSession(id=session_id, user_id=user_id, module=module, title="新对话")
            memory_token_count = max(0, chat_session.memory_token_count + token_delta)
            profile_token_count = max(0, chat_session.profile_token_count + token_delta)
            chat_session.memory_token_count = memory_token_count
            chat_session.profile_token_count = profile_token_count
            chat_session.updated_at = now()
            session.add(chat_session)
            await session.commit()
            return memory_token_count, profile_token_count

    async def get_session_token_counters(self, user_id: int, session_id: str, module: str) -> tuple[int, int]:  # 获取会话的token计数器值
        async with AsyncSession(self.engine) as session:
            chat_session = await self._get_owned_session(session, user_id, session_id, module)
            if not chat_session:
                return 0, 0
            return chat_session.memory_token_count, chat_session.profile_token_count

    async def should_trigger_memory_extraction(self, user_id: int, session_id: str, module: str, threshold: int = MEMORY_EXTRACTION_TOKEN_THRESHOLD) -> bool:  # 判断是否触发事实提取
        memory_tokens, _ = await self.get_session_token_counters(user_id, session_id, module)
        return memory_tokens >= threshold

    async def reset_memory_extraction_counter(self, user_id: int, session_id: str, module: str) -> None:  # 重置事实提取计数器
        async with AsyncSession(self.engine) as session:
            chat_session = await self._get_owned_session(session, user_id, session_id, module)
            if not chat_session:
                return
            chat_session.memory_token_count = 0
            session.add(chat_session)
            await session.commit()

    async def reset_profile_update_counter(self, user_id: int, session_id: str, module: str) -> None:  # 重置画像更新计数器
        async with AsyncSession(self.engine) as session:
            chat_session = await self._get_owned_session(session, user_id, session_id, module)
            if not chat_session:
                return
            chat_session.profile_token_count = 0
            session.add(chat_session)
            await session.commit()

    async def get_long_term_memories(self, user_id: int, module: str | None = None, limit: int = 10, only_unexpired: bool = True) -> list[UserMemory]:  # 获取用户的长期记忆列表
        async with AsyncSession(self.engine) as session:
            stmt = select(UserMemory).where(UserMemory.user_id == user_id)
            if module is not None:
                stmt = stmt.where(UserMemory.module == module)
            if only_unexpired:
                _now = now()
                stmt = stmt.where(or_(UserMemory.expires_at == None, UserMemory.expires_at > _now))  # noqa: E711
            stmt = stmt.order_by(UserMemory.created_at.desc()).limit(limit)
            return list((await session.exec(stmt)).all())

    async def get_long_term_memory_by_id(self, memory_id: int, *, user_id: int | None = None, module: str | None = None) -> UserMemory | None:  # 根据ID获取单条长期记忆
        async with AsyncSession(self.engine) as session:
            memory = await session.get(UserMemory, memory_id)
            if memory is None:
                return None
            if user_id is not None and memory.user_id != user_id:
                return None
            if module is not None and memory.module != module:
                return None
            return memory

    async def save_user_fact(  # 保存用户事实（支持去重和合并）
        self,
        user_id: int,
        content: str,
        memory_type: str,
        session_id: str | None = None,
        expires_at=None,
        module: str = "mentor",
    ) -> UserMemory:
        normalized_type = (memory_type or MEMORY_TYPE_FACT).strip().lower()
        if normalized_type not in FACT_AGENT_MEMORY_TYPES:
            normalized_type = MEMORY_TYPE_FACT
        cleaned_content = (content or "").strip()
        normalized_content = normalize_text(cleaned_content)
        if not normalized_content:
            raise ValueError("记忆内容不能为空")

        async with AsyncSession(self.engine) as session:
            _now = now()
            exact_stmt = (
                select(UserMemory)
                .where(
                    UserMemory.user_id == user_id,
                    UserMemory.module == module,
                    UserMemory.source == "fact_agent",
                    UserMemory.memory_type == normalized_type,
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
                    duplicate.importance = bump_importance(
                        duplicate.importance,
                        source=duplicate.source,
                        evidence_count=duplicate.evidence_count,
                        match_score=1.0,
                    )
                    session.add(duplicate)
                    await session.commit()
                    await session.refresh(duplicate)
                    return duplicate

            ranked_candidates = rank_merge_candidates(normalized_type, cleaned_content, candidates)
            if ranked_candidates:
                best_match = ranked_candidates[0]
                candidate = best_match.candidate
                candidate.content = choose_more_informative_content(candidate.content, cleaned_content)
                candidate.evidence_count = max(1, candidate.evidence_count) + 1
                candidate.last_seen_at = _now
                candidate.session_id = session_id or candidate.session_id
                if expires_at:
                    candidate.expires_at = expires_at
                candidate.importance = bump_importance(
                    candidate.importance,
                    source=candidate.source,
                    evidence_count=candidate.evidence_count,
                    match_score=best_match.match_score,
                )
                session.add(candidate)
                await session.commit()
                await session.refresh(candidate)
                return candidate

            memory = UserMemory(
                user_id=user_id,
                session_id=session_id or "",
                module=module,
                content=cleaned_content,
                memory_type=normalized_type,
                source="fact_agent",
                expires_at=expires_at,
                evidence_count=1,
                last_seen_at=_now,
                importance=initial_fact_importance(normalized_type, source="fact_agent"),
            )
            session.add(memory)
            await session.commit()
            await session.refresh(memory)
            return memory

    async def get_user_context_memories(  # 获取用户上下文记忆（按类型分组，支持去重和排序）
        self,
        user_id: int,
        memory_types: Iterable[str] | None = None,
        per_type_limits: dict[str, int] | None = None,
        only_unexpired: bool = True,
        source: str | None = "fact_agent",
        module: str | None = None,
    ) -> dict[str, list[UserMemory]]:
        target_types = list(memory_types) if memory_types else list(DEFAULT_MEMORY_TYPE_LIMITS.keys())
        limits = dict(DEFAULT_MEMORY_TYPE_LIMITS)
        if per_type_limits:
            limits.update(per_type_limits)

        async with AsyncSession(self.engine) as session:
            _now = now()
            stmt = select(UserMemory).where(UserMemory.user_id == user_id)
            if source is not None:
                stmt = stmt.where(UserMemory.source == source)
            if module is not None:
                stmt = stmt.where(UserMemory.module == module)
            if target_types:
                stmt = stmt.where(UserMemory.memory_type.in_(target_types))
            if only_unexpired:
                stmt = stmt.where(or_(UserMemory.expires_at == None, UserMemory.expires_at > _now))  # noqa: E711
            stmt = stmt.order_by(UserMemory.last_seen_at.desc(), UserMemory.created_at.desc())
            memories = list((await session.exec(stmt)).all())

        grouped: dict[str, list[UserMemory]] = defaultdict(list)
        seen_by_type: dict[str, set[str]] = defaultdict(set)
        for item in memories:
            m_type = item.memory_type or MEMORY_TYPE_FACT
            if m_type not in target_types:
                continue
            normalized = normalize_text(item.content)
            if not normalized or normalized in seen_by_type[m_type]:
                continue
            seen_by_type[m_type].add(normalized)
            grouped[m_type].append(item)

        for m_type, items in grouped.items():
            items.sort(key=rank_context_memory, reverse=True)
            grouped[m_type] = items[: max(0, limits.get(m_type, 2))]

        return {m_type: grouped.get(m_type, []) for m_type in target_types}

    async def save_long_term_memory(  # 直接保存长期记忆（无合并逻辑）
        self,
        user_id: int,
        session_id: str,
        content: str,
        memory_type: str,
        dimension: str | None = None,
        importance: float = 0.5,
        source: str = "conversation",
        source_message_count: int = 0,
        module: str = "mentor",
    ) -> UserMemory:
        async with AsyncSession(self.engine) as session:
            memory = UserMemory(
                user_id=user_id,
                session_id=session_id,
                module=module,
                content=content,
                memory_type=memory_type,
                dimension=dimension,
                importance=clamp_importance(importance),
                source=source,
                source_message_count=source_message_count,
                evidence_count=1,
                last_seen_at=now(),
            )
            session.add(memory)
            await session.commit()
            await session.refresh(memory)
            return memory

    async def update_long_term_memory(  # 更新长期记忆字段
        self,
        memory_id: int,
        *,
        user_id: int | None = None,
        module: str | None = None,
        content: str | None = None,
        memory_type: str | None = None,
        dimension: str | None = None,
        importance: float | None = None,
        expires_at=None,
        source: str | None = None,
    ) -> UserMemory | None:
        async with AsyncSession(self.engine) as session:
            memory = await session.get(UserMemory, memory_id)
            if memory is None:
                return None
            if user_id is not None and memory.user_id != user_id:
                return None
            if module is not None and memory.module != module:
                return None
            if content is not None:
                cleaned_content = content.strip()
                if not normalize_text(cleaned_content):
                    raise ValueError("记忆内容不能为空")
                memory.content = cleaned_content
            if memory_type is not None:
                normalized_type = memory_type.strip().lower()
                if normalized_type not in FACT_AGENT_MEMORY_TYPES:
                    normalized_type = MEMORY_TYPE_FACT
                memory.memory_type = normalized_type
            if dimension is not None:
                memory.dimension = dimension
            if importance is not None:
                memory.importance = clamp_importance(importance)
            if source is not None:
                memory.source = source
            if expires_at is not None:
                memory.expires_at = expires_at
            memory.last_seen_at = now()
            session.add(memory)
            await session.commit()
            await session.refresh(memory)
            return memory

    async def delete_long_term_memory(self, memory_id: int, *, user_id: int | None = None, module: str | None = None) -> bool:  # 删除长期记忆
        async with AsyncSession(self.engine) as session:
            memory = await session.get(UserMemory, memory_id)
            if memory is None:
                return False
            if user_id is not None and memory.user_id != user_id:
                return False
            if module is not None and memory.module != module:
                return False
            await session.delete(memory)
            await session.commit()
            return True

    async def summarize_and_compress(self, user_id: int, session_id: str, module: str, threshold: int = MEMORY_COMPRESSION_TOKEN_THRESHOLD, keep_recent: int = 10) -> None:  # 压缩旧消息为摘要并存储到长期记忆
        if not await self.should_summarize(user_id, session_id, module, threshold):
            return
        recent_msgs = await self.get_recent_messages(user_id, session_id, module)
        if not recent_msgs:
            return
        chat_text = "\n".join(
            f"[{m.created_at.strftime('%m-%d %H:%M')}] {m.role}: {m.content}"
            for m in recent_msgs[:-keep_recent]
        )
        if not chat_text.strip():
            return

        from langchain_core.prompts import ChatPromptTemplate

        summarize_prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个记忆压缩引擎。请将以下对话记录提炼为若干条关键知识点和结论。\n"
                "每条用一行表示，格式：`类别|内容`，类别包括 knowledge/error/behavior/interest/question/answer。\n"
                "只输出有价值的条目，忽略闲聊。"
            )),
            ("human", "{chat_text}"),
        ])
        llm = get_llm(temperature=0.1)
        result = await llm.ainvoke(summarize_prompt.invoke({"chat_text": chat_text}))
        summarized_ids = [m.id for m in recent_msgs[:-keep_recent]]
        await self.save_long_term_memory(
            user_id=user_id,
            session_id=session_id,
            content=result.content,
            memory_type=MEMORY_TYPE_SUMMARY,
            source=module,
            source_message_count=len(summarized_ids),
            module=module,
        )
        await self.delete_old_messages(user_id, session_id, module, keep_recent)


memory_store = MemoryStore()  # 模块级单例
