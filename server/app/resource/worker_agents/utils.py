"""
Worker Agent 工具函数集合。
"""

from __future__ import annotations

import re
from typing import Any


# Markdown 代码块匹配
_MARKDOWN_FENCE_RE = re.compile(r"```(?:markdown|md)?\s*\n(.*?)\n```", re.DOTALL | re.IGNORECASE)


def extract_markdown_from_llm_output(content: str) -> str:
    """从 LLM 输出中提取 Markdown 内容。"""
    raw = (content or "").strip()
    if not raw:
        return ""

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


def format_dependency_reports_for_prompt(dependency_reports: dict[str, Any] | None) -> str:
    """Format compact upstream execution reports for downstream agent prompts."""
    if not dependency_reports:
        return ""

    sections: list[str] = []
    for agent, report in dependency_reports.items():
        if not report:
            continue
        sections.append(f"### {agent}")
        sections.append(str(report).strip())
    return "\n".join(sections).strip()


def format_upstream_results_for_prompt(
    upstream_results: dict[str, Any] | None,
    *,
    skip_agents: dict[str, Any] | None = None,
    max_chars_per_agent: int = 900,
) -> str:
    """Format short upstream result previews without flooding the prompt."""
    if not upstream_results:
        return ""

    skipped = set((skip_agents or {}).keys())
    sections: list[str] = []
    for agent, result in upstream_results.items():
        if agent in skipped:
            continue
        preview = _preview_value(result, max_chars=max_chars_per_agent)
        if not preview:
            continue
        sections.append(f"### {agent}")
        sections.append(preview)
    return "\n".join(sections).strip()


def _preview_value(value: Any, *, max_chars: int) -> str:
    if isinstance(value, dict):
        for key in ("summary", "execution_report", "title", "content"):
            if key in value and value[key]:
                return _preview_value(value[key], max_chars=max_chars)
        return str(value)[:max_chars].strip()
    if isinstance(value, list):
        return str(value[:3])[:max_chars].strip()
    return str(value or "")[:max_chars].strip()


def format_learner_profile_for_prompt(learner_profile: dict[str, Any] | None) -> str:
    """Format backend-loaded learner profile for worker prompts."""
    if not learner_profile:
        return ""

    profile_markdown = str(learner_profile.get("profile_markdown") or "").strip()
    if profile_markdown:
        return profile_markdown

    lines: list[str] = []
    for key, label in (
        ("major", "专业"),
        ("grade", "年级"),
        ("school", "学校"),
        ("current_focus", "当前关注"),
        ("learning_style", "学习偏好"),
    ):
        value = learner_profile.get(key)
        if value:
            lines.append(f"- {label}: {value}")
    return "\n".join(lines).strip()


def append_backend_context_for_prompt(parts: list[str], state: Any) -> None:
    """Append backend-only context that is not part of the frontend request body."""
    profile_text = format_learner_profile_for_prompt(getattr(state, "learner_profile", {}))
    if profile_text:
        parts.extend(["", "## 学习者画像", profile_text])

    dependency_report_text = format_dependency_reports_for_prompt(getattr(state, "dependency_reports", {}))
    if dependency_report_text:
        parts.extend(["", "## 依赖交接报告", dependency_report_text])

    upstream_preview = format_upstream_results_for_prompt(
        getattr(state, "upstream_results", {}),
        skip_agents=getattr(state, "dependency_reports", {}),
    )
    if upstream_preview:
        parts.extend(["", "## 上游结果摘要", upstream_preview])


def learning_need_from_task(task: dict[str, Any]) -> str:
    """Return the frontend natural-language learning need from a worker task."""
    return str(task.get("learning_need") or "未说明").strip() or "未说明"


def title_from_learning_need(task: dict[str, Any], suffix: str, *, max_chars: int = 32) -> str:
    """Build a stable resource title from the frontend learning_need only."""
    learning_need = learning_need_from_task(task)
    if len(learning_need) > max_chars:
        learning_need = f"{learning_need[:max_chars]}..."
    return f"{learning_need} - {suffix}"
