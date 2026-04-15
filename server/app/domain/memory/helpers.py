"""
共享文本处理工具。

MemoryService / FactAgent / ProfileAgent 共用的 _normalize_text 唯一实现。
"""

from datetime import datetime, timedelta


def normalize_text(content: str) -> str:
    """标准化文本：去除首尾空白、折叠连续空格、统一小写。"""
    return " ".join((content or "").strip().lower().split())


def now() -> datetime:
    """统一的当前时间获取，方便测试 mock。"""
    return datetime.now()


def message_expire_cutoff(days: int = 7) -> datetime:
    """计算消息过期截止时间。"""
    return now() - timedelta(days=max(days, 0))


def estimate_token_count(text: str) -> int:
    """近似 token 估算：字符长度/4 与空格词数取大值。"""
    stripped = (text or "").strip()
    if not stripped:
        return 0
    by_chars = max(1, len(stripped) // 4)
    by_words = len(stripped.split())
    return max(by_chars, by_words)
