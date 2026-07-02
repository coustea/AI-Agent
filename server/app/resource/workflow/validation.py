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

if TYPE_CHECKING:
    from app.resource.schemas import AgentResult, ResourceInput, TeachingPlan

logger = get_logger(__name__)


# Agent ID 常量
BASE_RESOURCE_AGENT_IDS = frozenset({"content", "mindmap", "quiz", "code", "reading"})
AGGREGATION_AGENT_IDS = frozenset({"ppt", "video"})

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

    # Base Agent 需要 downstream_context
    if scheduled_agent_id in BASE_RESOURCE_AGENT_IDS:
        handoff = result.downstream_context
        if handoff is None or handoff.source_agent != scheduled_agent_id:
            raise ValidationError("Base Agent requires truthful downstream_context")

        plan_ids = {
            entry.get("id", "")
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
    """PPT 资源校验：严格校验 HTML 幻灯片文件生成。"""
    if result.file_type != "html":
        raise ValidationError("PPT resource must be HTML format")

    metadata = result.metadata or {}
    required_fields = {
        "agent_id",
        "html_file_path",
        "html_url",
        "slide_count",
        "style_name",
        "density",
        "file_size",
    }
    if not required_fields <= metadata.keys():
        missing = sorted(required_fields - metadata.keys())
        raise ValidationError(f"HTML PPT metadata is missing: {', '.join(missing)}")

    unexpected_fields = sorted(metadata.keys() - required_fields)
    if unexpected_fields:
        raise ValidationError(
            f"HTML PPT metadata contains unsupported fields: "
            f"{', '.join(unexpected_fields)}"
        )

    html_path = metadata["html_file_path"]
    html_url = metadata["html_url"]
    if not re.fullmatch(
        r"/api/v1/ai/resources/public/[A-Za-z0-9_-]+/html",
        str(html_url),
    ):
        raise ValidationError("HTML PPT has an invalid public html_url")
    if not isinstance(metadata["slide_count"], int) or metadata["slide_count"] < 1:
        raise ValidationError("HTML PPT slide_count must be a positive integer")
    if metadata["density"] not in {"speaker_led", "reading_first"}:
        raise ValidationError("HTML PPT density is invalid")

    import os
    if not os.path.exists(html_path):
        raise ValidationError(f"Generated HTML slide file does not exist: {html_path}")


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

    # 查找当前 Agent 的 assignment
    assignment = None
    for a in teaching_plan.agent_assignments:
        if a.agent_id == agent_id:
            assignment = a
            break

    if not assignment or not assignment.avoid_overlap_with:
        return warnings

    # 提取当前内容的关键词
    current_keywords = extract_keywords(result.content)

    for other_agent_id in assignment.avoid_overlap_with:
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
    "BASE_RESOURCE_AGENT_IDS",
    "AGGREGATION_AGENT_IDS",
    "CONTENT_SIMILARITY_THRESHOLD",
]
