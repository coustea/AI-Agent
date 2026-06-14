"""Resource item serialization helpers."""

from __future__ import annotations

import json
from typing import Any

from app.infra.models import GeneratedResourceItem as GeneratedResourceItemModel
from app.resource.schemas import GeneratedResourceItem, WorkerResult


def content_envelope(result: WorkerResult) -> tuple[dict[str, Any] | None, str | None]:
    """将 WorkerResult 拆分为结构化 JSON 和纯文本两个存储字段。

    返回 (content_json, content_text)：
    - markdown/mermaid/text/code 格式 → content_text 存储原始文本
    - json 格式 → content_json 存储结构化数据
    """
    fmt = result.file_type.lower()  # 统一转小写便于匹配
    content = result.content
    envelope = {  # 构建元数据信封，所有格式都包含这些字段
        "title": result.title,
        "summary": result.summary,
        "summary_data": result.summary_data,
        "metadata": result.metadata,
        "format": result.file_type,
        "content": content,
    }
    if fmt in {"markdown", "mermaid", "text", "code"}:  # 文本类格式直接存 content_text
        if isinstance(content, str):
            return envelope, content
        return envelope, json.dumps(content, ensure_ascii=False)  # 非字符串内容序列化为 JSON
    if fmt == "json":  # 结构化格式存 content_json
        if isinstance(content, dict):
            envelope["content"] = content  # dict 直接作为 JSON 主体
            return envelope, None
        if isinstance(content, list):
            envelope["content"] = {"items": content}  # list 包装为 {"items": [...]}
            return envelope, None
        if isinstance(content, str):  # LLM 可能返回 JSON 字符串，需要解析
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                return envelope, content  # 解析失败则降级存为纯文本
            if isinstance(parsed, dict):
                envelope["content"] = parsed
                return envelope, None
            if isinstance(parsed, list):
                envelope["content"] = {"items": parsed}
                return envelope, None
            envelope["content"] = {"value": parsed}  # 其他类型包装为 {"value": ...}
            return envelope, None
        envelope["content"] = {"value": content}  # 非 dict/list/str 类型兜底
        return envelope, None
    if isinstance(content, str):
        return envelope, content  # 未知格式兜底为纯文本
    envelope["content"] = {"value": content}
    return envelope, None


def db_item_to_resource_item(item: GeneratedResourceItemModel) -> GeneratedResourceItem:
    """将数据库记录转换为前端 ResourceItem DTO。"""
    envelope = dict(item.content_json) if isinstance(item.content_json, dict) else {}  # 提取 JSON 信封
    content = envelope.get("content") if item.content_json is not None else item.content_text  # 优先从 JSON 取内容
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
