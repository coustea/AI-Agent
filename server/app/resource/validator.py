"""Resource 模块确定性校验与上游交接内容提取器 (app.resource.validator)。"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Callable

from app.resource.catalog import BASE_RESOURCE_AGENT_IDS
from app.resource.schemas import (
    QuizPayload,
    build_quiz_blueprint,
    validate_quiz_payload,
)
from app.shared.cartoon.schemas import CartoonResourceMetadata

if TYPE_CHECKING:
    from app.resource.schemas import AgentResult, ResourceInput


class ValidationError(ValueError):
    """资源结果校验失败异常。"""


# ── 1. 确定性输出契约校验 ─────────────────────────────────────────────────


def validate_common_result(
    scheduled_agent_id: str,
    result: "AgentResult",
    input_data: "ResourceInput",
) -> None:
    """通用 Agent 结果校验。"""
    if result.success is not True:
        raise ValidationError(result.error or "Agent returned success=False")

    if result.file_type not in {"html", "mp4"} and (
        not isinstance(result.content, str) or not result.content.strip()
    ):
        raise ValidationError("Agent returned empty content")

    if not result.title.strip() or not result.file_type.strip():
        raise ValidationError("Agent result requires title and file_type")

    if result.metadata.get("agent_id") != scheduled_agent_id:
        raise ValidationError("Agent result identity mismatch")

    if scheduled_agent_id in BASE_RESOURCE_AGENT_IDS and not input_data.teaching_plan:
        raise ValidationError("Base Agent requires a teaching plan")


def validate_content(result: "AgentResult", input_data: "ResourceInput") -> None:
    _ = input_data
    if result.file_type != "markdown" or not result.content.strip():
        raise ValidationError("Content must be non-empty markdown")


def validate_mindmap(result: "AgentResult", input_data: "ResourceInput") -> None:
    _ = input_data
    if result.file_type != "markdown":
        raise ValidationError("Mindmap must be markdown format")
    content = result.content.strip()
    if not content:
        raise ValidationError("Mindmap content is empty")
    lines = content.splitlines()
    if not any(line.strip().startswith("# ") for line in lines):
        raise ValidationError("Mindmap must have at least one level-1 heading (#) as root")
    if sum(1 for line in lines if line.strip().startswith("## ")) < 2:
        raise ValidationError("Mindmap must have at least two level-2 headings (##) as branches")


def validate_quiz(result: "AgentResult", input_data: "ResourceInput") -> None:
    if result.file_type != "json":
        raise ValidationError("Quiz must be JSON")
    try:
        data = json.loads(result.content) if isinstance(result.content, str) else result.content
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Quiz JSON parse error: {exc}") from exc
    if not isinstance(data, dict):
        raise ValidationError("Quiz must be a QuizPayload object")
    try:
        payload = QuizPayload.model_validate(data)
        blueprint = build_quiz_blueprint(
            question_count=int(input_data.agent_config.get("question_count", 5)),
            question_types=input_data.agent_config.get("question_types"),
            difficulty_mode=str(input_data.agent_config.get("difficulty_mode", "basic")),
        )
        validate_quiz_payload(payload, blueprint)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"Quiz contract validation failed: {exc}") from exc


def validate_code(result: "AgentResult", input_data: "ResourceInput") -> None:
    _ = input_data
    if result.file_type not in {"code", "markdown"} or not result.content.strip():
        raise ValidationError("Code must be non-empty code or markdown format")


def validate_reading(result: "AgentResult", input_data: "ResourceInput") -> None:
    _ = input_data
    if result.file_type != "json":
        raise ValidationError("Reading must be JSON")
    try:
        data = json.loads(result.content) if isinstance(result.content, str) else result.content
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Reading JSON parse error: {exc}") from exc

    resources = data.get("resources", []) if isinstance(data, dict) else data
    if not isinstance(resources, list) or not resources:
        raise ValidationError("Reading must have at least one resource")

    url_pattern = re.compile(r"^https?://")
    for i, item in enumerate(resources, start=1):
        if not isinstance(item, dict):
            raise ValidationError(f"Resource #{i} must be an object")
        url = str(item.get("url") or "").strip()
        if not url_pattern.match(url):
            raise ValidationError(f"Reading resource #{i} has invalid URL: {url!r}")


def validate_ppt(result: "AgentResult", input_data: "ResourceInput") -> None:
    _ = input_data
    if result.file_type != "html":
        raise ValidationError("PPT resource must be HTML format")
    metadata = result.metadata or {}
    if not str(metadata.get("html_file_path", "")).strip():
        raise ValidationError("PPT resource requires html_file_path")
    if not str(metadata.get("html_url", "")).strip():
        raise ValidationError("PPT resource requires html_url")


def validate_cartoon(result: "AgentResult", input_data: "ResourceInput") -> None:
    _ = input_data
    if result.file_type != "mp4":
        raise ValidationError("Cartoon must be MP4")
    try:
        CartoonResourceMetadata.model_validate(result.metadata)
    except ValueError as exc:
        raise ValidationError(f"Cartoon metadata contract failed: {exc}") from exc


Validator = Callable[["AgentResult", "ResourceInput"], None]

AGENT_VALIDATORS: dict[str, Validator] = {
    "content": validate_content,
    "mindmap": validate_mindmap,
    "quiz": validate_quiz,
    "code": validate_code,
    "reading": validate_reading,
    "ppt": validate_ppt,
    "cartoon": validate_cartoon,
}


def validate_agent_result(
    agent_id: str,
    result: "AgentResult",
    input_data: "ResourceInput",
) -> None:
    """执行通用校验与特定 Agent 契约校验。"""
    validate_common_result(agent_id, result, input_data)
    validator = AGENT_VALIDATORS.get(agent_id)
    if validator:
        validator(result, input_data)


# ── 2. 上游交接素材提取 (Handoff Extraction) ─────────────────────────────


CONTENT_SECTION_MAP: dict[str, list[str]] = {
    "progressive": ["## 概述", "## 核心概念", "## 应用场景", "## 总结"],
    "summary_first": ["## 核心要点", "## 概念精解", "## 复习建议"],
    "exam_points": ["## 高频考点", "## 复习策略"],
    "case_driven": ["## 引入案例", "## 概念解析", "## 原理透视", "## 总结"],
}


def extract_core_content(
    markdown: str,
    agent_id: str,
    config: dict,
    *,
    max_blocks: int = 12,
    block_limit: int = 2400,
    total_limit: int = 12000,
) -> list[str]:
    """提取基础 Agent 输出中的语义完整块，供聚合 Agent (PPT/Cartoon) 作为上游素材消费。"""
    if not markdown or not markdown.strip():
        return []
    content = markdown.strip()[:total_limit]

    if agent_id == "content":
        structure = config.get("structure", "progressive")
        target_sections = CONTENT_SECTION_MAP.get(structure, CONTENT_SECTION_MAP["progressive"])
        blocks: list[str] = []
        for section_title in target_sections:
            sec = _extract_section(content, section_title)
            if not sec:
                continue
            truncated = _truncate_block(sec, block_limit)
            if truncated:
                blocks.append(truncated)
            if len(blocks) >= max_blocks:
                break
        if blocks:
            return blocks[:max_blocks]
    elif agent_id == "code":
        blocks = []
        goal_sec = _extract_section(content, "## 案例目标")
        if goal_sec:
            truncated = _truncate_block(goal_sec, block_limit)
            if truncated:
                blocks.append(truncated)
        for cb in re.findall(r"```[\w]*\n.*?```", content, re.DOTALL):
            if cb.strip() and len(blocks) < max_blocks:
                blocks.append(cb.strip())
        exp_sec = _extract_section(content, "## 关键解释")
        if exp_sec and len(blocks) < max_blocks:
            truncated = _truncate_block(exp_sec, block_limit)
            if truncated:
                blocks.append(truncated)
        if blocks:
            return blocks[:max_blocks]

    return _fallback_paragraph_split(content, max_blocks, block_limit)


def _extract_section(markdown: str, section_title: str) -> str:
    pattern = rf"^##\s*{re.escape(section_title[3:].strip())}\s*$"
    in_section = False
    section_lines: list[str] = []
    for line in markdown.splitlines():
        if re.match(pattern, line.strip()):
            in_section = True
            continue
        if in_section:
            if line.strip().startswith("## "):
                break
            section_lines.append(line)
    return "\n".join(section_lines).strip()


def _truncate_block(text: str, limit: int) -> str | None:
    if not text:
        return None
    if len(text) <= limit:
        return text
    truncated = text[:limit]
    last_period = max(
        truncated.rfind("。"),
        truncated.rfind("."),
        truncated.rfind("！"),
        truncated.rfind("？"),
    )
    if last_period > limit * 0.7:
        truncated = truncated[: last_period + 1]
    return truncated.strip() or None


def _fallback_paragraph_split(markdown: str, max_blocks: int, block_limit: int) -> list[str]:
    chunks: list[str] = []
    current = ""
    for paragraph in markdown.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        candidate = f"{current}\n\n{paragraph}".strip()
        if current and len(candidate) > block_limit:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks[:max_blocks]


__all__ = [
    "AGENT_VALIDATORS",
    "CONTENT_SECTION_MAP",
    "ValidationError",
    "extract_core_content",
    "validate_agent_result",
    "validate_common_result",
]
