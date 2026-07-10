"""Chat 工具函数 — 消息构建、文本处理。

核心函数：
  normalize_message_content — 将 LLM 输出统一转为字符串
  compact_text — 截断过长文本，防止撑爆 LLM 上下文窗口
  truncate — 截断任意值到指定字符数（日志用）
  is_unusable_reply_text — 检测 LLM 返回的文本是否属于无效回复
  extract_question — 从消息列表中提取用户最近的一条纯文本问题
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AnyMessage, HumanMessage


# ---------------------------------------------------------------------------
# 字符串 / 文本处理
# ---------------------------------------------------------------------------

# 将 LLM 输出统一转为字符串（None 为空串，其余强转）
def normalize_message_content(content: Any) -> str:
    """将 LLM 输出统一转为字符串。"""
    if content is None:
        return ""
    return content if isinstance(content, str) else str(content)


# 截断过长文本，防止撑爆 LLM 上下文窗口
def compact_text(text: str, *, limit: int = 3500) -> str:
    """截断过长文本，防止撑爆 LLM 上下文窗口。"""
    value = str(text or "").strip()
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


# 截断任意值为指定字符数的字符串（用于日志）
def truncate(value: Any, max_chars: int = 400) -> str:
    """截断任意值到指定字符数。"""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    text = text.replace("\n", " ").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


# 检测 LLM 返回文本是否为无效回复（空/时间标记/过短）
def is_unusable_reply_text(text: str) -> bool:
    """检测 LLM 返回的文本是否属于无效回复。"""
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

# 从消息列表中提取用户最近的一条纯文本问题（剥离附件标记）
def extract_question(messages: list[AnyMessage]) -> str:
    """从消息列表中提取用户最近的一条纯文本问题。"""
    # 倒序查找最近一条 HumanMessage 并剥离附件标记
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
