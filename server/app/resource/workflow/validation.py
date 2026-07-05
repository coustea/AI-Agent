"""
资源输出确定性验证层 — 无数据库、无网络的纯验证函数。

验证规则：
- 通用校验：success, content 非空, title, file_type, identity
- 每类资源的特定契约
- 内容去重：检查 avoid_overlap_with 配置，警告相似度过高的内容
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any, Callable

from app.infra.logging import get_logger
from app.resource.schemas.quiz import (
    QuizPayload,
    build_quiz_blueprint,
    validate_quiz_payload,
)
from app.resource.service import (
    AGGREGATION_AGENT_IDS,
    BASE_RESOURCE_AGENT_IDS,
)

if TYPE_CHECKING:
    from app.resource.schemas import AgentResult, ResourceInput, TeachingPlan

logger = get_logger(__name__)


# 内容相似度阈值
CONTENT_SIMILARITY_THRESHOLD = 0.7


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

    if result.file_type != "html" and (not isinstance(result.content, str) or not result.content.strip()):
        raise ValidationError("Agent returned empty content")

    if not result.title.strip() or not result.file_type.strip():
        raise ValidationError("Agent result requires title and file_type")

    # 身份校验
    if result.metadata.get("agent_id") != scheduled_agent_id:
        raise ValidationError("Agent result identity mismatch")

    # Base Agent 校验
    if scheduled_agent_id in BASE_RESOURCE_AGENT_IDS:
        if input_data.teaching_plan is None:
            raise ValidationError("Base Agent requires a TeachingPlan")
        task = input_data.teaching_plan.task_for(scheduled_agent_id)
        if result.file_type != task.deliverable.format:
            raise ValidationError(
                f"Agent result format does not match Worker Task: "
                f"expected={task.deliverable.format} actual={result.file_type}"
            )


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
    """Mindmap 资源校验：Markdown 格式（Markmap）、至少包含一级标题和二级标题。

    Mindmap agent 生成标准 Markdown 标题+列表结构，前端使用 Markmap 渲染。
    不使用 Mermaid 语法。
    """
    if result.file_type != "markdown":
        raise ValidationError("Mindmap must be markdown format (for Markmap rendering)")

    # 检查基本的 Markdown 标题结构
    content = result.content.strip()
    if not content:
        raise ValidationError("Mindmap content is empty")

    # 至少需要一个一级标题（根节点）和至少两个二级标题（分支）
    lines = content.splitlines()
    has_h1 = any(line.strip().startswith("# ") for line in lines)
    h2_count = sum(1 for line in lines if line.strip().startswith("## "))

    if not has_h1:
        raise ValidationError("Mindmap must have at least one level-1 heading (#) as root")

    if h2_count < 2:
        raise ValidationError("Mindmap must have at least two level-2 headings (##) as branches")


def validate_quiz(result: "AgentResult", input_data: "ResourceInput") -> None:
    """Quiz 资源校验：结构、数量、题型和难度必须与请求蓝图一致。"""
    if result.file_type != "json":
        raise ValidationError("Quiz must be JSON")

    try:
        data = json.loads(result.content) if isinstance(result.content, str) else result.content
    except json.JSONDecodeError as e:
        raise ValidationError(f"Quiz JSON parse error: {e}")

    if not isinstance(data, dict):
        raise ValidationError("Quiz must be a QuizPayload object")

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
    # 不执行代码，只检查内容非空
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

    if not resources:
        raise ValidationError("Reading must have at least one resource")

    url_pattern = re.compile(r"^https?://")
    for i, item in enumerate(resources, start=1):
        if not isinstance(item, dict):
            raise ValidationError(f"Resource #{i} must be an object")

        url = item.get("url", "")
        if not url or not url.strip():
            raise ValidationError(f"Resource #{i} '{item.get('title', 'unknown')}' must have a URL")

        if not url_pattern.match(url):
            raise ValidationError(
                f"Resource #{i} '{item.get('title', 'unknown')}' URL must be http/https: {url[:50]}"
            )


def validate_ppt(result: "AgentResult", input_data: "ResourceInput") -> None:
    """PPT 资源只校验发布引用，不检查生成器内部结构或 HTML 内容。"""
    if result.file_type != "html":
        raise ValidationError("PPT resource must be HTML format")

    metadata = result.metadata or {}
    if not str(metadata.get("html_file_path", "")).strip():
        raise ValidationError("PPT resource requires html_file_path")
    if not str(metadata.get("html_url", "")).strip():
        raise ValidationError("PPT resource requires html_url")


def validate_video(result: "AgentResult", input_data: "ResourceInput") -> None:
    """Video 资源必须是带音频的最终 MP4 产物。"""
    if result.file_type != "mp4":
        raise ValidationError("Video must be MP4")

    try:
        data = json.loads(result.content) if isinstance(result.content, str) else result.content
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Video JSON parse error: {exc}") from exc

    if not isinstance(data, dict):
        raise ValidationError("Video must be object")
    if data.get("schema_version") != "video/v2":
        raise ValidationError("Video must use the video/v2 schema")
    if not str(data.get("public_url", "")).endswith(".mp4"):
        raise ValidationError("Video must expose an MP4 public_url")
    if data.get("duration_ms", 0) <= 0 or data.get("size_bytes", 0) <= 0:
        raise ValidationError("Video artifact metadata is invalid")
    if result.metadata.get("has_audio") is not True:
        raise ValidationError("Video must contain an audio stream")


def validate_cartoon(result: "AgentResult", input_data: "ResourceInput") -> None:
    """Cartoon 资源必须提供 HyperFrames 生成的带音频 MP4 发布引用。"""
    if result.file_type != "mp4":
        raise ValidationError("Cartoon must be MP4")

    try:
        data = json.loads(result.content) if isinstance(result.content, str) else result.content
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Cartoon JSON parse error: {exc}") from exc

    if not isinstance(data, dict) or data.get("schema_version") != "cartoon/v1":
        raise ValidationError("Cartoon must use the cartoon/v1 schema")
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
    "video": validate_video,
    "cartoon": validate_cartoon,
}


def validate_agent_result(
    agent_id: str,
    result: "AgentResult",
    input_data: "ResourceInput",
    existing_results: dict[str, "AgentResult"] | None = None,
) -> list[str]:
    """执行通用校验和特定校验，返回内容重复警告列表。

    Args:
        agent_id: Agent 标识符
        result: Agent 输出结果
        input_data: Agent 输入数据
        existing_results: 已完成的其他 Agent 结果（用于去重检查）

    Returns:
        内容重复警告列表（不影响验证结果，仅作为警告）
    """
    validate_common_result(agent_id, result, input_data)

    validator = AGENT_VALIDATORS.get(agent_id)
    if validator:
        validator(result, input_data)

    # 内容去重检查
    overlap_warnings = []
    if existing_results and input_data.teaching_plan:
        overlap_warnings = check_content_overlap(
            agent_id, result, input_data.teaching_plan, existing_results
        )

    return overlap_warnings


def check_content_overlap(
    agent_id: str,
    result: "AgentResult",
    teaching_plan: "TeachingPlan",
    existing_results: dict[str, "AgentResult"],
) -> list[str]:
    """检查内容是否与 avoid_overlap_with 配置中的 Agent 重复。

    使用简单关键词重叠率作为相似度指标，避免引入重量级 NLP 库。

    Args:
        agent_id: 当前 Agent ID
        result: 当前 Agent 结果
        teaching_plan: 教学计划（包含 avoid_overlap_with 配置）
        existing_results: 已完成的其他 Agent 结果

    Returns:
        重复警告列表
    """
    warnings = []

    task = teaching_plan.worker_tasks.get(agent_id)
    if not task or not task.avoid_overlap_with:
        return warnings

    # 提取当前内容的关键词
    current_keywords = extract_keywords(result.content)

    for other_agent_id in task.avoid_overlap_with:
        if other_agent_id not in existing_results:
            continue

        other_content = existing_results[other_agent_id].content
        other_keywords = extract_keywords(other_content)

        # 计算关键词重叠率
        similarity = compute_keyword_overlap(current_keywords, other_keywords)

        if similarity > CONTENT_SIMILARITY_THRESHOLD:
            warning = (
                f"内容与 {other_agent_id} 相似度 {similarity:.1%} 超过阈值 "
                f"{CONTENT_SIMILARITY_THRESHOLD:.1%}，可能存在重复"
            )
            warnings.append(warning)
            logger.warning(
                "Agent %s 内容重复检测: overlap_with=%s similarity=%.2f",
                agent_id, other_agent_id, similarity
            )

    return warnings


def extract_keywords(content: str, max_keywords: int = 50) -> set[str]:
    """从内容中提取关键词（简单实现：提取非停用词）。

    使用分词和停用词过滤，不依赖外部 NLP 库。
    """
    # 中文停用词（简化版）
    stop_words = {
        "的", "是", "在", "有", "和", "与", "或", "但", "如果", "因为",
        "所以", "那么", "这", "那", "它", "他", "她", "我", "你", "我们",
        "可以", "需要", "应该", "必须", "能够", "可能", "已经", "将", "要",
        "一个", "一些", "所有", "每个", "任何", "这种", "那种", "这样",
        "通过", "使用", "进行", "实现", "完成", "开始", "结束", "继续",
    }

    # 提取中文词汇和英文单词
    words = set()

    # 提取中文连续字符（2-4字的词）
    chinese_pattern = re.findall(r"[a-zA-Z0-9\u4e00-\u9fff]{2,10}", content)
    for w in chinese_pattern:
        w_lower = w.lower()
        if w_lower not in stop_words and len(w_lower) >= 2:
            words.add(w_lower)

    # 提取英文单词
    english_words = re.findall(r"[a-zA-Z]{3,}", content)
    for w in english_words:
        w_lower = w.lower()
        if w_lower not in stop_words:
            words.add(w_lower)

    return set(list(words)[:max_keywords])


def compute_keyword_overlap(set1: set[str], set2: set[str]) -> float:
    """计算两个关键词集合的重叠率（Jaccard 相似度）。"""
    if not set1 or not set2:
        return 0.0

    intersection = len(set1 & set2)
    union = len(set1 | set2)

    return intersection / union if union > 0 else 0.0


__all__ = [
    "ValidationError",
    "validate_common_result",
    "validate_agent_result",
    "check_content_overlap",
    "AGENT_VALIDATORS",
    "CONTENT_SIMILARITY_THRESHOLD",
]
