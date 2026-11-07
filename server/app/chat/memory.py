"""Chat 记忆管线 —— 基于 learn-claude-code s06 上下文自动压缩 (Auto-compact) 与长期记忆 (LTM)。"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Final

from pydantic import BaseModel
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import (
    COMPRESS_KEEP_RECENT_MESSAGES,
    COMPRESS_MIN_MESSAGES,
    COMPRESS_MIN_TOKENS,
    LTM_MIN_CONFIDENCE,
    SUMMARY_CONTEXT_BLOCKS,
    UPDATE_MIN_MESSAGES,
    UPDATE_MIN_TOKENS,
)
from app.evaluation.event_types import CHAT_DIALOGUE, MODULE_CHAT
from app.evaluation.schemas import LearningEventCreate
from app.evaluation.service import EvaluationService
from app.infra.database import session_scope
from app.infra.llm import HumanMessage, LLM, SystemMessage, load_prompt
from app.infra.logging import get_logger
from app.infra.models import (
    ChatLongTermMemory,
    ChatMessage,
    ChatSession,
    ChatSessionSummaryBlock,
)

logger = get_logger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
_COMPRESSION_PROMPT = _PROMPTS_DIR / "compression.md"
_LTM_PROMPT = _PROMPTS_DIR / "ltm_update.md"

DEFAULT_SESSION_TITLE: Final[str] = "新对话"
TITLE_MAX_LENGTH: Final[int] = 100

LTM_CATEGORIES: Final[tuple[str, ...]] = (
    "learning_background",
    "long_term_goals",
    "learning_preferences",
    "stable_weaknesses",
    "interaction_rules",
    "effective_strategies",
    "corrections",
)

LTM_CATEGORY_NAMES: Final[dict[str, str]] = {
    "learning_background": "学习背景",
    "long_term_goals": "长期目标",
    "learning_preferences": "学习偏好",
    "stable_weaknesses": "稳定薄弱点",
    "interaction_rules": "交互规则",
    "effective_strategies": "有效辅导策略",
    "corrections": "用户纠正记录",
}

STABLE_SIGNAL_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"(总是|经常|一直|老是|反复).*(出错|不会|卡住|记不住|搞不清|混淆|薄弱|边界)"),
    re.compile(r"(以后|下次|后续).*(希望|想|请|先|多|少|给|讲|不要|必须|应该|保持|沿用|避免|记住)"),
    re.compile(r"(喜欢|不喜欢|更喜欢|偏好|习惯)"),
    re.compile(r"(在学|正在学|学过|准备|打算|想要).*(考研|提高|练习|项目)"),
    re.compile(r"(我是|我的|我在|我学|我读|我准备|我打算|我考|我参加).*(专业|年级|方向|课程|考试|证书|竞赛|实习|面试|项目)"),
)

NON_SIGNIFICANT_TEXTS: Final[frozenset[str]] = frozenset(
    {"谢谢", "好的", "收到", "明白了", "继续", "再来一道题", "ok", "OK"}
)


def now_utc() -> datetime:
    """返回当前 UTC 时间。"""
    return datetime.now(timezone.utc)


def extract_content_text(content: list[dict[str, Any]] | str | None) -> str:
    """从消息 content 结构中提取纯文本。"""
    if isinstance(content, list):
        return " ".join(
            str(p.get("text", ""))
            for p in content
            if isinstance(p, dict) and p.get("type") == "text"
        ).strip()
    return str(content or "").strip()


def estimate_token_count(text: str) -> int:
    """估算中英文混合文本的 token 数量。"""
    stripped = (text or "").strip()
    if not stripped:
        return 0
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(stripped))
    except Exception:
        pass
    chinese_chars = len(re.findall(r"[一-鿿]", stripped))
    non_chinese = re.sub(r"[一-鿿]", "", stripped)
    return int(chinese_chars * 1.5) + len(non_chinese.split())


def compact_text(text: str, *, limit: int = 3500) -> str:
    """按字符上限截断长文本并补省略号。"""
    value = str(text or "").strip()
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def has_stable_signal(text: str) -> bool:
    """检测文本是否包含值得写入长期记忆的稳定学习信号。"""
    normalized = " ".join((text or "").strip().split())
    if not normalized or normalized in NON_SIGNIFICANT_TEXTS:
        return False
    return any(pattern.search(normalized) for pattern in STABLE_SIGNAL_PATTERNS)


def make_default_memory_markdown() -> str:
    """生成包含 7 个标准二级标题的初始长期记忆 Markdown 模板。"""
    lines = ["# 长期记忆", "", "## 学习背景", "暂无学习背景信息。"]
    for key in LTM_CATEGORIES[1:]:
        lines.extend(["", f"## {LTM_CATEGORY_NAMES[key]}", "暂无信息。"])
    return "\n".join(lines)


def _strip_markdown_fence(text: str) -> str:
    """剥离首尾的 markdown 代码块围栏。"""
    s = text.strip()
    if s.startswith("```"):
        first_line_end = s.find("\n")
        if first_line_end != -1 and s.endswith("```"):
            s = s[first_line_end + 1 : -3].strip()
    return s


class MemoryUpdateOutput(BaseModel):
    """长期记忆增量更新的结构化输出模型。"""

    need_update: bool = False
    memory_markdown: str | None = None
    confidence: float = 0.75
    update_reason: str = ""


class ChatSessionCompressor:
    """会话滚动摘要压缩器 —— 将超出窗口的早期对话压缩为 ChatSessionSummaryBlock。"""

    def __init__(
        self,
        *,
        keep_recent: int = COMPRESS_KEEP_RECENT_MESSAGES,
        min_messages: int = COMPRESS_MIN_MESSAGES,
        min_tokens: int = COMPRESS_MIN_TOKENS,
    ) -> None:
        """初始化压缩器阈值与 LLM 客户端。"""
        self.keep_recent = keep_recent
        self.min_messages = min_messages
        self.min_tokens = min_tokens
        self.llm = LLM(temperature=0.7)

    async def needs_compression(self, *, db: AsyncSession, user_id: int, session_id: str) -> bool:
        """判断当前会话是否达到 token 或消息条数压缩阈值。"""
        chat_session = (await db.exec(select(ChatSession).where(ChatSession.id == session_id))).first()
        token_count = int(chat_session.summary_token_count or 0) if chat_session else 0
        if token_count >= self.min_tokens:
            return True

        latest_block = (
            await db.exec(
                select(ChatSessionSummaryBlock)
                .join(ChatSession, ChatSession.id == ChatSessionSummaryBlock.session_id)
                .where(
                    ChatSession.user_id == user_id,
                    ChatSessionSummaryBlock.session_id == session_id,
                )
                .order_by(ChatSessionSummaryBlock.block_index.desc())
                .limit(1)
            )
        ).first()
        last_summarized_id = int(latest_block.end_message_id or 0) if latest_block else 0

        count_result = (
            await db.exec(
                select(func.count())
                .select_from(ChatMessage)
                .join(ChatSession, ChatSession.id == ChatMessage.session_id)
                .where(
                    ChatSession.user_id == user_id,
                    ChatMessage.session_id == session_id,
                    ChatMessage.id > last_summarized_id,
                )
            )
        ).one()
        return int(count_result) >= self.min_messages

    async def maybe_compress(
        self,
        *,
        db: AsyncSession,
        user_id: int,
        session_id: str,
        force: bool = False,
        reason: str = "post_turn",
    ) -> ChatSessionSummaryBlock | None:
        """按阈值判断是否需要压缩，满足时生成并保存新的摘要块。"""
        should = force or await self.needs_compression(db=db, user_id=user_id, session_id=session_id)
        if not should:
            return None
        return await self._compress(db=db, user_id=user_id, session_id=session_id)

    async def _compress(
        self,
        *,
        db: AsyncSession,
        user_id: int,
        session_id: str,
    ) -> ChatSessionSummaryBlock | None:
        """提取未摘要的早期对话，调用 LLM 生成滚动摘要并更新水位。"""
        latest_block = (
            await db.exec(
                select(ChatSessionSummaryBlock)
                .join(ChatSession, ChatSession.id == ChatSessionSummaryBlock.session_id)
                .where(
                    ChatSession.user_id == user_id,
                    ChatSessionSummaryBlock.session_id == session_id,
                )
                .order_by(ChatSessionSummaryBlock.block_index.desc())
                .limit(1)
            )
        ).first()
        last_summarized_id = int(latest_block.end_message_id or 0) if latest_block else 0
        messages = list(
            (
                await db.exec(
                    select(ChatMessage)
                    .join(ChatSession, ChatSession.id == ChatMessage.session_id)
                    .where(
                        ChatSession.user_id == user_id,
                        ChatMessage.session_id == session_id,
                        ChatMessage.role.in_(["user", "assistant"]),
                        ChatMessage.id > last_summarized_id,
                    )
                    .order_by(ChatMessage.id.asc())
                )
            ).all()
        )
        dialogue = [msg for msg in messages if extract_content_text(msg.content)]
        if len(dialogue) <= self.keep_recent:
            return None

        target = dialogue[: -self.keep_recent] if self.keep_recent > 0 else dialogue
        if not target:
            return None

        chat_text = "\n".join(
            f"[{msg.created_at:%m-%d %H:%M}] {msg.role}: {extract_content_text(msg.content)[:500]}"
            for msg in target
        )
        prompt = load_prompt(_COMPRESSION_PROMPT, dialogue_text=chat_text[:5000])
        if latest_block and latest_block.summary_markdown:
            prompt += f"\n\n## 上一阶段滚动状态摘要\n{latest_block.summary_markdown}"

        resp = await self.llm.text(
            [
                SystemMessage(content=prompt),
                HumanMessage(content="请根据以上对话记录输出会话摘要 Markdown。"),
            ]
        )
        summary_markdown = _strip_markdown_fence(str(getattr(resp, "content", resp) or "").strip())
        if not summary_markdown:
            raise RuntimeError("LLM 生成的会话摘要为空")

        next_block_index = (latest_block.block_index if latest_block else 0) + 1
        summary_block = ChatSessionSummaryBlock(
            session_id=session_id,
            block_index=next_block_index,
            summary_markdown=summary_markdown,
            start_message_id=target[0].id,
            end_message_id=target[-1].id,
        )
        db.add(summary_block)
        await db.flush()

        chat_session = (await db.exec(select(ChatSession).where(ChatSession.id == session_id))).first()
        if chat_session:
            chat_session.summary_token_count = 0
            db.add(chat_session)
        return summary_block


class ChatLongTermMemoryService:
    """长期记忆提取与增量更新服务。"""

    def __init__(
        self,
        *,
        min_confidence: float = LTM_MIN_CONFIDENCE,
        cooldown_minutes: int = 30,
    ) -> None:
        """初始化长期记忆置信度阈值、冷却间隔与 LLM 客户端。"""
        self.min_confidence = min_confidence
        self.cooldown_seconds = cooldown_minutes * 60
        self.llm = LLM(temperature=0.1)

    def should_consider_update(self, *, user_message: str, assistant_reply: str) -> bool:
        """判断当轮对话是否包含触发长期记忆更新的稳定信号。"""
        if has_stable_signal(user_message):
            return True
        return has_stable_signal(assistant_reply) and any(
            kw in assistant_reply for kw in ("以后", "下次", "记住", "偏好", "纠正")
        )

    async def maybe_update(
        self,
        *,
        db: AsyncSession,
        user_id: int,
        session_id: str,
        user_message: str,
        assistant_reply: str,
        new_dialogue: str = "",
        turn_count: int = 0,
        signal_detected: bool | None = None,
    ) -> dict[str, bool]:
        """按信号或周期阈值判断并更新用户的长期记忆 Markdown。"""
        detected = (
            self.should_consider_update(user_message=user_message, assistant_reply=assistant_reply)
            if signal_detected is None
            else signal_detected
        )
        periodic_trigger = bool((new_dialogue or "").strip()) and turn_count > 0
        if not detected and not periodic_trigger:
            return {"updated": False, "analyzed": False}
        if not new_dialogue or not new_dialogue.strip():
            return {"updated": False, "analyzed": False}

        existing = (
            await db.exec(select(ChatLongTermMemory).where(ChatLongTermMemory.user_id == user_id))
        ).first()
        if existing:
            old_memory = existing
        else:
            old_memory = ChatLongTermMemory(
                user_id=user_id,
                memory_markdown=make_default_memory_markdown(),
            )
            db.add(old_memory)
            await db.flush()

        if (
            not detected
            and periodic_trigger
            and old_memory.updated_at
            and (now_utc() - old_memory.updated_at).total_seconds() < self.cooldown_seconds
        ):
            return {"updated": False, "analyzed": False}

        latest_summary_block = (
            await db.exec(
                select(ChatSessionSummaryBlock)
                .join(ChatSession, ChatSession.id == ChatSessionSummaryBlock.session_id)
                .where(
                    ChatSession.user_id == user_id,
                    ChatSessionSummaryBlock.session_id == session_id,
                )
                .order_by(ChatSessionSummaryBlock.created_at.desc())
                .limit(1)
            )
        ).first()

        prompt = load_prompt(
            _LTM_PROMPT,
            new_dialogue=(new_dialogue or "").strip()[:4000],
            user_message=user_message[:1000],
            assistant_reply=assistant_reply[:1000],
            session_summary=latest_summary_block.summary_markdown if latest_summary_block else "暂无会话概要。",
            old_memory=old_memory.memory_markdown if old_memory else "暂无长期记忆。",
        )
        resp = await self.llm.json(MemoryUpdateOutput, prompt)
        if not resp.need_update or not resp.memory_markdown:
            return {"updated": False, "analyzed": True}
        if getattr(resp, "confidence", self.min_confidence) < self.min_confidence:
            return {"updated": False, "analyzed": True}

        old_memory.memory_markdown = resp.memory_markdown
        old_memory.updated_at = now_utc()
        db.add(old_memory)
        return {"updated": True, "analyzed": True}


async def get_session_summary_context(user_id: int, session_id: str) -> str:
    """获取最近 N 个会话摘要块并拼接为上下文文本。"""
    async with session_scope() as db:
        stmt = (
            select(ChatSessionSummaryBlock)
            .join(ChatSession, ChatSession.id == ChatSessionSummaryBlock.session_id)
            .where(
                ChatSession.user_id == user_id,
                ChatSessionSummaryBlock.session_id == session_id,
            )
            .order_by(ChatSessionSummaryBlock.created_at.desc())
            .limit(SUMMARY_CONTEXT_BLOCKS)
        )
        blocks = list((await db.exec(stmt)).all())
    if not blocks:
        return ""
    return "\n\n---\n\n".join(
        block.summary_markdown for block in reversed(blocks) if block.summary_markdown
    )


async def get_memory_markdown(user_id: int, category: str | None = None) -> str:
    """读取用户长期记忆 Markdown，可按分类名称截取对应小节。"""
    async with session_scope() as db:
        record = (
            await db.exec(select(ChatLongTermMemory).where(ChatLongTermMemory.user_id == user_id))
        ).first()
    markdown = str(getattr(record, "memory_markdown", "") or "").strip()
    if not markdown:
        return "暂无长期学习记忆。"
    category_value = str(category or "").strip()
    if not category_value:
        return markdown
    heading = LTM_CATEGORY_NAMES.get(category_value)
    if not heading:
        return markdown
    match = re.search(
        rf"(^|\n)##\s+{re.escape(heading)}\s*\n(?P<body>.*?)(?=\n##\s+|\Z)",
        markdown,
        flags=re.S,
    )
    if not match:
        return f"## {heading}\n暂无信息。"
    return f"## {heading}\n{match.group('body').strip()}"


def clean_session_title(value: str) -> str:
    """清理会话标题中的换行、引号与首尾标点并截断长度。"""
    title = re.sub(r"[\r\n\t]+", " ", value or "").strip()
    title = title.strip("`'\"“”‘’《》[]（）()，。！？!?：:；;、 ")
    title = re.sub(r"\s+", " ", title)
    return title[:TITLE_MAX_LENGTH]


async def generate_session_title(user_id: int, session_id: str, first_message: str) -> bool:
    """根据首条用户消息调用 LLM 生成简短中文会话标题。"""
    fallback = clean_session_title(first_message) or DEFAULT_SESSION_TITLE
    title = fallback
    try:
        llm = LLM(temperature=0.7, max_tokens=32)
        resp = await llm.text(
            [
                SystemMessage(content="你是会话标题生成器。只输出一个简短中文标题，不要标点、引号或解释。"),
                HumanMessage(content=f"为这段学习辅导对话生成标题，最多12个中文字符：\n{first_message}"),
            ],
            max_tokens=32,
        )
        title = clean_session_title(str(getattr(resp, "content", resp) or "")) or fallback
    except Exception as exc:
        logger.warning("[Memory] 生成标题失败: user_id=%s session_id=%s err=%s", user_id, session_id, exc)

    async with session_scope() as db:
        chat_session = (
            await db.exec(
                select(ChatSession).where(
                    ChatSession.id == session_id,
                    ChatSession.user_id == user_id,
                )
            )
        ).first()
        if not chat_session:
            return False
        chat_session.title = title[:TITLE_MAX_LENGTH]
        chat_session.updated_at = now_utc()
        db.add(chat_session)
    return True


async def run_post_turn_memory_jobs(
    *,
    user_id: int,
    session_id: str,
    user_message: str,
    assistant_reply: str,
) -> None:
    """对话轮结束后的后台记忆管线：按阈值并行调度会话压缩与长期记忆更新。"""
    compressor = ChatSessionCompressor()
    ltm_service = ChatLongTermMemoryService()
    ltm_signal = ltm_service.should_consider_update(
        user_message=user_message,
        assistant_reply=assistant_reply,
    )

    try:
        async with session_scope() as db:
            chat_session = (
                await db.exec(
                    select(ChatSession).where(
                        ChatSession.id == session_id,
                        ChatSession.user_id == user_id,
                    )
                )
            ).first()
            if not chat_session:
                return
            ltm_token = int(chat_session.ltm_token_count or 0)
            ltm_msg = int(chat_session.ltm_message_count or 0)
            should_ltm = (ltm_signal or ltm_token >= UPDATE_MIN_TOKENS or ltm_msg >= UPDATE_MIN_MESSAGES) and ltm_msg > 0
            should_compress = await compressor.needs_compression(
                db=db,
                user_id=user_id,
                session_id=session_id,
            )

        async def _do_compress() -> None:
            """在独立会话中执行摘要压缩。"""
            async with session_scope() as db:
                await compressor.maybe_compress(db=db, user_id=user_id, session_id=session_id)

        async def _do_ltm() -> None:
            """在独立会话中提取新增对话并更新长期记忆。"""
            async with session_scope() as db:
                cs = (
                    await db.exec(
                        select(ChatSession).where(
                            ChatSession.id == session_id,
                            ChatSession.user_id == user_id,
                        )
                    )
                ).first()
                after_id = int(cs.last_ltm_message_id or 0) if cs else 0
                stmt = (
                    select(ChatMessage)
                    .join(ChatSession, ChatSession.id == ChatMessage.session_id)
                    .where(
                        ChatSession.user_id == user_id,
                        ChatMessage.session_id == session_id,
                        ChatMessage.role.in_(["user", "assistant"]),
                        ChatMessage.id > after_id,
                    )
                    .order_by(ChatMessage.id.desc())
                    .limit(60)
                )
                msgs = list((await db.exec(stmt)).all())
                if not msgs:
                    return
                lines: list[str] = []
                latest_id = after_id
                for m in reversed(msgs):
                    latest_id = max(latest_id, int(m.id or 0))
                    text = extract_content_text(m.content)
                    if not text:
                        continue
                    label = "学生" if m.role == "user" else "辅导老师"
                    lines.append(f"{label}：{text[:700]}")
                new_dialogue = "\n".join(lines)
                if not new_dialogue or latest_id <= after_id:
                    return
                res = await ltm_service.maybe_update(
                    db=db,
                    user_id=user_id,
                    session_id=session_id,
                    user_message=user_message,
                    assistant_reply=assistant_reply,
                    new_dialogue=new_dialogue,
                    turn_count=len(msgs),
                    signal_detected=ltm_signal,
                )
                if res.get("analyzed") and cs:
                    cs.ltm_token_count = 0
                    cs.ltm_message_count = 0
                    cs.last_ltm_message_id = latest_id
                    cs.last_ltm_updated_at = now_utc()
                    cs.updated_at = now_utc()
                    db.add(cs)

        async def _do_eval_event() -> None:
            """记录一次辅导对话学习事件以驱动画像与评估更新。"""
            async with session_scope() as db:
                stmt = (
                    select(ChatSessionSummaryBlock.summary_markdown)
                    .where(ChatSessionSummaryBlock.session_id == session_id)
                    .order_by(ChatSessionSummaryBlock.created_at.desc())
                    .limit(1)
                )
                summary_text = (await db.exec(stmt)).first() or ""
                payload = LearningEventCreate(
                    module=MODULE_CHAT,
                    entity_id=session_id,
                    event_type=CHAT_DIALOGUE,
                    event_metadata={
                        "summary_length": len(summary_text or ""),
                        "turn_count": 1,
                    },
                )
                await EvaluationService().record_event(db, user_id=user_id, payload=payload)

        tasks: list[asyncio.Task[Any]] = [asyncio.create_task(_do_eval_event())]
        if should_compress:
            tasks.append(asyncio.create_task(_do_compress()))
        if should_ltm:
            tasks.append(asyncio.create_task(_do_ltm()))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as exc:
        logger.warning("[Memory] 后台记忆管线执行异常: %s", exc)


__all__ = [
    "ChatLongTermMemoryService",
    "ChatSessionCompressor",
    "DEFAULT_SESSION_TITLE",
    "LTM_CATEGORIES",
    "LTM_CATEGORY_NAMES",
    "MemoryUpdateOutput",
    "TITLE_MAX_LENGTH",
    "clean_session_title",
    "compact_text",
    "estimate_token_count",
    "extract_content_text",
    "generate_session_title",
    "get_memory_markdown",
    "get_session_summary_context",
    "has_stable_signal",
    "make_default_memory_markdown",
    "now_utc",
    "run_post_turn_memory_jobs",
]
