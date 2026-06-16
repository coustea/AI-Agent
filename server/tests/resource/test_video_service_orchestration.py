import os
import sys
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SPARK_MAX_API_PASSWORD", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.resource.service import (
    AGGREGATION_AGENT_IDS,
    _build_agent_resource_input,
    _select_worker_agents,
)
from app.resource.schemas import AgentResult, DownstreamContext, ResourceGenerationRequest, TeachingPlan


def test_video_is_aggregation_agent_not_base_worker():
    registry = {"content": object, "reading": object, "ppt": object, "video": object}

    assert "video" in AGGREGATION_AGENT_IDS
    assert _select_worker_agents(["content", "video", "ppt", "reading"], registry) == ["content", "reading"]


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

    input_data = _build_agent_resource_input(
        request=request,
        resource_id=1,
        agent_id="video",
        teaching_plan=TeachingPlan(topic="TCP"),
        profile={"level": "beginner"},
        upstream_handoffs={"content": handoff},
        agent_config_extra=None,
    )

    assert input_data.agent_name == "video"
    assert input_data.upstream_handoffs["content"].source_agent == "content"


def test_review_agent_extracts_video_resource_audit_content():
    from app.resource.agents.review import ReviewAgent

    envelope = {
        "mode": "video_audit",
        "video_resource": {
            "agent_id": "video",
            "audit_content": '{"schema_version":"video/v1","scenes":[{"narration":"TCP 三次握手"}]}',
        },
    }

    content = ReviewAgent._extract_audit_content(envelope)

    assert "video/v1" in content
    assert "TCP 三次握手" in content


def test_overall_progress_treats_video_as_aggregation_stage_not_worker():
    from app.resource.service import ResourceService
    from app.resource.review import VIDEO_AGENT_ID, VIDEO_REVIEW_AGENT_ID

    progress = ResourceService._calculate_overall_progress(
        status="generating",
        selected_agents=["content", "reading", "video"],
        agent_snapshots={
            "planning": {"progress": 100},
            "content": {"progress": 100},
            "reading": {"progress": 100},
            "pre_review": {"progress": 100},
            "bundle": {"progress": 100},
            VIDEO_AGENT_ID: {"progress": 0},
            VIDEO_REVIEW_AGENT_ID: {"progress": 0},
        },
    )

    assert progress == 80
