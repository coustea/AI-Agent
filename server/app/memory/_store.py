from __future__ import annotations


import asyncio
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Iterable

from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infra.database import engine
from app.infra.llm import get_llm_manager
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
from app.shared.json_utils import parse_first_json_object

logger = get_logger(__name__)
llm_manager = get_llm_manager()

SHORT_TERM_MESSAGE_EXPIRE_DAYS = 7  # 短期记忆消息默认保留天数（用于最近消息查询/清理过期消息的截止时间计算）
MEMORY_COMPRESSION_TOKEN_THRESHOLD = 150  # 触发"对话摘要压缩"的token阈值（达到阈值后可将旧消息压缩为长期摘要）
MEMORY_EXTRACTION_TOKEN_THRESHOLD = 80  # 触发"事实提取"流程的token阈值（基于会话累积计数器判断是否需要抽取事实）
PROFILE_UPDATE_TOKEN_THRESHOLD = 120  # 触发"画像更新"流程的token阈值（基于会话累积计数器判断是否需要更新画像）

DEFAULT_MEMORY_TYPE_LIMITS: dict[str, int] = {  # 获取上下文记忆时，各 memory_type 的默认返回上限（用于控制提示词注入的长度）
    MEMORY_TYPE_PREFERENCE: 3,
    MEMORY_TYPE_GOAL: 2,
    MEMORY_TYPE_WEAKNESS: 3,
    MEMORY_TYPE_FACT: 3,
    MEMORY_TYPE_BACKGROUND: 2,
}

_TERM_PATTERN = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]+", re.IGNORECASE)  # 轻量分词正则：将英文/数字连串与中文连续片段拆成"术语块"用于重叠度计算
_SOURCE_WEIGHTS: dict[str, float] = {"fact_agent": 1.0, "conversation": 0.94}  # 记忆来源权重：用于在相同内容下微调重要性/排序（更信任 fact_agent）
_INITIAL_IMPORTANCE_BY_TYPE: dict[str, float] = {  # 新写入记忆的类型基准重要性（后续会结合来源权重与证据次数逐步抬升）
    "preference": 0.66,
    "goal": 0.7,
    "weakness": 0.62,
    "fact": 0.58,
    "background": 0.54,
}
_MIN_OVERLAP_BY_TYPE: dict[str, float] = {  # 判定"内容足够相似可合并"的最小重叠阈值（不同类型容忍度不同）
    "preference": 0.4,
    "goal": 0.4,
    "weakness": 0.4,
    "fact": 0.45,
    "background": 0.45,
}


class SessionTitleOutput(BaseModel):
    """会话标题结构化输出模型。"""
    title: str = Field(description="会话标题，不超过15个字")


def _normalize_session_title(title: Any, fallback: str = "新对话") -> str:
    text = str(title or "").strip()
    if not text:
        return fallback
    return text[:15] if len(text) > 15 else text


def _should_fallback_session_title_generation(exc: Exception) -> bool:
    error_text = str(exc)
    return (
        "response_format type is unavailable" in error_text
        or "does not support this tool_choice" in error_text
    )


def normalize_text(content: str) -> str:
    # 规范化文本：去首尾空白、统一小写、合并多余空白（用于去重/重叠度/包含关系判断）
    return " ".join((content or "").strip().lower().split())


def now() -> datetime:
    # 获取当前本地时间（统一出口，便于测试/替换）
    return datetime.now()


def message_expire_cutoff(days: int = SHORT_TERM_MESSAGE_EXPIRE_DAYS) -> datetime:
    # 计算短期消息的"仍然有效"截止时间点（days<=0 时按 0 处理，避免出现未来时间）
    return now() - timedelta(days=max(days, 0))


