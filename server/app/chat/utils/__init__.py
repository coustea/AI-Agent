"""Chat 工具函数 — 节点计时、消息构建、路由判断、SSE 事件构造。"""

from __future__ import annotations

import json
import time
from contextlib import contextmanager
from typing import Any, Generator

from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage

from app.infra.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 节点计时
# ---------------------------------------------------------------------------

@contextmanager
def node_timer(node_name: str, **extra: Any) -> Generator[None, None, None]:
    """节点计时上下文管理器。

    用于记录 LangGraph 节点的执行耗时，便于性能分析。

    Args:
        node_name: 节点名称。
        **extra: 额外的日志字段。

    Yields:
        无返回值。
    """
    # 将额外参数格式化为 "key=value" 字符串，便于日志追踪
    extra_str = " ".join(f"{k}={v}" for k, v in extra.items())
    logger.debug("[ChatRuntime] 节点进入 %s %s", node_name, extra_str)
    # 使用 monotonic 高精度计时，不受系统时间修改影响
    start = time.monotonic()
    try:
        yield
    finally:
        # 计算毫秒级耗时，用于性能分析和慢节点告警
        elapsed = int((time.monotonic() - start) * 1000)
        logger.debug("[ChatRuntime] 节点退出 %s 耗时%dms", node_name, elapsed)


# ---------------------------------------------------------------------------
# 字符串 / 文本处理
# ---------------------------------------------------------------------------

def normalize_message_content(content: Any) -> str:
    """将 LLM 输出统一转为字符串。

    Args:
        content: LLM 返回的内容，可能是字符串或其他类型。

    Returns:
        字符串形式的内容。
    """
    if content is None:
        return ""
    return content if isinstance(content, str) else str(content)


def truncate(value: Any, max_chars: int = 400) -> str:
    """截断任意值到指定字符数。

    用于日志输出时避免过长内容。

    Args:
        value: 要截断的值。
        max_chars: 最大字符数。

    Returns:
        截断后的字符串，超出部分用 "..." 标记。
    """
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    # 将换行符替换为空格
    text = text.replace("\n", " ").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


def is_unusable_reply_text(text: str) -> bool:
    """检测 LLM 返回的文本是否属于"无效回复"。

    无效回复包括：空字符串、过短文本、生成时间标记等。

    Args:
        text: LLM 返回的文本。

    Returns:
        True 表示无效回复，需要重试或降级。
    """
    # 统一为空白处理，去除首尾空格
    normalized = (text or "").strip()
    if not normalized:
        return True
    # 排除生成时间标记 — LLM 有时会错误输出时间戳而非实际内容
    if normalized in {"生成时间：", "生成时间:", "更新时间：", "更新时间:"}:
        return True
    # 匹配以"生成时间"开头且长度极短的文本（如"生成时间：2024-01-01"）
    if normalized.startswith("生成时间") and len(normalized) <= 16:
        return True
    # 少于 8 个字符的回复大概率不包含有效教学内容，视为无效
    if len(normalized) < 8:
        return True
    return False


# ---------------------------------------------------------------------------
# 消息构建
# ---------------------------------------------------------------------------

def extract_question(messages: list[AnyMessage]) -> str:
    """从消息列表中提取用户最近的一条纯文本问题。

    移除附件标记（[Attached Images:]、[Attached Files:] 等）。

    Args:
        messages: 消息列表。

    Returns:
        用户问题的纯文本，未找到则返回空字符串。
    """
    # 从后向前遍历，找到最近一条用户消息（支持多轮对话）
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            # 移除附件标记 — 前端会在消息末尾附加 [Attached Images:...] 等占位符
            return (
                content.split(" [Attached Images:")[0]
                .split(" [Attached Image:")[0]
                .split(" [Attached Files:")[0]
                .strip()
            )
    return ""


def build_messages(system_prompt: str, messages: list[AnyMessage]) -> list[AnyMessage]:
    """将系统提示词拼接到消息列表头部。

    确保消息列表中只有一个系统消息。

    Args:
        system_prompt: 系统提示词。
        messages: 原始消息列表。

    Returns:
        以系统消息开头的消息列表。
    """
    # 先移除消息列表中已有的系统消息，确保最终只有一条系统消息
    pure = [msg for msg in messages if not isinstance(msg, SystemMessage)]
    # 将新的系统提示词作为首条消息注入
    return [SystemMessage(content=system_prompt)] + pure


# ---------------------------------------------------------------------------
# 路由判断
# ---------------------------------------------------------------------------

def classify_route(state: dict) -> str:
    """LangGraph 条件路由：根据 classify 节点的结果选择路径。

    Args:
        state: LangGraph 状态字典。

    Returns:
        路由目标节点名称。
    """
    # 从状态中读取 classify 节点输出的路由类型，默认 direct（直接回答）
    route = state.get("route", "direct")
    # 白名单校验，防止非法路由值导致图执行异常
    valid_routes = {"direct", "search", "attachment_needed"}
    return route if route in valid_routes else "direct"


# ---------------------------------------------------------------------------
# SSE 事件
# ---------------------------------------------------------------------------

def stream_event(event: str, data: Any) -> dict[str, Any]:
    """构造 SSE 事件对象。

    Args:
        event: 事件类型名称。
        data: 事件数据。

    Returns:
        包含 event 和 data 字段的字典。
    """
    return {"event": event, "data": data}
