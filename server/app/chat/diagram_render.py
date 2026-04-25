from __future__ import annotations

import re
from typing import Any


_SAFE_ID_RE = re.compile(r"[^0-9A-Za-z_]")


def build_diagram_render(diagram: dict[str, Any]) -> dict[str, str]:
    source = _build_mermaid_source(diagram)
    return {"engine": "mermaid", "format": "text", "source": source}


def _build_mermaid_source(diagram: dict[str, Any]) -> str:
    diagram_type = diagram.get("type")
    spec = diagram.get("spec") or {}

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
    lines = ["sequenceDiagram"]
    for actor in spec.get("actors", []):
        lines.append(f"    participant {_node_id(actor.get('id'))} as {_label(actor)}")

    for message in spec.get("messages", []):
        source = _node_id(message.get("from"))
        target = _node_id(message.get("to"))
        lines.append(f"    {source}->>{target}: {_plain_text(message.get('label'))}")

    return "\n".join(lines)


def _build_flow(spec: dict[str, Any]) -> str:
    lines = ["flowchart TD"]
    for step in spec.get("steps", []):
        node_id = _node_id(step.get("id"))
        lines.append(f"    {node_id}[{_label(step)}]")

    for edge in spec.get("edges", []):
        lines.append(_edge_line(edge))

    return "\n".join(lines)


def _build_state(spec: dict[str, Any]) -> str:
    lines = ["stateDiagram-v2"]
    for state in spec.get("states", []):
        lines.append(f"    state {_label(state)} as {_node_id(state.get('id'))}")

    for transition in spec.get("transitions", []):
        source = _node_id(transition.get("from"))
        target = _node_id(transition.get("to"))
        label = _plain_text(transition.get("label"))
        lines.append(f"    {source} --> {target}: {label}")

    return "\n".join(lines)


def _build_relation(spec: dict[str, Any]) -> str:
    lines = ["graph TD"]
    for node in spec.get("nodes", []):
        node_id = _node_id(node.get("id"))
        lines.append(f"    {node_id}[{_label(node)}]")

    for edge in spec.get("edges", []):
        lines.append(_edge_line(edge))

    return "\n".join(lines)


def _build_hierarchy(spec: dict[str, Any]) -> str:
    lines = ["graph TD"]
    root = spec.get("root") or {}
    if root:
        _append_hierarchy_node(lines, root)
    return "\n".join(lines)


def _append_hierarchy_node(lines: list[str], node: dict[str, Any]) -> None:
    parent_id = _node_id(node.get("id"))
    lines.append(f"    {parent_id}[{_label(node)}]")
    for child in node.get("children", []):
        child_id = _node_id(child.get("id"))
        _append_hierarchy_node(lines, child)
        lines.append(f"    {parent_id} --> {child_id}")


def _build_compare(spec: dict[str, Any]) -> str:
    lines = ["flowchart LR"]
    previous_id: str | None = None
    for index, item in enumerate(spec.get("items", []), start=1):
        node_id = f"item_{index}"
        lines.append(f"    {node_id}[{_compare_label(item)}]")
        if previous_id is not None:
            lines.append(f"    {previous_id} ~~~ {node_id}")
        previous_id = node_id

    return "\n".join(lines)


def _edge_line(edge: dict[str, Any]) -> str:
    source = _node_id(edge.get("source"))
    target = _node_id(edge.get("target"))
    label = _plain_text(edge.get("label"))
    if label:
        return f"    {source} -->|{label}| {target}"
    return f"    {source} --> {target}"


def _node_id(value: Any) -> str:
    text = str(value or "node")
    text = _SAFE_ID_RE.sub("_", text).strip("_")
    if not text:
        return "node"
    if text[0].isdigit():
        return f"n_{text}"
    return text


def _label(item: dict[str, Any]) -> str:
    parts = [item.get("label"), item.get("description")]
    return _quoted_label(part for part in parts if part)


def _compare_label(item: dict[str, Any]) -> str:
    parts = [item.get("label"), item.get("description"), *item.get("points", [])]
    return _quoted_label(part for part in parts if part)


def _quoted_label(parts: Any) -> str:
    text = "<br/>".join(_plain_text(part) for part in parts)
    return f'"{text}"'


def _plain_text(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"\s+", " ", text).strip()
    return (
        text.replace('"', "'")
        .replace("[", "(")
        .replace("]", ")")
        .replace("{", "(")
        .replace("}", ")")
    )
