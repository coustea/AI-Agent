from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.chat.schemas import (
    DIAGRAM_MODEL_MAP,
    DiagramRender,
    FlowDiagram,
    HierarchyDiagram,
    RelationDiagram,
    SequenceDiagram,
    StateDiagram,
)
from app.chat.utils import load_prompts


def test_diagram_model_map_exports_all_supported_types() -> None:
    assert set(DIAGRAM_MODEL_MAP) == {
        "hierarchy",
        "flow",
        "compare",
        "relation",
        "sequence",
        "state",
        "class",
        "er",
        "block",
        "packet",
        "git",
        "activity",
        "usecase",
        "component",
        "package",
        "deployment",
        "object",
        "communication",
    }


def test_diagram_prompts_require_json_output() -> None:
    prompts = load_prompts(Path(__file__).resolve().parents[2] / "app" / "chat")

    decision_prompt = prompts["diagram_decision_system"]
    generation_prompt = prompts["diagram_generation_system"]

    assert "JSON" in decision_prompt
    assert "json" in decision_prompt.lower()
    assert "Mermaid" in generation_prompt
    assert "JSON" not in generation_prompt
    assert "json" not in generation_prompt.lower()
    assert "只输出 Mermaid 源码" in generation_prompt
    assert "不是 demo" in generation_prompt
    assert "8 到 18" in generation_prompt
    assert "覆盖用户问题中的主要概念、关系、步骤或边界条件" in generation_prompt


def test_diagram_render_schema_accepts_mermaid_text_only() -> None:
    render = DiagramRender.model_validate(
        {
            "engine": "mermaid",
            "format": "text",
            "source": "flowchart TD\n  a-->b",
        }
    )

    assert render.engine == "mermaid"


def test_flow_rejects_edge_referencing_unknown_step() -> None:
    with pytest.raises(ValidationError):
        FlowDiagram.model_validate(
            {
                "type": "flow",
                "title": "流程",
                "summary": "流程说明",
                "spec": {
                    "steps": [
                        {"id": "a", "label": "开始", "description": "开始执行"},
                    ],
                    "edges": [{"source": "a", "target": "missing", "label": "下一步"}],
                },
            }
        )


def test_relation_rejects_edge_referencing_unknown_node() -> None:
    with pytest.raises(ValidationError):
        RelationDiagram.model_validate(
            {
                "type": "relation",
                "title": "关系",
                "summary": "关系说明",
                "spec": {
                    "nodes": [
                        {"id": "client", "label": "客户端", "description": "发起请求"},
                    ],
                    "edges": [
                        {
                            "source": "client",
                            "target": "server",
                            "label": "请求",
                            "description": "发送请求",
                        }
                    ],
                },
            }
        )


def test_sequence_supports_from_to_alias_and_validates_actor_ids() -> None:
    diagram = SequenceDiagram.model_validate(
        {
            "type": "sequence",
            "title": "握手",
            "summary": "客户端和服务器建立连接",
            "spec": {
                "actors": [
                    {"id": "client", "label": "客户端", "description": "发起连接"},
                    {"id": "server", "label": "服务器", "description": "接受连接"},
                ],
                "messages": [
                    {
                        "from": "client",
                        "to": "server",
                        "label": "SYN",
                        "description": "请求建立连接",
                    }
                ],
            },
        }
    )

    dumped = diagram.model_dump(by_alias=True)
    assert dumped["spec"]["messages"][0]["from"] == "client"
    assert dumped["spec"]["messages"][0]["to"] == "server"

    with pytest.raises(ValidationError):
        SequenceDiagram.model_validate(
            {
                "type": "sequence",
                "title": "错误",
                "summary": "引用未知参与者",
                "spec": {
                    "actors": [
                        {"id": "client", "label": "客户端", "description": "发起连接"},
                    ],
                    "messages": [
                        {
                            "from": "client",
                            "to": "missing",
                            "label": "请求",
                            "description": "错误目标",
                        }
                    ],
                },
            }
        )


def test_state_supports_from_to_alias_and_validates_state_ids() -> None:
    diagram = StateDiagram.model_validate(
        {
            "type": "state",
            "title": "状态",
            "summary": "状态变化过程",
            "spec": {
                "states": [
                    {"id": "new", "label": "新建", "description": "刚创建"},
                    {"id": "ready", "label": "就绪", "description": "等待运行"},
                ],
                "transitions": [
                    {
                        "from": "new",
                        "to": "ready",
                        "label": "调度",
                        "description": "进入就绪队列",
                    }
                ],
            },
        }
    )

    dumped = diagram.model_dump(by_alias=True)
    assert dumped["spec"]["transitions"][0]["from"] == "new"
    assert dumped["spec"]["transitions"][0]["to"] == "ready"

    with pytest.raises(ValidationError):
        StateDiagram.model_validate(
            {
                "type": "state",
                "title": "错误",
                "summary": "未知状态引用",
                "spec": {
                    "states": [
                        {"id": "new", "label": "新建", "description": "刚创建"},
                    ],
                    "transitions": [
                        {
                            "from": "new",
                            "to": "missing",
                            "label": "错误",
                            "description": "引用不存在状态",
                        }
                    ],
                },
            }
        )


def test_extra_fields_and_length_limits_are_rejected() -> None:
    with pytest.raises(ValidationError):
        RelationDiagram.model_validate(
            {
                "type": "relation",
                "title": "关系",
                "summary": "关系说明",
                "unexpected": True,
                "spec": {"nodes": [], "edges": []},
            }
        )

    with pytest.raises(ValidationError):
        RelationDiagram.model_validate(
            {
                "type": "relation",
                "title": "标题超过二十个字需要被模型拒绝掉",
                "summary": "关系说明",
                "spec": {"nodes": [], "edges": []},
            }
        )

    with pytest.raises(ValidationError):
        RelationDiagram.model_validate(
            {
                "type": "relation",
                "title": "关系",
                "summary": "关系说明",
                "spec": {
                    "nodes": [
                        {
                            "id": "a",
                            "label": "这个标签长度明显超过十六个字需要拒绝",
                            "description": "说明",
                        }
                    ],
                    "edges": [],
                },
            }
        )


def test_hierarchy_recursive_node_model_validates_children() -> None:
    diagram = HierarchyDiagram.model_validate(
        {
            "type": "hierarchy",
            "title": "知识结构",
            "summary": "展示知识点组成",
            "spec": {
                "root": {
                    "id": "root",
                    "label": "网络",
                    "description": "计算机网络",
                    "children": [
                        {
                            "id": "tcp",
                            "label": "TCP",
                            "description": "可靠传输",
                            "children": [],
                        }
                    ],
                }
            },
        }
    )

    assert diagram.spec.root.children[0].id == "tcp"
