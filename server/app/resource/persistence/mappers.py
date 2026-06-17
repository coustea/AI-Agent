"""持久化模型与资源域 Schema 之间的映射辅助。"""

from __future__ import annotations

import json
from typing import Any

from app.infra.models import GeneratedResourceItem as GeneratedResourceItemModel
from app.resource.schemas import AgentResult, DownstreamContext, GeneratedResourceItem


def content_envelope(result: AgentResult) -> tuple[dict[str, Any] | None, str | None]:
    """将 AgentResult 内容拆分为 JSON 和纯文本存储字段。

    返回 (content_json, content_text) 元组：
    - markdown/text/code 类型 → content_json=None, content_text=原文
    - json 类型 → content_json=结构化数据, content_text=None
    """
    fmt = result.file_type.lower()
    content = result.content
    envelope = {
        "title": result.title,
        "summary": result.summary,
        "metadata": result.metadata,
        "format": result.file_type,
        "content": content,
    }
    if fmt in {"markdown", "mermaid", "text", "code"}:
        if isinstance(content, str):
            return envelope, content
        return envelope, json.dumps(content, ensure_ascii=False)
    if fmt == "json":
        if isinstance(content, dict):
            envelope["content"] = content
            return envelope, None
        if isinstance(content, list):
            envelope["content"] = {"items": content}
            return envelope, None
        if isinstance(content, str):
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                return envelope, content
            if isinstance(parsed, dict):
                envelope["content"] = parsed
                return envelope, None
            if isinstance(parsed, list):
                envelope["content"] = {"items": parsed}
                return envelope, None
            envelope["content"] = {"value": parsed}
            return envelope, None
        envelope["content"] = {"value": content}
        return envelope, None
    if isinstance(content, str):
        return envelope, content
    envelope["content"] = {"value": content}
    return envelope, None


def db_item_to_resource_item(item: GeneratedResourceItemModel) -> GeneratedResourceItem:
    """将数据库行转换为前端资源项 DTO。"""
    envelope = dict(item.content_json) if isinstance(item.content_json, dict) else {}
    content = envelope.get("content") if item.content_json is not None else item.content_text
    return GeneratedResourceItem(
        id=str(item.id),
        type=item.agent_type,
        title=envelope.get("title") or item.title or f"学习资源 - {item.agent_type}",
        format=envelope.get("format") or item.content_format,
        content=content,
        summary=envelope.get("summary") or item.summary or "",
        metrics=item.metrics or {},
        downstream_context=(
            DownstreamContext.model_validate(item.downstream_context)
            if isinstance(item.downstream_context, dict)
            else None
        ),
        execution_report=item.execution_report,
        metadata=envelope.get("metadata") or item.metadata_json or {},
        status=item.status,
        error_message=item.error_message,
        created_at=item.created_at.isoformat() if item.created_at else None,
        updated_at=item.updated_at.isoformat() if item.updated_at else None,
    )


def db_item_to_agent_result(item: GeneratedResourceItemModel) -> AgentResult:
    """将数据库行转换为 AgentResult，供下游审核/工作流使用。"""
    envelope = dict(item.content_json) if isinstance(item.content_json, dict) else {}
    content = envelope.get("content") if item.content_json is not None else item.content_text
    if not isinstance(content, str):
        content = json.dumps(content, ensure_ascii=False)
    return AgentResult(
        success=True,
        content=content,
        file_type=envelope.get("format") or item.content_format,
        title=envelope.get("title") or item.title or "",
        summary=envelope.get("summary") or item.summary or "",
        metrics=item.metrics or {},
        downstream_context=(
            DownstreamContext.model_validate(item.downstream_context)
            if isinstance(item.downstream_context, dict)
            else None
        ),
        metadata=envelope.get("metadata") or item.metadata_json or {},
    )