def estimate_token_count(text: str) -> int:
    # 粗略估算文本 token 数（启发式，仅用于阈值/计数器，不用于计费或严格 tokenization）
    stripped = (text or "").strip()
    if not stripped:
        return 0
    # 仅启发式估算：这里的 token 计数用于触发阈值/累积计数器，精度不要求与真实分词器一致（不要用于计费或精确配额）。
    return max(max(1, len(stripped) // 4), len(stripped.split()))


@dataclass(frozen=True, slots=True)
class MergeDecision:
    # 记忆合并决策结构：candidate 为候选记忆对象；match_score 为综合匹配分；relation 为关系类型标签
    candidate: Any
    match_score: float
    relation: str


def clamp_importance(value: float | None, *, default: float = 0.5) -> float:
    # 将 importance 夹紧到 [0,1]（None 时回退到默认值，避免数据库/上游异常值污染排序）
    if value is None:
        return default
    return max(0.0, min(1.0, float(value)))


def source_weight(source: str | None) -> float:
    # 根据 source 获取权重系数（未知/缺失来源使用保守默认值，避免把未知来源抬得过高或过低）
    if not source:
        return 1.0
    return _SOURCE_WEIGHTS.get(source.strip().lower(), 0.96)


def initial_fact_importance(memory_type: str, source: str | None = "fact_agent") -> float:
    # 计算新写入记忆的初始重要性（按类型基准分 * 来源权重，再做 [0,1] 夹紧）
    base = _INITIAL_IMPORTANCE_BY_TYPE.get((memory_type or "").strip().lower(), 0.55)
    return clamp_importance(base * source_weight(source))


def _extract_terms(content: str | None) -> set[str]:
    # 从文本提取"术语集合"（用于 overlap/Jaccard，相比直接比字符串更稳健）
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
        # 对中文连续片段额外抽取相邻二字片段（bigram），提升"部分重叠/改写表达"场景下的召回与相似度稳定性。
        terms.update(chunk[index : index + 2] for index in range(len(chunk) - 1))  # 中文额外抽取二字片段（bigram）
    return terms


def content_information_score(content: str | None) -> float:
    # 计算内容信息量分数（用于合并时选择更"信息密度高/细节更多"的那段内容）
    normalized = normalize_text(content or "")
    if not normalized:
        return 0.0
    terms = _extract_terms(normalized)
    alpha_bonus = sum(1 for char in normalized if char.isalpha())
    digit_bonus = sum(1 for char in normalized if char.isdigit())
    return float(len(normalized) + len(terms) * 4 + alpha_bonus * 0.5 + digit_bonus)


def choose_more_informative_content(existing_content: str | None, new_content: str | None) -> str:
    # 在两段内容中选择更信息丰富的一段（用于合并后更新 candidate.content）
    existing = existing_content or ""
    incoming = new_content or ""
    if content_information_score(incoming) > content_information_score(existing):
        return incoming
    return existing


def memory_overlap_score(new_text: str | None, existing_text: str | None) -> float:
    # 计算两段文本"术语集合"的 Jaccard 重叠度（用于判断是否足够相似）
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


def classify_merge_relation(memory_type: str, new_text: str | None, existing_text: str | None) -> tuple[str, float]:
    # 分类两条记忆关系：完全相同(exact)/包含(containment)/重叠(overlap)/无关(none)
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


def score_merge_candidate(memory_type: str, new_text: str | None, candidate: Any) -> MergeDecision | None:  # 为单个候选记忆计算合并匹配分（relation 为主，importance/证据/新鲜度仅作极弱的平局裁决）
    relation, relation_score = classify_merge_relation(memory_type, new_text, getattr(candidate, "content_markdown", None))
    if relation_score <= 0:
        return None

    candidate_importance = clamp_importance(getattr(candidate, "importance", None))
    evidence_count = max(1, int(getattr(candidate, "evidence_count", 1) or 1))
    last_seen_at = getattr(candidate, "last_seen_at", None) or getattr(candidate, "created_at", None)
    recency_score = last_seen_at.timestamp() if isinstance(last_seen_at, datetime) else 0.0
    # 新鲜度 recency_score 只是弱信号：这里用很大的缩放系数把 timestamp 压到极小量级，避免"时间新"凌驾于"内容相似"之上。
    # 平局裁决项刻意压得很小：确保 relation_score（相似/包含关系）主导合并行为，避免重要性/新鲜度"压过"内容相似度。
    tiebreak_score = candidate_importance * 0.05 + min(evidence_count, 10) * 0.03 + recency_score / 1_000_000_000_000
    return MergeDecision(candidate=candidate, match_score=relation_score + tiebreak_score, relation=relation)


def rank_merge_candidates(memory_type: str, new_text: str | None, candidates: Iterable[Any]) -> list[MergeDecision]:  # 对全部候选记忆打分并排序（返回从最可能合并到最不可能的顺序）
    ranked = [decision for candidate in candidates if (decision := score_merge_candidate(memory_type, new_text, candidate))]
    ranked.sort(
        key=lambda item: (
            item.match_score,
            clamp_importance(getattr(item.candidate, "importance", None)),
            max(1, int(getattr(item.candidate, "evidence_count", 1) or 1)),
            (getattr(item.candidate, "last_seen_at", None) or getattr(item.candidate, "created_at", None) or datetime.min),
            len(normalize_text(getattr(item.candidate, "content_markdown", None) or "")),
        ),
        reverse=True,
    )
    return ranked


def bump_importance(  # 合并/重复命中时提升记忆 importance（综合来源权重、证据次数、匹配分，并做 [0,1] 夹紧）
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


def rank_context_memory(memory: Any) -> tuple[float, int, datetime]:  # 计算记忆用于上下文注入时的排序键（质量分、证据数、最近出现时间）
    importance = clamp_importance(getattr(memory, "importance", None))
    evidence_count = max(1, int(getattr(memory, "evidence_count", 1) or 1))
    quality = importance * source_weight(getattr(memory, "source", None)) + min(max(evidence_count - 1, 0), 6) * 0.06
    last_seen_at = getattr(memory, "last_seen_at", None) or getattr(memory, "created_at", None) or datetime.min
    return quality, evidence_count, last_seen_at


class MemoryStore:  # 记忆存储核心类：封装会话/短期消息/长期记忆的 CRUD 以及触发阈值、合并去重与摘要压缩
    def __init__(self) -> None:
        self.engine = engine

    async def _get_owned_session(  # 校验会话是否属于指定 user_id（可选 module 约束），用于写入前的权限与归属验证
        self,
        session: AsyncSession,
        user_id: int,
        session_id: str,
        module: str | None = None,
    ) -> ChatSession | None:
        stmt = select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)  # 通过 id+user_id 双条件查询，避免越权访问他人会话
        if module is not None:
            stmt = stmt.where(ChatSession.module == module)
        result = await session.exec(stmt)
        return result.first()

    async def _update_session_title(self, session: AsyncSession, chat_session: ChatSession, title: str) -> None:  # 更新会话标题（内部方法，用于标题生成后更新）
        chat_session.title = title[:100] if len(title) > 100 else title  # 截断到 100 字符上限
        session.add(chat_session)
        await session.commit()

    async def _generate_session_title(self, user_message: str) -> str:  # 用轻量级 LLM 从用户首条消息提取会话标题
        from langchain_core.prompts import ChatPromptTemplate
        model_kwargs = {"temperature": 0.1, "max_tokens": 80}
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个标题生成助手。请根据用户的第一条消息，生成一个简短的会话标题。标题应该简洁明了，能够概括对话主题。"),
            ("human", "{user_message}"),
        ])
        messages = prompt.invoke({"user_message": user_message[:500]})
        try:
            llm = llm_manager.with_structured_output(
                "deepseek",
                SessionTitleOutput,
                model_kwargs=model_kwargs,
            )
            result = await llm_manager.ainvoke_runnable(
                llm,
                messages,
                model_type="deepseek",
            )
            title = _normalize_session_title(result.title)
            logger.info("[MemoryStore] title.llm_response title=%r", title)
            return title
        except Exception as exc:
            if not _should_fallback_session_title_generation(exc):
                logger.exception("[MemoryStore] title_generation.failed")
                raise

            logger.warning("[MemoryStore] title structured_output 不可用，回退到 JSON 文本生成: %s", exc)
            fallback_messages = list(messages.to_messages()) + [
                (
                    "human",
                    "请直接输出一个合法 JSON 对象，不要使用 Markdown 代码块，不要添加解释文字。"
                    '格式必须是：{"title":"会话标题"}，标题不超过15个字。',
                )
            ]
            raw_response = await llm_manager.ainvoke(
                "deepseek",
                fallback_messages,
                model_kwargs=model_kwargs,
            )
            raw_content = getattr(raw_response, "content", raw_response)
            parsed = parse_first_json_object(str(raw_content))
            title = _normalize_session_title(parsed.get("title"))
            logger.info("[MemoryStore] title.llm_response fallback title=%r", title)
            return title

    async def _generate_and_update_title_background(self, session_id: str, user_message: str) -> None:  # 后台任务：生成标题并更新数据库（不阻塞主流程）
        """后台异步生成标题并更新会话。此方法通过 asyncio.create_task 调用，不阻塞消息保存。"""
        try:
            new_title = await self._generate_session_title(user_message)
            async with AsyncSession(self.engine) as title_session:
                stmt = select(ChatSession).where(ChatSession.id == session_id)
                target_session = (await title_session.exec(stmt)).first()
                if target_session and target_session.title == "新对话":  # 再次检查避免并发冲突
                    await self._update_session_title(title_session, target_session, new_title)
                    logger.info("[MemoryStore] title.generated session=%s title=%s", session_id, new_title)
        except Exception:
            logger.exception("[MemoryStore] title_generation.update.failed session=%s", session_id)

    async def create_chat_session(self, user_id: int, module: str, title: str = "新对话") -> ChatSession:  # 创建新的聊天会话记录（写入 ChatSession 并返回持久化后的对象）
        async with AsyncSession(self.engine) as session:
            chat_session = ChatSession(user_id=user_id, module=module, title=title)
            session.add(chat_session)
            await session.commit()
            await session.refresh(chat_session)
            return chat_session

    async def get_chat_session(self, session_id: str) -> ChatSession | None:  # 按 session_id 获取会话（不做 user/module 归属校验）
        async with AsyncSession(self.engine) as session:
            stmt = select(ChatSession).where(ChatSession.id == session_id)
            return (await session.exec(stmt)).first()

    async def get_user_chat_sessions(self, user_id: int, module: str | None = None, limit: int = 20) -> list[ChatSession]:  # 获取用户会话列表（默认排除已归档，按 updated_at 倒序）
        async with AsyncSession(self.engine) as session:
            stmt = select(ChatSession).where(ChatSession.user_id == user_id, ChatSession.is_archived == False)  # noqa: E712
            if module:
                stmt = stmt.where(ChatSession.module == module)
            stmt = stmt.order_by(ChatSession.updated_at.desc()).limit(limit)
            return list((await session.exec(stmt)).all())

    async def archive_chat_session(self, session_id: str, user_id: int) -> bool:  # 归档会话（软删除）：仅标记 is_archived，不物理删除历史消息
        async with AsyncSession(self.engine) as session:
            stmt = select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
            chat_session = (await session.exec(stmt)).first()
            if not chat_session:
                return False
            chat_session.is_archived = True
            session.add(chat_session)
            await session.commit()
            return True

    async def save_message(  # 保存单条聊天消息到短期存储（同时更新/创建会话元信息，并返回该会话当前消息总数）
        self,
        user_id: int,
        session_id: str,
        module: str,
        role: str,
        content: str,
        attachments: str | None = None,
        tool_calls: str | None = None,
        diagram: dict | None = None,
    ) -> int:
        should_generate_title = False  # 标记是否需要生成标题（首条用户消息且标题为"新对话"）
        async with AsyncSession(self.engine) as session:
            session_stmt = select(ChatSession).where(ChatSession.id == session_id)
            chat_session = (await session.exec(session_stmt)).first()
            if chat_session:
                if chat_session.user_id != user_id or chat_session.module != module:
                    raise PermissionError("会话不属于当前用户或模块，禁止写入")
                chat_session.updated_at = now()
                # 检查是否是首条用户消息且标题仍为默认值
                if role == "user" and chat_session.title == "新对话":
                    existing_count = await self.get_message_count(user_id, session_id, module)
                    if existing_count == 0:  # 这是第一条用户消息
                        should_generate_title = True
            else:
                chat_session = ChatSession(id=session_id, user_id=user_id, module=module, title="新对话")
                if role == "user":  # 新会话的首条用户消息
                    should_generate_title = True
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
                    diagram=diagram,
                )
            )
            # 单次 commit 同时持久化"会话元数据更新"和"消息新增"，尽量保证写入原子性，避免出现只写消息或只改会话的中间态。
            await session.commit()

        # 使用 asyncio.create_task 在后台异步生成标题，不阻塞主流程
        if should_generate_title:
            try:
                asyncio.create_task(self._generate_and_update_title_background(session_id, content))
            except Exception:
                logger.exception("[MemoryStore] title_task.create.failed session=%s", session_id)

        return await self.get_message_count(user_id, session_id, module)

    async def get_recent_messages(  # 获取会话最近消息列表（可按过期策略过滤；limit 表示返回最后 N 条，但保持时间正序）
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
            # 这里用"count + offset"的两次查询实现取最后 N 条：在并发写入时可能有轻微错位，但对 UI 展示而言是最佳努力且可接受。
            total = (await session.exec(select(func.count()).where(*filters))).one()
            # 先按时间正序排序，再通过 offset 只取最后 N 条，确保返回列表顺序符合对话时间线展示。
            stmt = select(ChatMessage).where(*filters).order_by(ChatMessage.created_at.asc())
            if limit is not None and limit > 0 and total > limit:
                stmt = stmt.offset(total - limit)
            return list((await session.exec(stmt)).all())

    async def get_message_count(self, user_id: int, session_id: str, module: str) -> int:  # 获取会话消息总数（按 user/session/module 三元组计数）
        async with AsyncSession(self.engine) as session:
            stmt = select(func.count()).where(
                ChatMessage.user_id == user_id,
                ChatMessage.session_id == session_id,
                ChatMessage.module == module,
            )
            return (await session.exec(stmt)).one()

    async def get_message_token_count(  # 计算会话消息总 token 数（基于启发式估算，用于阈值判断与计数器）
        self,
        user_id: int,
        session_id: str,
        module: str,
        days: int = SHORT_TERM_MESSAGE_EXPIRE_DAYS,
        only_unexpired: bool = True,
    ) -> int:
        messages = await self.get_recent_messages(user_id, session_id, module, None, days, only_unexpired)
        return sum(estimate_token_count(getattr(msg, "content", "")) for msg in messages)

    async def delete_old_messages(self, user_id: int, session_id: str, module: str, keep_recent: int = 10) -> int:  # 删除旧消息，仅保留最近 keep_recent 条（用于摘要压缩后清理）
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
            # 用消息 id 作为删除边界：假设 id 随插入单调递增；这样能稳定保留"最近 N 条"对应的那一段消息。
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

    async def cleanup_expired_short_term_messages(  # 清理过期短期消息：删除 created_at 早于 cutoff 的记录并返回删除数量
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

    async def clear_session_messages(self, user_id: int, session_id: str, module: str) -> int:  # 清空会话所有消息（物理删除 ChatMessage，返回删除条数）
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

    async def should_summarize(self, user_id: int, session_id: str, module: str, threshold: int = MEMORY_COMPRESSION_TOKEN_THRESHOLD) -> bool:  # 判断是否需要做摘要压缩（会话 token 总量达到阈值则返回 True）
        return await self.get_message_token_count(user_id, session_id, module) >= threshold

    async def accumulate_session_tokens(self, user_id: int, session_id: str, module: str, content: str) -> tuple[int, int]:  # 累加会话 token 计数器（分别用于记忆提取与画像更新的触发阈值判断）
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

    async def get_session_token_counters(self, user_id: int, session_id: str, module: str) -> tuple[int, int]:  # 获取会话 token 计数器（memory_token_count, profile_token_count）
        async with AsyncSession(self.engine) as session:
            chat_session = await self._get_owned_session(session, user_id, session_id, module)
            if not chat_session:
                return 0, 0
            return chat_session.memory_token_count, chat_session.profile_token_count

    async def should_trigger_memory_extraction(self, user_id: int, session_id: str, module: str, threshold: int = MEMORY_EXTRACTION_TOKEN_THRESHOLD) -> bool:  # 判断是否应触发事实提取（基于 memory_token_count 与阈值比较）
        memory_tokens, _ = await self.get_session_token_counters(user_id, session_id, module)
        return memory_tokens >= threshold

    async def reset_memory_extraction_counter(self, user_id: int, session_id: str, module: str) -> None:  # 重置事实提取计数器（将 memory_token_count 清零）
        async with AsyncSession(self.engine) as session:
            chat_session = await self._get_owned_session(session, user_id, session_id, module)
            if not chat_session:
                return
            chat_session.memory_token_count = 0
            session.add(chat_session)
            await session.commit()

    async def reset_profile_update_counter(self, user_id: int, session_id: str, module: str) -> None:  # 重置画像更新计数器（将 profile_token_count 清零）
        async with AsyncSession(self.engine) as session:
            chat_session = await self._get_owned_session(session, user_id, session_id, module)
            if not chat_session:
                return
            chat_session.profile_token_count = 0
            session.add(chat_session)
            await session.commit()

    async def get_long_term_memories(self, user_id: int, module: str | None = None, limit: int = 10, only_unexpired: bool = True) -> list[UserMemory]:  # 获取用户长期记忆列表（可按 module 过滤，默认仅取未过期记录）
        async with AsyncSession(self.engine) as session:
            stmt = select(UserMemory).where(UserMemory.user_id == user_id)
            if module is not None:
                stmt = stmt.where(UserMemory.module == module)
            if only_unexpired:
                _now = now()
                stmt = stmt.where(or_(UserMemory.expires_at == None, UserMemory.expires_at > _now))  # noqa: E711
            stmt = stmt.order_by(UserMemory.created_at.desc()).limit(limit)
            return list((await session.exec(stmt)).all())

    async def get_long_term_memory_by_id(self, memory_id: int, *, user_id: int | None = None, module: str | None = None) -> UserMemory | None:  # 按 memory_id 获取单条长期记忆（可选 user/module 过滤用于权限约束）
        async with AsyncSession(self.engine) as session:
            memory = await session.get(UserMemory, memory_id)
            if memory is None:
                return None
            if user_id is not None and memory.user_id != user_id:
                return None
            if module is not None and memory.module != module:
                return None
            return memory

    async def save_user_fact(  # 写入"用户事实"长期记忆（对 fact_agent 来源做去重与近似合并，尽量避免重复条目）
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
            # 这里是"尽力而为"的合并：没有数据库层唯一约束/锁；并发写入时仍可能产生近似重复，但能覆盖大多数串行写入场景。
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
                if normalize_text(duplicate.content_markdown) == normalized_content:
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

            # 没有完全相同内容时，才按相似/包含/重叠关系挑选最优候选合并（并用更信息丰富的文本覆盖 content_markdown）。
            ranked_candidates = rank_merge_candidates(normalized_type, cleaned_content, candidates)
            if ranked_candidates:
                best_match = ranked_candidates[0]
                candidate = best_match.candidate
                candidate.content_markdown = choose_more_informative_content(candidate.content_markdown, cleaned_content)
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
                title=None,
                content_markdown=cleaned_content,
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

    async def get_user_context_memories(  # 获取用于上下文注入的用户记忆（按类型分组、去重、排序，并按每类上限截断）
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

        # 查询后再做分组/去重：把纯内存处理移到 DB session 之外，缩短事务窗口，减少长事务带来的并发与锁风险。
        grouped: dict[str, list[UserMemory]] = defaultdict(list)
        seen_by_type: dict[str, set[str]] = defaultdict(set)
        for item in memories:
            m_type = item.memory_type or MEMORY_TYPE_FACT
            if m_type not in target_types:
                continue
            normalized = normalize_text(item.content_markdown)
            if not normalized or normalized in seen_by_type[m_type]:
                continue
            seen_by_type[m_type].add(normalized)
            grouped[m_type].append(item)

        for m_type, items in grouped.items():
            items.sort(key=rank_context_memory, reverse=True)
            grouped[m_type] = items[: max(0, limits.get(m_type, 2))]

        return {m_type: grouped.get(m_type, []) for m_type in target_types}

    async def save_long_term_memory(  # 直接新增一条长期记忆（不做去重/合并；适用于摘要等"必然新增"的场景）
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
        title: str | None = None,
    ) -> UserMemory:
        async with AsyncSession(self.engine) as session:
            memory = UserMemory(
                user_id=user_id,
                session_id=session_id,
                module=module,
                title=title,
                content_markdown=content,
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

    async def update_long_term_memory(  # 更新长期记忆字段（带 user/module 约束；更新后会刷新 last_seen_at）
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
                memory.content_markdown = cleaned_content
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

    async def delete_long_term_memory(self, memory_id: int, *, user_id: int | None = None, module: str | None = None) -> bool:  # 删除长期记忆（带 user/module 约束；物理删除记录）
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

    async def summarize_and_compress(self, user_id: int, session_id: str, module: str, threshold: int = MEMORY_COMPRESSION_TOKEN_THRESHOLD, keep_recent: int = 10) -> None:  # 将旧消息压缩为摘要写入长期记忆，并清理已压缩的历史消息（保留最近 keep_recent 条）
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
        result = await llm_manager.ainvoke(
            "spark_x",
            summarize_prompt.invoke({"chat_text": chat_text}),
            model_kwargs={"temperature": 0.1},
        )
        summarized_ids = [m.id for m in recent_msgs[:-keep_recent]]
        # 先落库摘要再删旧消息：即使清理过程中途失败，也能保证摘要已保存，避免"删了但没存摘要"的数据丢失。
        await self.save_long_term_memory(
            user_id=user_id,
            session_id=session_id,
            content=result.content,
            memory_type=MEMORY_TYPE_SUMMARY,
            source=module,
            source_message_count=len(summarized_ids),
            module=module,
            title="对话摘要",
        )
        await self.delete_old_messages(user_id, session_id, module, keep_recent)


memory_store = MemoryStore()  # 模块级单例：作为全局共享入口使用（避免在各处重复构建 Store）
