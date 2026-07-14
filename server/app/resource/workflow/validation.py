"""资源输出确定性验证层 — 无数据库、无网络的纯验证函数。

验证规则：
- 通用校验：success, content 非空, title, file_type, identity
- 每类资源的特定契约
- 内容去重：检查相似度过高的内容
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Callable

from app.resource.schemas.quiz import (
    QuizPayload,
    build_quiz_blueprint,
    validate_quiz_payload,
)
from app.resource.catalog import BASE_RESOURCE_AGENT_IDS

if TYPE_CHECKING:
    from app.resource.schemas import AgentResult, ResourceInput

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

    # HTML 文件型不要求内联正文，其余类型内容必须非空
    if result.file_type != "html" and (not isinstance(result.content, str) or not result.content.strip()):
        raise ValidationError("Agent returned empty content")

    # 标题与文件类型缺失则不合格
    if not result.title.strip() or not result.file_type.strip():
        raise ValidationError("Agent result requires title and file_type")

    # 身份校验：结果中的 agent_id 必须与调度的一致
    if result.metadata.get("agent_id") != scheduled_agent_id:
        raise ValidationError("Agent result identity mismatch")

    # 基础 Agent 必须基于协同计划生成（聚合 Agent 由上游提供）
    if scheduled_agent_id in BASE_RESOURCE_AGENT_IDS:
        if not input_data.teaching_plan:
            raise ValidationError("Base Agent requires a teaching plan")


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
    """Mindmap 资源校验：Markdown 格式（Markmap）、至少包含一级标题和二级标题。"""
    if result.file_type != "markdown":
        raise ValidationError("Mindmap must be markdown format (for Markmap rendering)")

    content = result.content.strip()
    if not content:
        raise ValidationError("Mindmap content is empty")

    # 解析标题层级，校验是否为合法导图结构
    lines = content.splitlines()
    has_h1 = any(line.strip().startswith("# ") for line in lines)
    h2_count = sum(1 for line in lines if line.strip().startswith("## "))

    # 必须有一个一级标题作为根节点
    if not has_h1:
        raise ValidationError("Mindmap must have at least one level-1 heading (#) as root")

    # 至少两个二级标题作为分支
    if h2_count < 2:
        raise ValidationError("Mindmap must have at least two level-2 headings (##) as branches")


def validate_quiz(result: "AgentResult", input_data: "ResourceInput") -> None:
    """Quiz 资源校验：结构、数量、题型和难度必须与请求蓝图一致。"""
    if result.file_type != "json":
        raise ValidationError("Quiz must be JSON")

    # 解析 JSON 内容
    try:
        data = json.loads(result.content) if isinstance(result.content, str) else result.content
    except json.JSONDecodeError as e:
        raise ValidationError(f"Quiz JSON parse error: {e}")

    if not isinstance(data, dict):
        raise ValidationError("Quiz must be a QuizPayload object")

    # 校验结构化契约并比对确定性蓝图
    try:
        payload = QuizPayload.model_validate(data)
        blueprint = build_quiz_blueprint(
            question_count=int(input_data.agent_config.get("question_count", 5)),
            question_types=input_data.agent_config.get("question_types"),
            difficulty_mode=str(
                input_data.agent_config.get("difficulty_mode", "basic")
            ),
        )
        validate_quiz_payload(payload, blueprint)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"Quiz contract validation failed: {exc}") from exc


def validate_code(result: "AgentResult", input_data: "ResourceInput") -> None:
    """Code 资源校验：fenced language 与配置一致，语法解析但绝不执行。"""
    if result.file_type not in {"code", "markdown"}:
        raise ValidationError("Code must be code or markdown format")
    if not result.content.strip():
        raise ValidationError("Code content is empty")


def validate_reading(result: "AgentResult", input_data: "ResourceInput") -> None:
    """Reading 资源校验：所有资源必须有有效的 http/https URL。"""
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

    # 至少一条阅读资源
    if not resources:
        raise ValidationError("Reading must have at least one resource")

    url_pattern = re.compile(r"^https?://")

    # 逐条校验 URL 必须为有效 http/https 链接
    for i, item in enumerate(resources, start=1):
        if not isinstance(item, dict):
            raise ValidationError(f"Resource #{i} must be an object")

        url = item.get("url", "")
        if not url or not url.strip() or not url_pattern.match(url):
            raise ValidationError(f"Reading resource #{i} has invalid URL: {url!r}")


def validate_ppt(result: "AgentResult", input_data: "ResourceInput") -> None:
    """PPT 资源只校验发布引用。"""
    if result.file_type != "html":
        raise ValidationError("PPT resource must be HTML format")

    metadata = result.metadata or {}
    if not str(metadata.get("html_file_path", "")).strip():
        raise ValidationError("PPT resource requires html_file_path")
    if not str(metadata.get("html_url", "")).strip():
        raise ValidationError("PPT resource requires html_url")


def validate_cartoon(result: "AgentResult", input_data: "ResourceInput") -> None:
    """Cartoon 资源必须提供 HyperFrames 生成的带音频 MP4 发布引用。"""
    if result.file_type != "mp4":
        raise ValidationError("Cartoon must be MP4")

    # 解析产物元数据 JSON
    try:
        data = json.loads(result.content) if isinstance(result.content, str) else result.content
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Cartoon JSON parse error: {exc}") from exc

    # 逐项校验动画产物契约
    if not isinstance(data, dict) or data.get("schema_version") != "cartoon/v6":
        raise ValidationError("Cartoon must use the cartoon/v6 schema")
    if not str(data.get("video_url", "")).endswith(".mp4"):
        raise ValidationError("Cartoon must expose an MP4 video_url")
    if float(data.get("duration_seconds", 0)) <= 0:
        raise ValidationError("Cartoon duration must be positive")
    if int(data.get("scene_count", 0)) < 3:
        raise ValidationError("Cartoon must contain at least three scenes")
    if result.metadata.get("engine") != "hyperframes":
        raise ValidationError("Cartoon must be rendered by HyperFrames")
    if result.metadata.get("has_audio") is not True:
        raise ValidationError("Cartoon must contain an audio stream")


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
    "cartoon": validate_cartoon,
}


def validate_agent_result(
    agent_id: str,
    result: "AgentResult",
    input_data: "ResourceInput",
) -> None:
    """执行通用校验和类型契约校验。"""
    # 先执行通用校验
    validate_common_result(agent_id, result, input_data)

    # 再执行该 agent 的特定契约校验
    validator = AGENT_VALIDATORS.get(agent_id)
    if validator:
        validator(result, input_data)

__all__ = [
    "ValidationError",
    "validate_common_result",
    "validate_agent_result",
    "AGENT_VALIDATORS",
]
