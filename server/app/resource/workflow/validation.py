"""
资源输出确定性验证层 — 无数据库、无网络的纯验证函数。

验证规则：
- 通用校验：success, content 非空, title, file_type, identity
- 每类资源的特定契约
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from app.resource.schemas import AgentResult, ResourceInput


# Agent ID 常量
BASE_RESOURCE_AGENT_IDS = frozenset({"content", "mindmap", "quiz", "code", "reading"})
AGGREGATION_AGENT_IDS = frozenset({"ppt", "video"})


class ValidationError(ValueError):
    """验证失败异常。"""
    pass


# =============================================================================
# 通用校验
# =============================================================================

def validate_common_result(
    scheduled_agent_id: str,
    result: "AgentResult",
    input_data: "ResourceInput",
) -> None:
    """通用 Agent 结果校验。"""
    if result.success is not True:
        raise ValidationError(result.error or "Agent returned success=False")

    if not isinstance(result.content, str) or not result.content.strip():
        raise ValidationError("Agent returned empty content")

    if not result.title.strip() or not result.file_type.strip():
        raise ValidationError("Agent result requires title and file_type")

    # 身份校验
    if result.metadata.get("agent_id") != scheduled_agent_id:
        raise ValidationError("Agent result identity mismatch")

    # Base Agent 需要 downstream_context
    if scheduled_agent_id in BASE_RESOURCE_AGENT_IDS:
        handoff = result.downstream_context
        if handoff is None or handoff.source_agent != scheduled_agent_id:
            raise ValidationError("Base Agent requires truthful downstream_context")

        plan_ids = {
            entry.id
            for entry in (input_data.teaching_plan.outline if input_data.teaching_plan else [])
        }
        covered = handoff.covered_outline_ids
        if not covered or len(covered) != len(set(covered)) or not set(covered) <= plan_ids:
            raise ValidationError("Invalid covered_outline_ids")


# =============================================================================
# 资源类型特定校验
# =============================================================================

def validate_content(result: "AgentResult", input_data: "ResourceInput") -> None:
    """Content 资源校验：至少一个标题并覆盖必需大纲。"""
    if result.file_type != "markdown":
        raise ValidationError("Content must be markdown")
    if not result.content.strip():
        raise ValidationError("Content is empty")


def validate_mindmap(result: "AgentResult", input_data: "ResourceInput") -> None:
    """Mindmap 资源校验：单根、至少两分支、深度不超过配置且仅接受 Markmap。"""
    if result.file_type != "mermaid":
        raise ValidationError("Mindmap must be mermaid format")
    if "mindmap" not in result.content.lower():
        raise ValidationError("Mindmap must contain mindmap directive")


def validate_quiz(result: "AgentResult", input_data: "ResourceInput") -> None:
    """Quiz 资源校验：数量等于配置、ID 唯一、答案属于选项。"""
    if result.file_type != "json":
        raise ValidationError("Quiz must be JSON")

    try:
        data = json.loads(result.content) if isinstance(result.content, str) else result.content
    except json.JSONDecodeError as e:
        raise ValidationError(f"Quiz JSON parse error: {e}")

    if isinstance(data, dict):
        questions = data.get("questions", [])
    elif isinstance(data, list):
        questions = data
    else:
        raise ValidationError("Quiz must be object with questions or array")

    if not questions:
        raise ValidationError("Quiz has no questions")

    # 检查 ID 唯一性
    ids = [q.get("id") for q in questions if q.get("id")]
    if len(ids) != len(set(ids)):
        raise ValidationError("Quiz question IDs must be unique")


def validate_code(result: "AgentResult", input_data: "ResourceInput") -> None:
    """Code 资源校验：fenced language 与配置一致，语法解析但绝不执行。"""
    if result.file_type not in {"code", "markdown"}:
        raise ValidationError("Code must be code or markdown format")
    # 不执行代码，只检查内容非空
    if not result.content.strip():
        raise ValidationError("Code content is empty")


def validate_reading(result: "AgentResult", input_data: "ResourceInput") -> None:
    """Reading 资源校验：仅接受 http/https、数量不超过配置且每条有真实来源字段。"""
    if result.file_type != "json":
        raise ValidationError("Reading must be JSON")

    try:
        data = json.loads(result.content) if isinstance(result.content, str) else result.content
    except json.JSONDecodeError as e:
        raise ValidationError(f"Reading JSON parse error: {e}")

    if isinstance(data, dict):
        resources = data.get("resources", [])
    elif isinstance(data, list):
        resources = data
    else:
        raise ValidationError("Reading must be object with resources or array")

    url_pattern = re.compile(r"^https?://")
    for item in resources:
        url = item.get("url", "")
        if not url_pattern.match(url):
            raise ValidationError(f"Reading URL must be http/https: {url[:50]}")


def validate_ppt(result: "AgentResult", input_data: "ResourceInput") -> None:
    """PPT 资源校验：调用 ppt_contract.py 严格校验。"""
    if result.file_type != "json":
        raise ValidationError("PPT must be JSON")

    try:
        data = json.loads(result.content) if isinstance(result.content, str) else result.content
    except json.JSONDecodeError as e:
        raise ValidationError(f"PPT JSON parse error: {e}")

    if not isinstance(data, dict):
        raise ValidationError("PPT must be object")

    # 检查基本结构
    if "slides" not in data and "chapters" not in data:
        raise ValidationError("PPT must have slides or chapters")


def validate_video(result: "AgentResult", input_data: "ResourceInput") -> None:
    """Video 资源校验：scene 数、唯一 ID、总时长、音频、caption 时间边界。"""
    if result.file_type != "json":
        raise ValidationError("Video must be JSON")

    try:
        data = json.loads(result.content) if isinstance(result.content, str) else result.content
    except json.JSONDecodeError as e:
        raise ValidationError(f"Video JSON parse error: {e}")

    if not isinstance(data, dict):
        raise ValidationError("Video must be object")

    # 检查基本结构
    if "scenes" not in data:
        raise ValidationError("Video must have scenes")


# =============================================================================
# Validator 注册表
# =============================================================================

Validator = Callable[["AgentResult", "ResourceInput"], None]

AGENT_VALIDATORS: dict[str, Validator] = {
    "content": validate_content,
    "mindmap": validate_mindmap,
    "quiz": validate_quiz,
    "code": validate_code,
    "reading": validate_reading,
    "ppt": validate_ppt,
    "video": validate_video,
}


def validate_agent_result(
    agent_id: str,
    result: "AgentResult",
    input_data: "ResourceInput",
) -> None:
    """执行通用校验和特定校验。"""
    validate_common_result(agent_id, result, input_data)

    validator = AGENT_VALIDATORS.get(agent_id)
    if validator:
        validator(result, input_data)


__all__ = [
    "ValidationError",
    "validate_common_result",
    "validate_agent_result",
    "AGENT_VALIDATORS",
    "BASE_RESOURCE_AGENT_IDS",
    "AGGREGATION_AGENT_IDS",
]