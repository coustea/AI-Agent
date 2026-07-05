"""Agent 双入口重构测试 — 验证新类型和旧类型删除。"""

import os
import sys
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SPARK_MAX_API_PASSWORD", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def test_resource_runtime_types_are_explicit():
    from app.resource.schemas import AgentResult, DownstreamContext, NodeInput, ResourceInput

    handoff = DownstreamContext(
        source_agent="content",
        title="TCP 内容",
        one_sentence_summary="讲解 TCP 三次握手",
    )
    resource_input = ResourceInput(
        learning_need="学习 TCP 三次握手",
        learning_scenario="self_study",
        upstream_handoffs={"content": handoff},
    )

    node_input = NodeInput(
        path_id=1,
        node_id=2,
        node_key="tcp-handshake",
        path_title="计算机网络",
        path_goal="掌握 TCP/IP",
        stage_id="stage-1",
        node_title="TCP 三次握手",
        difficulty="intermediate",
        mastery_target="解释三次握手每个报文的作用",
        knowledge_points=["SYN", "ACK", "连接建立"],
        weak_knowledge_points=["第三次握手的必要性"],
        generation_focus=["用时序解释连接建立"],
        tutorial_title="TCP 三次握手教程",
        tutorial_summary="从 SYN/ACK 解释连接建立",
        tutorial_markdown="# TCP 三次握手\n...",
        existing_resources={
            "content": AgentResult(
                success=True,
                title="节点讲义",
                content="# 节点讲义",
                file_type="markdown",
            )
        },
    )

    assert resource_input.upstream_handoffs["content"].source_agent == "content"
    assert node_input.node_title == "TCP 三次握手"
    assert node_input.knowledge_points == ["SYN", "ACK", "连接建立"]
    assert node_input.stage_id == "stage-1"
    assert node_input.existing_resources["content"].title == "节点讲义"


def test_old_runtime_types_are_removed():
    import app.resource.schemas as schemas

    assert not hasattr(schemas, "WorkerState")
    assert not hasattr(schemas, "WorkerResult")
