"""Chat 记忆管线 —— 基于 learn-claude-code s06 上下文自动压缩 (Auto-compact) 与长期记忆 (LTM)。"""

from __future__ import annotations

from datetime import datetime, timezone
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
from app.infra.llm import HumanMessage, LLM, SystemMessage, load_prompt
from app.infra.models import (
    ChatLongTermMemory,
    ChatMessage,
    ChatSession,
    ChatSessionSummaryBlock,
)

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


def now_utc() -> datetime:
    """返回当前 UTC 时间。"""
    return datetime.now(timezone.utc)


def extract_content_text(content: list[dict[str, Any]]) -> str:
    """从当前消息块列表中提取纯文本。"""
    return " ".join(part["text"] for part in content if part["type"] == "text").strip()


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


async def compress_session(user_id: int, session_id: str) -> ChatSessionSummaryBlock | None:
    """达到阈值后压缩完整旧轮次，保留近期消息并推进实际摘要水位。"""
    async with session_scope() as db:
        chat_session = await db.get(ChatSession, session_id)
        if chat_session is None or chat_session.user_id != user_id:
            return None
        latest_block = (await db.exec(
            select(ChatSessionSummaryBlock)
            .where(ChatSessionSummaryBlock.session_id == session_id)
            .order_by(ChatSessionSummaryBlock.block_index.desc())
            .limit(1)
        )).first()
        last_summarized_id = latest_block.end_message_id if latest_block else 0
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

        # 保留最近消息所在的完整轮次，水位只能推进到实际送入模型的内容。
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
        if latest_block and latest_block.summary_markdown:
            prompt += f"\n\n## 上一阶段滚动状态摘要\n{latest_block.summary_markdown}"

        resp = await LLM(temperature=0.7).text(
            [
                SystemMessage(content=prompt),
                HumanMessage(content="请根据以上对话记录输出会话摘要 Markdown。"),
            ]
        )
        summary_markdown = _strip_markdown_fence(resp)
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

        remaining = (await db.exec(select(ChatMessage).where(
            ChatMessage.session_id == session_id,
            ChatMessage.id > target[-1].id,
        ))).all()
        chat_session.summary_token_count = sum(
            estimate_token_count(extract_content_text(message.content)) for message in remaining
        )
        db.add(chat_session)
        return summary_block


async def update_long_term_memory(
    user_id: int, session_id: str, user_message: str, assistant_reply: str,
) -> None:
    """按稳定信号或累计阈值分析新增对话，更新长期记忆及已分析水位。"""
    detected = has_stable_signal(user_message) or (
        has_stable_signal(assistant_reply)
        and any(word in assistant_reply for word in ("以后", "下次", "记住", "偏好", "纠正"))
    )
    async with session_scope() as db:
        session = await db.get(ChatSession, session_id)
        if session is None or session.user_id != user_id or not session.ltm_message_count:
            return
        if not detected and session.ltm_token_count < UPDATE_MIN_TOKENS and session.ltm_message_count < UPDATE_MIN_MESSAGES:
            return
        old_memory = (await db.exec(select(ChatLongTermMemory).where(
            ChatLongTermMemory.user_id == user_id,
        ))).first()
        if old_memory and not detected and (now_utc() - old_memory.updated_at).total_seconds() < 1800:
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
        summary = (await db.exec(select(ChatSessionSummaryBlock.summary_markdown).where(
            ChatSessionSummaryBlock.session_id == session_id,
        ).order_by(ChatSessionSummaryBlock.block_index.desc()).limit(1))).first()
        prompt = load_prompt(
            _LTM_PROMPT,
            new_dialogue="\n".join(lines),
            user_message=user_message[:1000],
            assistant_reply=assistant_reply[:1000],
            session_summary=summary or "暂无会话概要。",
            old_memory=old_memory.memory_markdown if old_memory else make_default_memory_markdown(),
        )
        result = await LLM(temperature=0.1).json(MemoryUpdateOutput, prompt)
        if result.need_update and result.memory_markdown and result.confidence >= LTM_MIN_CONFIDENCE:
            if old_memory is None:
                old_memory = ChatLongTermMemory(user_id=user_id)
            old_memory.memory_markdown = result.memory_markdown
            old_memory.updated_at = now_utc()
            db.add(old_memory)
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
    """读取用户长期记忆 Markdown，可按分类名称截取对应小节。"""
    async with session_scope() as db:
        record = (
            await db.exec(select(ChatLongTermMemory).where(ChatLongTermMemory.user_id == user_id))
        ).first()
    markdown = record.memory_markdown.strip() if record else ""
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
