"""图解渲染模块。

将结构化图解数据转换为 Mermaid 语法，供前端渲染。
"""

from __future__ import annotations

import re
from typing import Any


# 匹配非安全字符的正则表达式，用于生成合法的 Mermaid 节点ID
_SAFE_ID_RE = re.compile(r"[^0-9A-Za-z_]")


def build_diagram_render(diagram: dict[str, Any]) -> dict[str, str]:
    """构建图解渲染结果。

    Args:
        diagram: 结构化图解数据，包含 type 和 spec 字段。

    Returns:
        包含 engine、format、source 的渲染信息字典。
    """
    source = _build_mermaid_source(diagram)
    return {"engine": "mermaid", "format": "text", "source": source}


def _build_mermaid_source(diagram: dict[str, Any]) -> str:
    """根据图解类型构建 Mermaid 源码。

    Args:
        diagram: 结构化图解数据。

    Returns:
        Mermaid 语法的图解源码。

    Raises:
        ValueError: 不支持的图解类型。
    """
    diagram_type = diagram.get("type")
    spec = diagram.get("spec") or {}

    # 根据类型分发到对应的构建函数
    if diagram_type == "sequence":
        return _build_sequence(spec)
    if diagram_type == "flow":
        return _build_flow(spec)
    if diagram_type == "state":
        return _build_state(spec)
    if diagram_type == "relation":
        return _build_relation(spec)
    if diagram_type == "hierarchy":
        return _build_hierarchy(spec)
    if diagram_type == "compare":
        return _build_compare(spec)

    raise ValueError(f"unsupported diagram type: {diagram_type!r}")


def _build_sequence(spec: dict[str, Any]) -> str:
    """构建时序图 Mermaid 源码。

    Args:
        spec: 时序图规格，包含 actors 和 messages。

    Returns:
        sequenceDiagram 语法的 Mermaid 源码。
    """
    lines = ["sequenceDiagram"]
    # 声明参与者
    for actor in spec.get("actors", []):
        lines.append(f"    participant {_node_id(actor.get('id'))} as {_label(actor)}")

    # 声明消息
    for message in spec.get("messages", []):
        source = _node_id(message.get("from"))
        target = _node_id(message.get("to"))
        lines.append(f"    {source}->>{target}: {_plain_text(message.get('label'))}")

    return "\n".join(lines)


def _build_flow(spec: dict[str, Any]) -> str:
    """构建流程图 Mermaid 源码。

    Args:
        spec: 流程图规格，包含 steps 和 edges。

    Returns:
        flowchart TD 语法的 Mermaid 源码。
    """
    lines = ["flowchart TD"]
    # 声明步骤节点
    for step in spec.get("steps", []):
        node_id = _node_id(step.get("id"))
        lines.append(f"    {node_id}[{_label(step)}]")

    # 声明边
    for edge in spec.get("edges", []):
        lines.append(_edge_line(edge))

    return "\n".join(lines)


def _build_state(spec: dict[str, Any]) -> str:
    """构建状态图 Mermaid 源码。

    Args:
        spec: 状态图规格，包含 states 和 transitions。

    Returns:
        stateDiagram-v2 语法的 Mermaid 源码。
    """
    lines = ["stateDiagram-v2"]
    # 声明状态
    for state in spec.get("states", []):
        lines.append(f"    state {_label(state)} as {_node_id(state.get('id'))}")

    # 声明转换
    for transition in spec.get("transitions", []):
        source = _node_id(transition.get("from"))
        target = _node_id(transition.get("to"))
        label = _plain_text(transition.get("label"))
        lines.append(f"    {source} --> {target}: {label}")

    return "\n".join(lines)


def _build_relation(spec: dict[str, Any]) -> str:
    """构建关系图 Mermaid 源码。

    Args:
        spec: 关系图规格，包含 nodes 和 edges。

    Returns:
        graph TD 语法的 Mermaid 源码。
    """
    lines = ["graph TD"]
    # 声明节点
    for node in spec.get("nodes", []):
        node_id = _node_id(node.get("id"))
        lines.append(f"    {node_id}[{_label(node)}]")

    # 声明边
    for edge in spec.get("edges", []):
        lines.append(_edge_line(edge))

    return "\n".join(lines)


