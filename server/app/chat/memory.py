"""Chat 记忆管线 —— 基于上下文自动压缩 (Auto-compact) 与长期记忆 (LTM)。"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Final

from pydantic import BaseModel
from sqlmodel import select

from app.config import (
    COMPRESS_KEEP_RECENT_MESSAGES,
    COMPRESS_MIN_MESSAGES,
    COMPRESS_MIN_TOKENS,
    LTM_MIN_CONFIDENCE,
    UPDATE_MIN_MESSAGES,
    UPDATE_MIN_TOKENS,
)
from app.infra.database import session_scope
from app.infra.logging import get_logger
from app.infra.types import now_utc
from app.infra.llm import HumanMessage, LLM, SystemMessage, load_prompt
from app.infra.models import (
    ChatMessage,
    ChatSession,
    User,
)

logger = get_logger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
_COMPRESSION_PROMPT = _PROMPTS_DIR / "compression.md"
_LTM_PROMPT = _PROMPTS_DIR / "ltm_update.md"

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


def extract_content_text(content: list[dict[str, Any]]) -> str:
    """从当前消息块列表中提取纯文本。"""
    return " ".join(part["text"] for part in content if part.get("type") == "text").strip()


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
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", stripped))
    non_chinese = re.sub(r"[\u4e00-\u9fff]", "", stripped)
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


async def compress_session(user_id: int, session_id: str) -> str | None:
    """达到阈值后压缩完整旧轮次，滚动更新会话内置摘要并推进水位。"""
    async with session_scope() as db:
        chat_session = await db.get(ChatSession, session_id)
        if chat_session is None or chat_session.user_id != user_id:
            return None

        last_summarized_id = chat_session.last_summarized_message_id
        messages = (await db.exec(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id, ChatMessage.id > last_summarized_id)
            .order_by(ChatMessage.id.asc())
        )).all()

        if chat_session.summary_token_count < COMPRESS_MIN_TOKENS and len(messages) < COMPRESS_MIN_MESSAGES:
            return None
        dialogue = [
            message for message in messages
            if message.role in {"user", "assistant"} and extract_content_text(message.content)
        ]
        if len(dialogue) <= COMPRESS_KEEP_RECENT_MESSAGES:
            return None

        cutoff = max(0, len(dialogue) - COMPRESS_KEEP_RECENT_MESSAGES)
        while 0 < cutoff < len(dialogue) and dialogue[cutoff].role != "user":
            cutoff -= 1
        if cutoff == 0:
            return None

        target: list[ChatMessage] = []
        lines: list[str] = []
        chars = 0
        for message in dialogue[:cutoff]:
            if message.role == "user" and chars >= 8000:
                break
            line = f"[{message.created_at:%m-%d %H:%M}] {message.role}: {extract_content_text(message.content)}"
            target.append(message)
            lines.append(line)
            chars += len(line)

        prompt = load_prompt(_COMPRESSION_PROMPT, dialogue_text="\n".join(lines))
        if chat_session.summary_markdown:
            prompt += f"\n\n## 上一阶段滚动状态摘要\n{chat_session.summary_markdown}"

        resp = await LLM(temperature=0.7).text(
            [
                SystemMessage(content=prompt),
                HumanMessage(content="请根据以上对话记录输出会话摘要 Markdown。"),
            ]
        )
        summary_markdown = _strip_markdown_fence(resp)
        if not summary_markdown:
            raise RuntimeError("LLM 生成的会话摘要为空")

        chat_session.summary_markdown = summary_markdown
        chat_session.last_summarized_message_id = target[-1].id

        remaining = (await db.exec(select(ChatMessage).where(
            ChatMessage.session_id == session_id,
            ChatMessage.id > target[-1].id,
        ))).all()
        chat_session.summary_token_count = sum(
            estimate_token_count(extract_content_text(message.content)) for message in remaining
        )
        chat_session.updated_at = now_utc()
        db.add(chat_session)
        logger.info(
            "[ChatMemory] 会话压缩完成: session_id=%s 压缩 %d 条消息 摘要 %d 字符 剩余水位 %d tokens",
            session_id, len(target), len(summary_markdown), chat_session.summary_token_count,
        )
        return summary_markdown


async def update_long_term_memory(
    user_id: int, session_id: str, user_message: str, assistant_reply: str,
) -> None:
    """按稳定信号或累计阈值分析新增对话，直接增量更新 User 表中的长期记忆。"""
    detected = has_stable_signal(user_message) or (
        has_stable_signal(assistant_reply)
        and any(word in assistant_reply for word in ("以后", "下次", "记住", "偏好", "纠正"))
    )
    async with session_scope() as db:
        session = await db.get(ChatSession, session_id)
        user = await db.get(User, user_id)
        if session is None or user is None or session.user_id != user_id or not session.ltm_message_count:
            return

        if not detected and session.ltm_token_count < UPDATE_MIN_TOKENS and session.ltm_message_count < UPDATE_MIN_MESSAGES:
            return

        if user.long_term_memory and not detected and user.updated_at and (now_utc() - user.updated_at).total_seconds() < 1800:
            return

        messages = (await db.exec(select(ChatMessage).where(
            ChatMessage.session_id == session_id,
            ChatMessage.role.in_(["user", "assistant"]),
            ChatMessage.id > (session.last_ltm_message_id or 0),
        ).order_by(ChatMessage.id.asc()).limit(60))).all()
        lines = [
            f"{'学生' if message.role == 'user' else '辅导老师'}：{text}"
            for message in messages if (text := extract_content_text(message.content))
        ]
        if not lines:
            return

        prompt = load_prompt(
            _LTM_PROMPT,
            new_dialogue="\n".join(lines),
            user_message=user_message[:1000],
            assistant_reply=assistant_reply[:1000],
            session_summary=session.summary_markdown or "暂无会话概要。",
            old_memory=user.long_term_memory or make_default_memory_markdown(),
        )
        result = await LLM(temperature=0.1).json(MemoryUpdateOutput, prompt)
        if result.need_update and result.memory_markdown and result.confidence >= LTM_MIN_CONFIDENCE:
            user.long_term_memory = result.memory_markdown
            user.updated_at = now_utc()
            db.add(user)
            logger.info(
                "[ChatMemory] 长期记忆已更新: user_id=%d confidence=%.2f reason=%s",
                user_id, result.confidence, result.update_reason,
            )
        else:
            logger.info(
                "[ChatMemory] 长期记忆未更新: user_id=%d need_update=%s confidence=%.2f (阈值 %.2f)",
                user_id, result.need_update, result.confidence, LTM_MIN_CONFIDENCE,
            )

        latest_id = messages[-1].id
        remaining = (await db.exec(select(ChatMessage).where(
            ChatMessage.session_id == session_id, ChatMessage.id > latest_id,
        ))).all()
        session.ltm_token_count = sum(estimate_token_count(extract_content_text(m.content)) for m in remaining)
        session.ltm_message_count = len(remaining)
        session.last_ltm_message_id = latest_id
        session.last_ltm_updated_at = now_utc()
        session.updated_at = now_utc()
        db.add(session)


async def get_memory_markdown(user_id: int, category: str | None = None) -> str:
    """读取 User 表中的长期记忆 Markdown，可按分类名称截取对应小节。"""
    async with session_scope() as db:
        user = await db.get(User, user_id)
    markdown = (user.long_term_memory if user else "").strip()
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
