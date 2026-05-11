"""长期记忆 API Schema。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class LongTermMemoryResponse(BaseModel):
    """长期记忆响应。"""
    user_id: int
    module: str
    memory_markdown: str
    memory_json: dict[str, Any] | None
    version: int
    confidence: float
    updated_reason: str | None
    updated_at: datetime

    @classmethod
    def from_model(cls, memory: Any) -> "LongTermMemoryResponse":
        return cls(
            user_id=memory.user_id,
            module=memory.module,
            memory_markdown=memory.memory_markdown,
            memory_json=memory.memory_json,
            version=memory.version,
            confidence=memory.confidence,
            updated_reason=memory.updated_reason,
            updated_at=memory.updated_at,
        )
