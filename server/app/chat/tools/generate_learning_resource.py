"""High-level chat tool for on-demand learning resources."""

from __future__ import annotations

from langchain.tools import tool

from app.chat.context import get_current_user_id
from app.chat.services.learning_resource import learning_resource_service


@tool("generate_learning_resource")
async def generate_learning_resource(
    resource_type: str,
    topic: str,
    course: str = "",
    gap: str = "",
    need: str = "review",
    reason: str = "",
    extra: str = "",
) -> dict:
    """按需生成学习资源。"""
    current_user_id = get_current_user_id()
    return await learning_resource_service.generate(
        current_user_id=current_user_id,
        resource_type=resource_type,
        topic=topic,
        course=course,
        gap=gap,
        need=need,
        reason=reason,
        extra=extra,
    )
