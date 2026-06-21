"""将通用工具运行事件转换为前端可展示的辅导状态。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


_TOOL_ACTIONS: dict[str, str] = {
    "get_learner_profile": "正在了解你的学习情况",
    "get_long_term_memory": "正在回顾学习记录",
    "search_knowledge_base": "正在检索课程知识库",
    "duckduckgo_search": "正在搜索相关资料",
    "duckduckgo_instant_answer": "正在查询即时答案",
    "tavily_search": "正在搜索相关资料",
    "spark_search": "正在搜索相关资料",
    "open_web_page": "正在阅读网页",
    "find_in_web_page": "正在网页中查找内容",
    "extract_web_links": "正在提取网页链接",
    "read_web_pdf": "正在阅读 PDF",
}


def _preview(value: Any, *, limit: int = 50) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _result_preview(value: Any, *, limit: int = 500) -> str:
    if isinstance(value, Mapping):
        value = value.get("text") or value.get("message") or value
    return _preview(value, limit=limit)


def _tool_context(tool_name: str, arguments: Mapping[str, Any]) -> str:
    keys = {
        "get_learner_profile": ("dimension", "course_name"),
        "get_long_term_memory": ("category",),
        "search_knowledge_base": ("query", "course_name"),
        "duckduckgo_search": ("query",),
        "duckduckgo_instant_answer": ("query",),
        "tavily_search": ("query",),
        "spark_search": ("query",),
        "open_web_page": ("url",),
        "find_in_web_page": ("pattern", "page_id"),
        "extract_web_links": ("page_id",),
        "read_web_pdf": ("url",),
    }.get(tool_name, ())
    for key in keys:
        value = _preview(arguments.get(key))
        if value:
            return f"「{value}」"
    return ""


def build_agent_status_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """构建单条、无敏感参数的前端工具状态。"""
    status = str(event.get("status") or "running")
    tool_name = str(event.get("tool_name") or "").strip()
    raw_arguments = event.get("arguments")
    arguments = raw_arguments if isinstance(raw_arguments, Mapping) else {}
    context = _tool_context(tool_name, arguments)
    output = _result_preview(event.get("result"))
    error = _preview(event.get("error"), limit=200)
    action = _TOOL_ACTIONS.get(tool_name, "正在调用工具")
    title = action.removeprefix("正在")

    if status == "done":
        message = f"{title}已完成"
    elif status == "failed":
        message = f"{title}未完成"
    else:
        message = f"{action}{context}..."

    return {
        "activity_id": str(event.get("activity_id") or "").strip(),
        "kind": "tool",
        "stage": "tool_running",
        "status": status,
        "tool_name": tool_name,
        "title": title,
        "summary": context.strip("「」"),
        "message": message,
        "detail": {
            "tool_name": tool_name,
            "input": context.strip("「」"),
            "output": output,
            "error": error,
            "duration_ms": event.get("duration_ms"),
        },
    }


def build_attachment_status_payload(
    *,
    activity_id: str,
    status: str,
    file_names: list[str],
    analysis_type: str,
    summary: str = "",
    error: str = "",
) -> dict[str, Any]:
    """构建附件分析活动，供实时事件和历史记录复用。"""
    label = "图片分析" if analysis_type == "image" else "文档分析"
    names = "、".join(name for name in file_names if name) or "附件"
    if status == "running":
        message = f"正在进行{label}：{_preview(names)}..."
    elif status == "failed":
        message = f"{label}未完成"
    else:
        message = f"{label}已完成"
    return {
        "activity_id": activity_id,
        "kind": "attachment",
        "stage": "attachment_analysis",
        "status": status,
        "title": label,
        "summary": _preview(names),
        "message": message,
        "detail": {
            "analysis_type": analysis_type,
            "files": file_names,
            "output": _preview(summary, limit=1000),
            "error": _preview(error, limit=200),
            "duration_ms": None,
        },
    }


def build_persisted_tool_activity(invocation: Any) -> dict[str, Any]:
    """把已落库的工具调用恢复为前端活动卡数据。"""
    status = "failed" if str(getattr(invocation, "status", "")) == "error" else "done"
    return build_agent_status_payload({
        "activity_id": getattr(invocation, "tool_call_id", ""),
        "status": status,
        "tool_name": getattr(invocation, "tool_name", ""),
        "arguments": getattr(invocation, "arguments_json", None) or {},
        "result": getattr(invocation, "result_text", ""),
    })
