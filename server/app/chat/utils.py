"""Chat 模块工具函数。

精简版：只保留 TutorAgent 轻量级编排器需要的辅助函数。
"""

from __future__ import annotations

import json
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage

from app.infra.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Prompt 加载
# ---------------------------------------------------------------------------

def load_prompts(agent_dir: Path) -> dict[str, str]:
    """从 prompt.md 读取提示词，按 ## 标题拆分为区段。

    Args:
        agent_dir: Agent 所在目录路径。

    Returns:
        包含各提示词区段的字典。
    """
    prompt_path = agent_dir / "prompt.md"
    content = prompt_path.read_text(encoding="utf-8")
    sections: dict[str, str] = {}
    current = None
    for line in content.split("\n"):
        stripped = line.strip()
        # 识别区段标题 (## xxx)
        if stripped.startswith("## "):
            current = stripped[3:].strip()
            sections[current] = ""
            continue
        # 追加到当前区段
        if current:
            sections[current] += line + "\n"
    return sections


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
    extra_str = " ".join(f"{k}={v}" for k, v in extra.items())
    logger.debug("[TutorAgent] 节点进入 %s %s", node_name, extra_str)
    start = time.monotonic()
    try:
        yield
    finally:
        elapsed = int((time.monotonic() - start) * 1000)
        logger.debug("[TutorAgent] 节点退出 %s 耗时%dms", node_name, elapsed)


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
    normalized = (text or "").strip()
    if not normalized:
        return True
    # 排除生成时间标记
    if normalized in {"生成时间：", "生成时间:", "更新时间：", "更新时间:"}:
        return True
    if normalized.startswith("生成时间") and len(normalized) <= 16:
        return True
    # 过短的回复视为无效
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
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            # 移除附件标记
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
    # 过滤掉已有的系统消息
    pure = [msg for msg in messages if not isinstance(msg, SystemMessage)]
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
    return state.get("route", "direct")


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
