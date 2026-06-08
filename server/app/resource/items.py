"""Resource item serialization helpers."""

from __future__ import annotations

import json
from typing import Any

from app.infra.models import GeneratedResourceItem as GeneratedResourceItemModel
from app.resource.schemas import GeneratedResourceItem, WorkerResult


def content_envelope(result: WorkerResult) -> tuple[dict[str, Any] | None, str | None]:
    """Split a WorkerResult into structured JSON and plain text storage."""
    fmt = result.file_type.lower()
    content = result.content
    envelope = {
        "title": result.title,
        "summary": result.summary,
        "summary_data": result.summary_data,
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
    envelope = dict(item.content_json) if isinstance(item.content_json, dict) else {}
    content = envelope.get("content") if item.content_json is not None else item.content_text
    return GeneratedResourceItem(
        id=str(item.id),
        type=item.agent_type,
        title=envelope.get("title") or item.title or f"学习资源 - {item.agent_type}",
        format=envelope.get("format") or item.content_format,
        content=content,
        summary=envelope.get("summary") or item.summary or "",
        summary_data=envelope.get("summary_data") or {},
        execution_report=item.execution_report,
        metadata=envelope.get("metadata") or item.metadata_json or {},
        status=item.status,
        error_message=item.error_message,
        created_at=item.created_at.isoformat() if item.created_at else None,
        updated_at=item.updated_at.isoformat() if item.updated_at else None,
    )


def db_item_to_worker_result(item: GeneratedResourceItemModel) -> WorkerResult:
    envelope = dict(item.content_json) if isinstance(item.content_json, dict) else {}
    content = envelope.get("content") if item.content_json is not None else item.content_text
    if not isinstance(content, str):
        content = json.dumps(content, ensure_ascii=False)
    return WorkerResult(
        success=True,
        content=content,
        file_type=envelope.get("format") or item.content_format,
        title=envelope.get("title") or item.title or "",
        summary=envelope.get("summary") or item.summary or "",
        summary_data=envelope.get("summary_data") or {},
        metadata=envelope.get("metadata") or item.metadata_json or {},
    )
