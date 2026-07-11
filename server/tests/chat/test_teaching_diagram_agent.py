from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SPARK_MAX_API_PASSWORD", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def _canvas_payload() -> dict:
    return {
        "graph_type": "sequence",
        "title": "TCP 连接建立",
        "subtitle": "三次握手关键过程",
        "teaching_goal": "解释为什么 TCP 需要三次握手",
        "difficulty": "intermediate",
        "visual_content": {
            "actors": ["Client", "Server"],
            "messages": [
                {"from": "Client", "to": "Server", "label": "SYN", "detail": "Seq=x"},
                {"from": "Server", "to": "Client", "label": "SYN+ACK", "detail": "Seq=y, Ack=x+1"},
                {"from": "Client", "to": "Server", "label": "ACK", "detail": "Seq=x+1, Ack=y+1"},
            ],
        },
        "teaching_content": {
            "core_explanation": "双方需要分别确认收发能力，三步才能建立可靠连接。",
            "key_points": ["客户端发起", "服务端确认并回应", "客户端最终确认"],
            "common_mistakes": ["把两次握手误认为足够"],
            "examples": ["第一次确认能发，第二次确认能收能发，第三次确认对方能收"],
            "summary": "三次握手用于双向能力确认与初始序号同步。",
        },
    }


@pytest.mark.asyncio
async def test_teaching_diagram_generator_returns_diagram(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.chat.schemas.diagram import TeachingDiagramGenerator
    from app.chat.schemas import Evidence, EvidenceSet, TutorRequestContext

    class FakeLLM:
        async def ainvoke_json(self, schema, messages, **kwargs):
            return schema.model_validate(_canvas_payload())

    generator = TeachingDiagramGenerator(llm=FakeLLM())
    result = await generator.generate(
        TutorRequestContext(user_id=7, username="test", session_id="session-1", user_input="三次握手为什么不能少？"),
        "双方需要分别确认收发能力。",
        EvidenceSet(items=[Evidence(evidence_type="attachment", summary="[图片] 这是一张网络时序图")]),
    )
    assert result["graph_type"] == "sequence"
    assert result["title"] == "TCP 连接建立"


@pytest.mark.asyncio
async def test_teaching_diagram_generator_propagates_failure() -> None:
    from app.chat.schemas.diagram import TeachingDiagramGenerator
    from app.chat.schemas import EvidenceSet, TutorRequestContext

    class RaisingLLM:
        async def ainvoke_json(self, schema, messages, **kwargs):
            raise ValueError("invalid board")

    generator = TeachingDiagramGenerator(llm=RaisingLLM())
    with pytest.raises(ValueError, match="invalid board"):
        await generator.generate(
            TutorRequestContext(user_id=7, username="test", session_id="session-1", user_input="画图说明递归"),
            "递归通过调用栈保存状态。",
            EvidenceSet(items=[]),
        )


def test_teaching_diagram_new_cs_types() -> None:
    from app.chat.schemas.diagram import TeachingDiagram

    # 1. Tree
    tree_data = {
        "graph_type": "tree",
        "title": "Binary Search Tree",
        "teaching_goal": "Understand BST structure",
        "difficulty": "intermediate",
        "visual_content": {
            "root_id": "1",
            "nodes": [
                {"id": "1", "label": "8", "left_id": "2", "right_id": "3", "type": "root", "detail": "Root node"},
                {"id": "2", "label": "3", "left_id": None, "right_id": None, "type": "leaf", "detail": "Left child"},
                {"id": "3", "label": "10", "left_id": None, "right_id": None, "type": "leaf", "detail": "Right child"},
            ]
        },
        "teaching_content": {
            "core_explanation": "A binary search tree satisfies the BST property.",
            "key_points": ["Root is 8", "Left is smaller", "Right is larger"],
            "common_mistakes": ["Violating BST property"],
            "examples": ["Search for 3 starting from 8"],
            "summary": "BST allows O(log n) search.",
        }
    }
    diagram = TeachingDiagram.model_validate(tree_data)
    assert diagram.graph_type == "tree"
    assert diagram.visual_content.root_id == "1"
    assert len(diagram.visual_content.nodes) == 3

    # 2. Grid
    grid_data = {
        "graph_type": "grid",
        "title": "Memory Grid",
        "teaching_goal": "Understand 2D array representation",
        "difficulty": "intermediate",
        "visual_content": {
            "layout": "matrix",
            "cols": 2,
            "cells": [
                {"index": 0, "label": "A", "status": "active", "pointer": "ptr1", "detail": "First element"},
                {"index": 1, "label": "B", "status": "idle", "pointer": None, "detail": "Second element"},
            ]
        },
        "teaching_content": {
            "core_explanation": "A 2D array can be flattened or represented as a grid.",
            "key_points": ["Grid representation", "Matrix layout"],
            "common_mistakes": ["Index out of bounds"],
            "examples": ["Array with 2 rows and 2 columns"],
            "summary": "Grids are structured visual representations of 2D data.",
        }
    }
    diagram = TeachingDiagram.model_validate(grid_data)
    assert diagram.graph_type == "grid"
    assert diagram.visual_content.layout == "matrix"
    assert diagram.visual_content.cols == 2
    assert len(diagram.visual_content.cells) == 2

    # 3. Protocol
    protocol_data = {
        "graph_type": "protocol",
        "title": "IP Packet Header",
        "teaching_goal": "Understand IP header fields",
        "difficulty": "advanced",
        "visual_content": {
            "orientation": "horizontal_split",
            "fields": [
                {"name": "Version", "detail": "4 bits", "width_ratio": 4, "highlight": True},
                {"name": "IHL", "detail": "4 bits", "width_ratio": 4, "highlight": False},
            ]
        },
        "teaching_content": {
            "core_explanation": "IP header contains control information.",
            "key_points": ["Version is 4 for IPv4", "IHL specifies header length"],
            "common_mistakes": ["Confusing IPv4 and IPv6 fields"],
            "examples": ["IPv4 header fields"],
            "summary": "Protocol headers specify layout of packet bytes.",
        }
    }
    diagram = TeachingDiagram.model_validate(protocol_data)
    assert diagram.graph_type == "protocol"
    assert diagram.visual_content.orientation == "horizontal_split"
    assert len(diagram.visual_content.fields) == 2
    assert diagram.visual_content.fields[0].highlight is True

    # 4. Timeline
    timeline_data = {
        "graph_type": "timeline",
        "title": "OS Process Scheduling",
        "teaching_goal": "Visualize process execution timeline",
        "difficulty": "intermediate",
        "visual_content": {
            "axis_label": "Time (ms)",
            "tracks": [
                {
                    "track_name": "CPU 0",
                    "blocks": [
                        {"label": "Process A", "start": 0.0, "duration": 10.5, "status": "active"},
                        {"label": "Idle", "start": 10.5, "duration": 2.0, "status": "idle"},
                    ]
                }
            ]
        },
        "teaching_content": {
            "core_explanation": "Processes are scheduled to execute on CPU tracks over time.",
            "key_points": ["Process A runs first", "CPU is idle for 2ms"],
            "common_mistakes": ["Overlapping execution on single CPU"],
            "examples": ["Gantt chart representation"],
            "summary": "Timelines visualize events across multiple parallel tracks.",
        }
    }
    diagram = TeachingDiagram.model_validate(timeline_data)
    assert diagram.graph_type == "timeline"
    assert diagram.visual_content.axis_label == "Time (ms)"
    assert len(diagram.visual_content.tracks) == 1
    assert len(diagram.visual_content.tracks[0].blocks) == 2


def _image_renderer_framework_diagram() -> dict:
    return {
        "graph_type": "framework",
        "title": "TCP 连接建立",
        "subtitle": "三次握手的关键信息",
        "teaching_goal": "理解连接建立过程",
        "difficulty": "intermediate",
        "visual_content": {
            "center": "三次握手",
            "modules": [
                {"title": "发起", "items": ["客户端发送 SYN"]},
                {"title": "确认", "items": ["服务端返回 SYN + ACK"]},
            ],
        },
        "teaching_content": {
            "core_explanation": "双方分别确认收发能力。",
            "key_points": ["SYN", "SYN + ACK", "ACK"],
            "summary": "建立可靠的双向连接。",
        },
    }


def _image_renderer_comparison_diagram() -> dict:
    diagram = _image_renderer_framework_diagram()
    diagram.update(
        {
            "graph_type": "comparison",
            "title": "TCP 与 UDP 对比",
            "visual_content": {
                "left_entity": {"name": "TCP", "core_label": "可靠", "short_desc": "面向连接"},
                "right_entity": {"name": "UDP", "core_label": "高效", "short_desc": "无连接"},
                "visual_summary": {"center_conclusion": "可靠性与实时性的取舍"},
                "dimensions": [{"name": "连接", "left": "需要", "right": "不需要"}],
            },
        }
    )
    return diagram


class TestDiagramImageRenderer:
    @pytest.mark.asyncio
    async def test_ensure_png_retries_once_then_returns_image(self) -> None:
        from app.chat.diagram_image_renderer import ensure_teaching_diagram_png_payload

        calls = 0

        async def flaky_renderer(diagram: dict, *, username: str, session_id: str) -> dict:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("chromium launch failed")
            return {"kind": "image", "title": diagram["title"], "image_url": "/diagram.png"}

        payload = await ensure_teaching_diagram_png_payload(
            _image_renderer_framework_diagram(), username="alice", session_id="s1", renderer=flaky_renderer,
        )

        assert calls == 2
        assert payload["kind"] == "image"

    @pytest.mark.asyncio
    async def test_ensure_png_returns_structured_fallback_after_two_failures(self) -> None:
        from app.chat.diagram_image_renderer import ensure_teaching_diagram_png_payload

        async def broken_renderer(diagram: dict, *, username: str, session_id: str) -> dict:
            raise TimeoutError("screenshot timeout")

        diagram = _image_renderer_framework_diagram()
        payload = await ensure_teaching_diagram_png_payload(
            diagram, username="alice", session_id="s1", renderer=broken_renderer,
        )

        assert payload == {
            "kind": "fallback", "diagram": diagram,
            "render_error": "图片生成暂时失败", "retryable": True,
        }

    def test_comparison_html_uses_a_style_chinese_information_graphic(self) -> None:
        from app.chat.diagram_image_renderer import build_teaching_diagram_html

        html = build_teaching_diagram_html(_image_renderer_comparison_diagram())

        assert "核心差异对比" in html
        assert "TCP" in html
        assert "UDP" in html
        assert "PNG DIAGRAM" not in html
        assert "Backend Rendered PNG" not in html
