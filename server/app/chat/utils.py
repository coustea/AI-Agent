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
    """从 prompt.md 读取提示词，按 ## 标题拆分为 classifier / direct_system / tool_system 三个区段。"""
    prompt_path = agent_dir / "prompt.md"
    content = prompt_path.read_text(encoding="utf-8")
    sections: dict[str, str] = {"classifier": "", "direct_system": "", "tool_system": ""}
    current = None
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## classifier"):
            current = "classifier"
            continue
        if stripped.startswith("## direct_system"):
            current = "direct_system"
            continue
        if stripped.startswith("## tool_system"):
            current = "tool_system"
            continue
        if current:
            sections[current] += line + "\n"
    return sections


# ---------------------------------------------------------------------------
# 节点计时
# ---------------------------------------------------------------------------

@contextmanager
def node_timer(node_name: str, **extra: Any) -> Generator[None, None, None]:
    """节点计时上下文管理器。"""
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
    """将 LLM 输出统一转为字符串。"""
    if content is None:
        return ""
    return content if isinstance(content, str) else str(content)


def truncate(value: Any, max_chars: int = 400) -> str:
    """截断任意值到指定字符数。"""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    text = text.replace("\n", " ").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


def is_unusable_reply_text(text: str) -> bool:
    """检测 LLM 返回的文本是否属于"无效回复"。"""
    normalized = (text or "").strip()
    if not normalized:
        return True
    if normalized in {"生成时间：", "生成时间:", "更新时间：", "更新时间:"}:
        return True
    if normalized.startswith("生成时间") and len(normalized) <= 16:
        return True
    if len(normalized) < 8:
        return True
    return False


# ---------------------------------------------------------------------------
# 消息构建
# ---------------------------------------------------------------------------

def extract_question(messages: list[AnyMessage]) -> str:
    """从消息列表中提取用户最近的一条纯文本问题。"""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            return (
                content.split(" [Attached Images:")[0]
                .split(" [Attached Image:")[0]
                .split(" [Attached Files:")[0]
                .strip()
            )
    return ""


def build_messages(system_prompt: str, messages: list[AnyMessage]) -> list[AnyMessage]:
    """将系统提示词拼接到消息列表头部。"""
    pure = [msg for msg in messages if not isinstance(msg, SystemMessage)]
    return [SystemMessage(content=system_prompt)] + pure


# ---------------------------------------------------------------------------
# 路由判断
# ---------------------------------------------------------------------------

def classify_route(state: dict) -> str:
    """LangGraph 条件路由：根据 classify 节点的结果选择路径。"""
    return state.get("route", "direct")


def guard_route(state: dict) -> str:
    """LangGraph 条件路由：根据 last_guard_decision 选择下一步节点。"""
    return state.get("last_guard_decision", "end")


# ---------------------------------------------------------------------------
# SSE 事件
# ---------------------------------------------------------------------------

def stream_event(event: str, data: Any) -> dict[str, Any]:
    """构造 SSE 事件对象。"""
    return {"event": event, "data": data}
