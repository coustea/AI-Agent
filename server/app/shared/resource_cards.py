"""Utilities for normalizing chat resource cards."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


RESOURCE_TOOL_NAME = "generate_learning_resource"
RESOURCE_TITLES = {
    "image": "图片学习资源",
    "video": "视频学习资源",
    "document": "文档学习资源",
    "ppt": "PPT学习资源",
}
DOCUMENT_EXTENSIONS = {".md", ".markdown", ".doc", ".docx", ".pdf", ".txt", ".ppt", ".pptx"}


def _parse_tool_result(raw_result: Any) -> dict[str, Any] | None:
    if isinstance(raw_result, dict):
        return raw_result
    if not isinstance(raw_result, str):
        return None

    text = raw_result.strip()
    if not text:
        return None

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _normalize_asset_urls(payload: dict[str, Any]) -> list[str]:
    asset_urls = payload.get("asset_urls")
    if isinstance(asset_urls, list):
        return [str(url) for url in asset_urls if url]

    for key in ("images", "videos", "files", "file_urls", "urls"):
        value = payload.get(key)
        if isinstance(value, list):
            return [str(url) for url in value if url]
    return []


def _normalize_resource_type(payload: dict[str, Any], call: dict[str, Any]) -> str:
    raw_type = str(payload.get("resource_type", "")).strip().lower()
    if not raw_type and isinstance(call.get("args"), dict):
        raw_type = str(call["args"].get("resource_type", "")).strip().lower()

    if raw_type in {"image", "video"}:
        return raw_type
    if raw_type in {"ppt", "slides", "powerpoint"}:
        return "ppt"
    if raw_type in {"document", "doc", "word", "markdown", "md"}:
        return "document"
    if raw_type in {"file", "files", "attachment", "attachments"}:
        return "document"

    file_path = str(payload.get("file_path") or "").strip()
    if file_path:
        suffix = Path(file_path).suffix.lower()
        if suffix in {".ppt", ".pptx"}:
            return "ppt"
        if suffix in DOCUMENT_EXTENSIONS:
            return "document"
    for asset in _normalize_asset_urls(payload):
        suffix = Path(asset).suffix.lower()
        if suffix in {".ppt", ".pptx"}:
            return "ppt"
        if suffix in DOCUMENT_EXTENSIONS:
            return "document"
    if file_path:
        return "document"
    return ""


def build_resource_cards_from_tool_calls(tool_calls: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not tool_calls:
        return []

    cards: list[dict[str, Any]] = []
    for call in tool_calls:
        if call.get("tool") != RESOURCE_TOOL_NAME:
            continue
        payload = _parse_tool_result(call.get("result"))
        if not payload or not payload.get("success"):
            continue

        resource_type = _normalize_resource_type(payload, call)
        if resource_type not in {"image", "video", "document", "ppt"}:
            continue

        summary = payload.get("summary") or ""
        file_path = payload.get("file_path")
        if resource_type == "document" and not summary and file_path:
            summary = f"已生成文档资源：{Path(str(file_path)).name}"

        card = {
            "type": resource_type,
            "title": payload.get("title") or RESOURCE_TITLES.get(resource_type, "学习资源"),
            "summary": summary,
            "asset_urls": _normalize_asset_urls(payload),
            "file_path": file_path,
            "preview_text": payload.get("preview_text") or payload.get("content") or "",
        }
        cards.append(card)

    return cards
