"""
Worker Agent 工具函数集合。

包含：
- Markdown 清理工具
- 执行报告生成工具
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from app.infra.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Markdown 清理工具
# =============================================================================

# Markdown 代码块匹配
_MARKDOWN_FENCE_RE = re.compile(r"```(?:markdown|md)?\s*\n(.*?)\n```", re.DOTALL | re.IGNORECASE)


def extract_markdown_from_llm_output(content: str) -> str:
    """从 LLM 输出中提取 Markdown 内容。

    Args:
        content: LLM 返回的原始内容

    Returns:
        提取并规范化后的 Markdown 文本
    """
    raw = (content or "").strip()
    if not raw:
        return ""

    # 尝试从代码块中提取
    match = _MARKDOWN_FENCE_RE.search(raw)
    if match:
        raw = match.group(1).strip()

    return _normalize_markdown_indent(raw)


def _normalize_markdown_indent(markdown_text: str) -> str:
    """规范化 Markdown 缩进，确保一级分支顶格。"""
    lines = markdown_text.splitlines()
    bullet_indents = [
        len(line) - len(line.lstrip(" "))
        for line in lines
        if line.lstrip(" ").startswith("- ")
    ]
    if not bullet_indents:
        return markdown_text.strip()

    min_indent = min(bullet_indents)
    if min_indent == 0:
        return markdown_text.strip()

    normalized = []
    for line in lines:
        if line.startswith(" " * min_indent):
            normalized.append(line[min_indent:])
        else:
            normalized.append(line)
    return "\n".join(normalized).strip()


# =============================================================================
# 执行报告生成工具
# =============================================================================

def generate_execution_report(
    agent_type: str,
    task: dict[str, Any],
    content: str | dict[str, Any] | None,
    success: bool = True,
    error: str | None = None,
) -> str:
    """生成 Agent 执行报告。

    Args:
        agent_type: Agent 类型（如 "content", "mindmap", "diagram"）
        task: 任务信息
        content: 生成的内容
        success: 是否成功
        error: 错误信息

    Returns:
        Markdown 格式的执行报告
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    if not success:
        return _generate_failure_report(agent_type, task, error or "未知错误", timestamp)

    return _generate_success_report(agent_type, task, content, timestamp)


def _generate_failure_report(
    agent_type: str,
    task: dict[str, Any],
    error: str,
    timestamp: str,
) -> str:
    """生成失败报告。"""
    lines = [
        f"# {agent_type} Agent 执行报告",
        "",
        f"**执行状态**: ❌ 失败",
        f"**执行时间**: {timestamp}",
        "",
        "## 任务信息",
        "",
        f"- **课程主题**: {task.get('course', '未知')}",
        f"- **学习主题**: {task.get('topic', task.get('gap', '未知'))}",
        f"- **学习目标**: {task.get('learning_goal', task.get('need', 'review'))}",
        "",
        "## 错误信息",
        "",
        f"```\n{error}\n```",
        "",
        "## 影响",
        "",
        f"由于 {agent_type} Agent 执行失败，依赖此产物的后续 Agent 可能无法正常执行。",
    ]
    return "\n".join(lines)


def _generate_success_report(
    agent_type: str,
    task: dict[str, Any],
    content: str | dict[str, Any] | None,
    timestamp: str,
) -> str:
    """生成成功报告。"""
    content_preview = ""
    if content:
        if isinstance(content, dict):
            content_preview = f"```json\n{content}\n```"
        else:
            preview = str(content)[:500]
            if len(str(content)) > 500:
                preview += "..."
            content_preview = preview

    lines = [
        f"# {agent_type} Agent 执行报告",
        "",
        f"**执行状态**: ✅ 成功",
        f"**执行时间**: {timestamp}",
        "",
        "## 任务信息",
        "",
        f"- **课程主题**: {task.get('course', '未知')}",
        f"- **学习主题**: {task.get('topic', task.get('gap', '未知'))}",
        f"- **学习目标**: {task.get('learning_goal', task.get('need', 'review'))}",
        "",
        "## 执行摘要",
        "",
        f"{agent_type} Agent 成功完成资源生成任务。",
        "",
        "## 内容预览",
        "",
        content_preview or "无内容",
        "",
        "---",
        "",
        "*此报告由系统自动生成。*",
    ]
    return "\n".join(lines)
