import os
import sys
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SPARK_MAX_API_PASSWORD", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


async def _fake_generate_node(_input_data):
    from app.resource.schemas import AgentResult

    return AgentResult(
        success=True,
        title="节点讲义",
        summary="已生成节点资源",
        content="# 节点讲义",
        file_type="markdown",
    )


def test_service_exposes_path_node_generation_entrypoint():
    import app.resource.path_helpers as path_helpers
    from app.resource.agents.base import AGENT_REGISTRY
    from app.resource.schemas import NodeInput

    original = AGENT_REGISTRY.get("content")

    class FakeContentAgent:
        def __init__(self, emitter=None):
            self.emitter = emitter

        async def generate_node(self, input_data):
            return await _fake_generate_node(input_data)

    AGENT_REGISTRY["content"] = FakeContentAgent
    try:
        result = __import__("asyncio").run(
            path_helpers.generate_path_node_resource(
                "content",
                NodeInput(
                    path_id=1,
                    node_id=2,
                    node_key="tcp-handshake",
                    path_title="计算机网络",
                    path_goal="掌握 TCP",
                    stage_id="stage-1",
                    node_title="TCP 三次握手",
                    tutorial_title="TCP 三次握手教程",
                    tutorial_summary="从 SYN/ACK 解释连接建立",
                    tutorial_markdown="# TCP 三次握手\n...",
                ),
            )
        )
    finally:
        if original is None:
            AGENT_REGISTRY.pop("content", None)
        else:
            AGENT_REGISTRY["content"] = original

    assert result.success is True
    assert result.title == "节点讲义"
