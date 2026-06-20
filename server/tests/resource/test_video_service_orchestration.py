import os
import sys
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SPARK_MAX_API_PASSWORD", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.resource.workflow.nodes import AGGREGATION_AGENT_IDS, build_agent_resource_input
from app.resource.schemas import AgentResult, DownstreamContext, ResourceGenerationRequest, TeachingPlan
from app.resource.schemas.plan import TeachingOutlineItem, AgentAssignment


def test_video_is_aggregation_agent_not_base_worker():
    registry = {"content": object, "reading": object, "ppt": object, "video": object}

    assert "video" in AGGREGATION_AGENT_IDS


def test_agent_resource_input_receives_upstream_handoffs():
    request = ResourceGenerationRequest.model_validate(
        {
            "learning_need": "生成 TCP 讲解视频",
            "selected_agents": [
                {"agent_id": "content", "enabled": True, "priority": 0},
                {"agent_id": "video", "enabled": True, "priority": 1},
            ],
        }
    )
    handoff = DownstreamContext(
        source_agent="content",
        title="课程内容",
        one_sentence_summary="TCP 三次握手讲解",
    )

    teaching_plan = TeachingPlan(
        teaching_strategy="循序渐进",
        outline=[
            TeachingOutlineItem(id="o1", title="TCP 概述", goal="理解 TCP 基础", key_points=["可靠传输"]),
            TeachingOutlineItem(id="o2", title="三次握手", goal="掌握连接建立", key_points=["SYN", "ACK"]),
            TeachingOutlineItem(id="o3", title="四次挥手", goal="掌握连接断开", key_points=["FIN"]),
        ],
        agent_assignments=[
            AgentAssignment(agent_id="content", assigned_outline_ids=["o1", "o2"], focus_instruction="讲解", style_constraint="清晰"),
            AgentAssignment(agent_id="video", assigned_outline_ids=["o1", "o2", "o3"], focus_instruction="制作视频", style_constraint="生动"),
        ],
    )

    input_data = build_agent_resource_input(
        request=request,
        resource_id=1,
        agent_id="video",
        teaching_plan=teaching_plan,
        profile={"level": "beginner"},
        upstream_handoffs={"content": handoff},
        agent_config_extra=None,
    )

    assert input_data.agent_name == "video"
    assert input_data.upstream_handoffs["content"].source_agent == "content"
