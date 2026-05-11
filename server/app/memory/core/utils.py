"""核心工具函数。

模块职责：
- 时间工具
- Token 估算
- 文本处理
"""

from __future__ import annotations

from datetime import datetime, timedelta


def now() -> datetime:
    """获取当前时间。"""
    return datetime.now()


def utcnow() -> datetime:
    """获取当前 UTC 时间。"""
    from datetime import timezone
    return datetime.now(timezone.utc)


def days_ago(days: int) -> datetime:
    """获取 N 天前的时间。"""
    return now() - timedelta(days=max(days, 0))


def estimate_token_count(text: str) -> int:
    """估算文本 token 数量。

    使用简单估算：取字符数/4 和词数的最大值。
    """
    stripped = (text or "").strip()
    if not stripped:
        return 0
    return max(max(1, len(stripped) // 4), len(stripped.split()))


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """截断文本到指定长度。"""
    if len(text) <= max_length:
        return text
    return text[: max(max_length - len(suffix), 0)].rstrip() + suffix


def strip_markdown_fence(content: str) -> str:
    """去除 Markdown 代码围栏。"""
    text = (content or "").strip()
    if text.startswith("```markdown"):
        text = text[len("```markdown"):].strip()
    if text.startswith("```json"):
        text = text[len("```json"):].strip()
    if text.startswith("```"):
        text = text[3:].strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    return text
