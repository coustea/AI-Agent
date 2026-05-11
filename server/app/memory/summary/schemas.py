"""概要 API Schema。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SummaryResponse(BaseModel):
    """概要响应。"""
    id: int
    user_id: int
    session_id: str
    module: str
    summary_markdown: str
    summary_json: dict | None
    summary_type: str
    version: int
    current_topic: str | None
    current_goal: str | None
    summarized_message_count: int
    created_at: datetime

    @classmethod
    def from_model(cls, summary: Any) -> "SummaryResponse":
        return cls(
            id=summary.id,
            user_id=summary.user_id,
            session_id=summary.session_id,
            module=summary.module,
            summary_markdown=summary.summary_markdown,
            summary_json=summary.summary_json,
            summary_type=summary.summary_type,
            version=summary.version,
            current_topic=summary.current_topic,
            current_goal=summary.current_goal,
            summarized_message_count=summary.summarized_message_count,
            created_at=summary.created_at,
        )
