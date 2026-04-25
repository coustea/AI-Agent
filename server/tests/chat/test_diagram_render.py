from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.chat.diagram_render import build_diagram_render


def test_build_sequence_diagram_render() -> None:
    render = build_diagram_render(
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
                    {"from": "client", "to": "server", "label": "SYN", "description": "请求"}
                ],
            },
        }
    )

    assert render["engine"] == "mermaid"
    assert render["format"] == "text"
    assert render["source"].startswith("sequenceDiagram")
    assert 'participant client as "客户端<br/>发起连接"' in render["source"]
    assert "client->>server: SYN" in render["source"]


def test_build_flow_diagram_render() -> None:
    render = build_diagram_render(
        {
            "type": "flow",
            "title": "流程",
            "summary": "学习流程",
            "spec": {
                "steps": [
                    {"id": "start", "label": "开始", "description": "读题"},
                    {"id": "solve", "label": "求解", "description": "列式"},
                ],
                "edges": [{"source": "start", "target": "solve", "label": "下一步"}],
            },
        }
    )

    assert render["source"].startswith("flowchart TD")
    assert 'start["开始<br/>读题"]' in render["source"]
    assert "start -->|下一步| solve" in render["source"]


def test_build_state_diagram_render() -> None:
    render = build_diagram_render(
        {
            "type": "state",
            "title": "状态",
            "summary": "状态变化过程",
            "spec": {
                "states": [
                    {"id": "new", "label": "新建", "description": "刚创建"},
                    {"id": "ready", "label": "就绪", "description": "等待运行"},
                ],
                "transitions": [{"from": "new", "to": "ready", "label": "调度"}],
            },
        }
    )

    assert render["source"].startswith("stateDiagram-v2")
    assert 'state "新建<br/>刚创建" as new' in render["source"]
    assert "new --> ready: 调度" in render["source"]


def test_build_relation_diagram_render() -> None:
    render = build_diagram_render(
        {
            "type": "relation",
            "title": "关系",
            "summary": "请求关系",
            "spec": {
                "nodes": [
                    {"id": "client", "label": "客户端", "description": "发起请求"},
                    {"id": "server", "label": "服务器", "description": "处理请求"},
                ],
                "edges": [{"source": "client", "target": "server", "label": "请求"}],
            },
        }
    )

    assert render["source"].startswith("graph TD")
    assert 'server["服务器<br/>处理请求"]' in render["source"]
    assert "client -->|请求| server" in render["source"]


def test_build_hierarchy_diagram_render() -> None:
    render = build_diagram_render(
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

    assert render["source"].startswith("graph TD")
    assert 'root["网络<br/>计算机网络"]' in render["source"]
    assert "root --> tcp" in render["source"]


def test_build_compare_diagram_render() -> None:
    render = build_diagram_render(
        {
            "type": "compare",
            "title": "对比",
            "summary": "协议对比",
            "spec": {
                "items": [
                    {
                        "label": "TCP",
                        "description": "可靠",
                        "points": ["面向连接", "有序"],
                    },
                    {
                        "label": "UDP",
                        "description": "轻量",
                        "points": ["无连接", "快速"],
                    },
                ],
                "dimensions": ["可靠性", "速度"],
            },
        }
    )

    assert render["source"].startswith("flowchart LR")
    assert 'item_1["TCP<br/>可靠<br/>面向连接<br/>有序"]' in render["source"]
    assert 'item_2["UDP<br/>轻量<br/>无连接<br/>快速"]' in render["source"]


def test_mermaid_labels_are_escaped() -> None:
    render = build_diagram_render(
        {
            "type": "flow",
            "title": "转义",
            "summary": "转义标签",
            "spec": {
                "steps": [
                    {"id": "a", "label": 'A ["x"]', "description": "line\nbreak"},
                ],
                "edges": [],
            },
        }
    )

    assert 'a["A (' in render["source"]
    assert '"x"' not in render["source"]
    assert "line break" in render["source"]
