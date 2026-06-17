"""资源域持久化层 — Repository 模式 + ORM 映射。"""

from app.resource.persistence.mappers import (
    content_envelope,
    db_item_to_agent_result,
    db_item_to_resource_item,
)
from app.resource.persistence.repository import ResourceRepository

__all__ = [
    "ResourceRepository",
    "content_envelope",
    "db_item_to_agent_result",
    "db_item_to_resource_item",
]
