"""共享文本处理工具。"""
from datetime import datetime, timedelta

def normalize_text(content: str) -> str:
    return " ".join((content or "").strip().lower().split())

def now() -> datetime:
    return datetime.now()

def message_expire_cutoff(days: int = 7) -> datetime:
    return now() - timedelta(days=max(days, 0))

def estimate_token_count(text: str) -> int:
    stripped = (text or "").strip()
    if not stripped:
        return 0
    by_chars = max(1, len(stripped) // 4)
    by_words = len(stripped.split())
    return max(by_chars, by_words)
