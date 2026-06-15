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
from app.resource.schemas import AgentResult, LearningBlueprint, ResourceGenerationRequest


def test_video_is_aggregation_agent_not_base_worker():
    registry = {"content": object, "reading": object, "ppt": object, "video": object}

    assert "video" in AGGREGATION_AGENT_IDS
    assert _select_worker_agents(["content", "video", "ppt", "reading"], registry) == ["content", "reading"]


def test_agent_resource_input_receives_previous_results():
    request = ResourceGenerationRequest.model_validate(
        {
            "learning_need": "生成 TCP 讲解视频",
            "selected_agents": [
                {"agent_id": "content", "enabled": True, "priority": 0},
                {"agent_id": "video", "enabled": True, "priority": 1},
            ],
        }
    )
    previous_results = {
        "content": AgentResult(
            success=True,
            content="# TCP",
            title="课程内容",
            metadata={"agent_id": "content"},
        )
    }

    input_data = _build_agent_resource_input(
        request=request,
        resource_id=1,
        agent_id="video",
        blueprint=LearningBlueprint(topic="TCP"),
        instruction_map={},
        profile={"level": "beginner"},
        previous_results=previous_results,
        agent_config_extra=None,
    )

    assert input_data.agent_name == "video"
    assert input_data.previous_results["content"].content == "# TCP"