def _build_hierarchy(spec: dict[str, Any]) -> str:
    """构建层级结构图 Mermaid 源码。

    Args:
        spec: 层级结构规格，包含 root 节点。

    Returns:
        graph TD 语法的 Mermaid 源码。
    """
    lines = ["graph TD"]
    root = spec.get("root") or {}
    if root:
        _append_hierarchy_node(lines, root)
    return "\n".join(lines)


def _append_hierarchy_node(lines: list[str], node: dict[str, Any]) -> None:
    """递归追加层级节点到行列表。

    Args:
        lines: Mermaid 源码行列表。
        node: 当前层级节点。
    """
    parent_id = _node_id(node.get("id"))
    lines.append(f"    {parent_id}[{_label(node)}]")
    # 递归处理子节点
    for child in node.get("children", []):
        child_id = _node_id(child.get("id"))
        _append_hierarchy_node(lines, child)
        lines.append(f"    {parent_id} --> {child_id}")


def _build_compare(spec: dict[str, Any]) -> str:
    """构建对比图 Mermaid 源码。

    Args:
        spec: 对比图规格，包含 items 列表。

    Returns:
        flowchart LR 语法的 Mermaid 源码。
    """
    lines = ["flowchart LR"]
    previous_id: str | None = None
    # 声明对比项节点，使用隐形连接符 ~~~ 保持水平排列
    for index, item in enumerate(spec.get("items", []), start=1):
        node_id = f"item_{index}"
        lines.append(f"    {node_id}[{_compare_label(item)}]")
        if previous_id is not None:
            lines.append(f"    {previous_id} ~~~ {node_id}")
        previous_id = node_id

    return "\n".join(lines)


def _edge_line(edge: dict[str, Any]) -> str:
    """构建边的 Mermaid 语法行。

    Args:
        edge: 边数据，包含 source、target、label。

    Returns:
        边的 Mermaid 语法行。
    """
    source = _node_id(edge.get("source"))
    target = _node_id(edge.get("target"))
    label = _plain_text(edge.get("label"))
    if label:
        return f"    {source} -->|{label}| {target}"
    return f"    {source} --> {target}"


def _node_id(value: Any) -> str:
    """生成合法的 Mermaid 节点ID。

    将非字母数字下划线字符替换为下划线，确保不以数字开头。

    Args:
        value: 原始节点ID值。

    Returns:
        合法的 Mermaid 节点ID。
    """
    text = str(value or "node")
    text = _SAFE_ID_RE.sub("_", text).strip("_")
    if not text:
        return "node"
    # Mermaid 节点ID 不能以数字开头
    if text[0].isdigit():
        return f"n_{text}"
    return text


def _label(item: dict[str, Any]) -> str:
    """构建节点的显示标签。

    合并 label 和 description 字段。

    Args:
        item: 节点数据。

    Returns:
        引号包裹的标签文本。
    """
    parts = [item.get("label"), item.get("description")]
    return _quoted_label(part for part in parts if part)


def _compare_label(item: dict[str, Any]) -> str:
    """构建对比项的显示标签。

    合并 label、description 和 points 字段。

    Args:
        item: 对比项数据。

    Returns:
        引号包裹的标签文本。
    """
    parts = [item.get("label"), item.get("description"), *item.get("points", [])]
    return _quoted_label(part for part in parts if part)


def _quoted_label(parts: Any) -> str:
    """将标签部分合并并用引号包裹。

    Args:
        parts: 标签部分的可迭代对象。

    Returns:
        引号包裹的标签文本。
    """
    text = "<br/>".join(_plain_text(part) for part in parts)
    return f'"{text}"'


def _plain_text(value: Any) -> str:
    """将值转换为纯文本。

    移除多余空白，替换可能破坏 Mermaid 语法的特殊字符。

    Args:
        value: 任意值。

    Returns:
        处理后的纯文本。
    """
    text = str(value or "")
    # 合并连续空白为单个空格
    text = re.sub(r"\s+", " ", text).strip()
    # 替换可能破坏 Mermaid 语法的字符
    return (
        text.replace('"', "'")
        .replace("[", "(")
        .replace("]", ")")
        .replace("{", "(")
        .replace("}", ")")
    )
