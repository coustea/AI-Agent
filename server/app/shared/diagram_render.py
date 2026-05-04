"""图解渲染模块。

从 LLM 返回的 Mermaid 源码中提取和验证内容，供前端渲染。
"""

from __future__ import annotations

import re
from typing import Any


# 匹配 Mermaid 代码围栏的正则表达式
_MERMAID_FENCE_RE = re.compile(r"```(?:mermaid)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)

# 匹配 Mermaid 图类型声明的正则表达式
_MERMAID_START_RE = re.compile(
    r"^\s*(flowchart|graph|sequenceDiagram|stateDiagram-v2|classDiagram|erDiagram|block-beta|packet-beta|gitGraph)\b",
    re.IGNORECASE,
)


def build_mermaid_render(source: str) -> dict[str, str]:
    """从 LLM 生成的 Mermaid 源码构建渲染 payload。

    Args:
        source: LLM 返回的 Mermaid 源码（可能包含代码围栏）。

    Returns:
        包含 engine、format、source 的渲染信息字典。
    """
    return {"engine": "mermaid", "format": "text", "source": extract_mermaid_source(source)}


def extract_mermaid_source(text: Any) -> str:
    """从 LLM 响应中提取原始 Mermaid 代码。

    模型被指示只返回 Mermaid 源码，但此函数容忍意外的代码围栏，
    同时拒绝对象格式的 payload 和纯文本响应。

    Args:
        text: LLM 返回的文本内容。

    Returns:
        清理后的 Mermaid 源码。

    Raises:
        ValueError: 如果源码为空、不是合法的 Mermaid、或返回了 JSON 对象。
    """
    raw = str(text or "").strip()
    if not raw:
        raise ValueError("Mermaid 源码为空")

    # 移除代码围栏
    fenced = _MERMAID_FENCE_RE.search(raw)
    if fenced:
        raw = fenced.group(1).strip()

    # 清理前后空白行
    lines = [line.rstrip() for line in raw.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    source = "\n".join(lines).strip()

    # 验证是否以合法的 Mermaid 关键词开头
    if not _MERMAID_START_RE.match(source):
        raise ValueError("LLM 未返回合法 Mermaid 源码")

    # 拒绝 JSON 对象格式
    if source.startswith("{") or '"type"' in source[:200]:
        raise ValueError("LLM 返回了对象数据而不是 Mermaid 源码")

    # 防御性修复：针对 LLM 容易产生的 Mermaid 语法错误进行后处理
    # 1. 修复 sequenceDiagram 中不支持的 note across: 语法，尝试退化为 note over
    if "sequenceDiagram" in source:
        # 如果发现 note across，将其退化为兼容性更好的 note over
        # note over ActorA, ActorB: message 是 Mermaid 标准语法
        source = re.sub(r"note\s+across\s+", "note over ", source, flags=re.IGNORECASE)
        # 2. 修复行尾莫名出现的 n 字符（可能是转义失败残留）
        source = re.sub(r"([^\w])n\s*$", r"\1", source, flags=re.MULTILINE)

    return source