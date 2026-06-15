import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.resource.schemas import ResourceGenerationRequest


def test_resource_generation_request_rebuilds_for_fastapi_body_validation():
    assert ResourceGenerationRequest.model_rebuild(force=True) is True


def test_resource_generation_request_accepts_current_frontend_payload():
    request = ResourceGenerationRequest.model_validate(
        {
            "learning_need": "复习 TCP 三次握手",
            "learning_scenario": "daily_review",
            "selected_agents": [
                {"agent_id": "content", "enabled": True, "priority": 0},
                {"agent_id": "mindmap", "enabled": True, "priority": 1},
                {"agent_id": "quiz", "enabled": True, "priority": 2},
            ],
            "agent_configs": {
                "content": {
                    "structure": "summary_first",
                    "include_common_mistakes": True,
                    "include_examples": False,
                    "focus_mode": "key_concepts",
                    "depth_level": "quick",
                },
                "mindmap": {
                    "map_type": "knowledge_tree",
                    "max_depth": 2,
                    "highlight_weak": False,
                    "expand_weak_points": False,
                    "include_prerequisites": False,
                },
                "code": {
                    "programming_language": "python",
                    "case_type": "basic_demo",
                    "difficulty": "beginner",
                },
                "quiz": {
                    "question_count": 1,
                    "difficulty_mode": "basic",
                    "weak_point_weight": 20,
                    "exam_style": "school",
                    "include_analysis": True,
                    "question_types": ["single", "multiple", "judge", "fill"],
                },
                "reading": {
                    "reading_depth": "course_extended",
                    "max_items": 1,
                    "language_preference": "both",
                },
            },
            }
    )

    assert request.learning_need == "复习 TCP 三次握手"
    assert request.enabled_agent_ids() == ["content", "mindmap", "quiz"]
    assert request.agent_configs.quiz.difficulty_mode == "basic"
    assert request.agent_configs.quiz.question_types == ["single", "multiple", "judge", "fill"]
    assert request.agent_configs.reading.language_preference == "both"


def test_resource_generation_request_normalizes_frontend_bilingual_alias():
    request = ResourceGenerationRequest.model_validate(
        {
            "learning_need": "阅读操作系统论文",
            "agent_configs": {
                "reading": {
                    "language_preference": "bilingual",
                },
            },
        }
    )

    assert request.agent_configs.reading.language_preference == "both"


def test_resource_generation_request_rejects_unsupported_ppt_output_format():
    with pytest.raises(ValidationError):
        ResourceGenerationRequest.model_validate(
            {
                "learning_need": "把离散数学章节做成课堂讲解PPT",
                "agent_configs": {
                    "ppt": {
                        "output_format": "pptx",
                    },
                },
            }
        )


def test_resource_generation_request_rejects_legacy_payload_fields():
    with pytest.raises(ValidationError):
        ResourceGenerationRequest.model_validate(
            {
                "topic": "操作系统进程调度",
                "resource_types": ["content", "quiz"],
            }
        )


def test_resource_generation_request_rejects_legacy_diagram_agent():
    with pytest.raises(ValidationError):
        ResourceGenerationRequest.model_validate(
            {
                "learning_need": "复习 TCP 三次握手",
                "selected_agents": [
                    {"agent_id": "diagram", "enabled": True, "priority": 0},
                ],
            }
        )


def test_resource_generation_request_accepts_video_agent_config():
    request = ResourceGenerationRequest.model_validate(
        {
            "learning_need": "把 TCP 三次握手生成讲解视频",
            "selected_agents": [
                {"agent_id": "content", "enabled": True, "priority": 0},
                {"agent_id": "video", "enabled": True, "priority": 1},
            ],
            "agent_configs": {
                "video": {
                    "duration_seconds": 180,
                    "scene_count": 6,
                    "style": "explainer",
                    "voice": "teacher",
                    "aspect_ratio": "16:9",
                    "include_captions": True,
                    "output_format": "preview",
                }
            },
        }
    )

    assert request.enabled_agent_ids() == ["content", "video"]
    assert request.agent_configs.video.duration_seconds == 180
    assert request.agent_configs.video.scene_count == 6
    assert request.agent_configs.video.output_format == "preview"


def test_resource_generation_request_video_is_not_default_enabled():
    request = ResourceGenerationRequest.model_validate(
        {
            "learning_need": "复习操作系统进程调度",
        }
    )

    assert "video" not in request.enabled_agent_ids()


@pytest.mark.asyncio
async def test_resource_workflow_created_event_is_emitted_before_generation(monkeypatch):
    pytest.importorskip("app.resource.workflow", reason="workflow module not yet implemented")
    from app.resource import workflow as resource_workflow
    from app.resource.events import AgentEventEmitter
    from app.resource.workflow import ResourceGenerationWorkflow
    from app.resource.schemas import (
        AgentResult,
        ExecutionPlan,
        LearningBlueprint,
        AgentInstruction,
        ReviewResult,
        ResourceBundle,
    )

    class FakeRecord:
        id = 123

    class FakeStore:
        def __init__(self):
            self.persisted = {}

        async def create_resource(self, *, user_id, request):
            return FakeRecord()

        async def update_resource_status(self, *, resource_id, status):
            self.updated = (resource_id, status)

        async def save_agent_result(self, *, user_id, resource_id, result):
            self.persisted[result.metadata["agent_id"]] = result

        async def results_for_review(self, user_id, resource_id, failures):
            return {**self.persisted, **failures}

        async def save_generation_results(self, **kwargs):
            self.saved = kwargs

        async def get_resource_bundle(self, user_id, resource_id):
            return ResourceBundle(
                id=str(resource_id),
                task_id=str(resource_id),
                learning_need="复习 TCP 三次握手",
                status="completed",
                resources=[],
            )

    class FakePlanningAgent:
        def __init__(self, emitter):
            pass

        async def run(self, learning_need, learning_scenario, profile, enabled_agents):
            return ExecutionPlan(
                blueprint=LearningBlueprint(topic="TCP", learner_goal="理解三次握手"),
                agent_instructions=[AgentInstruction(agent_id="content", focus="讲解三次握手")],
            )

    class FakeContentAgent:
        def __init__(self, emitter):
            pass

        async def run(self, state):
            return AgentResult(
                success=True,
                content="# 内容",
                title="课程内容",
                summary="生成内容",
                metadata={"agent_id": "content"},
            )

    class FakeReviewAgent:
        def __init__(self, emitter):
            pass

        async def run(self, results, blueprint, profile, learning_need):
            return ReviewResult(passed=True)

    monkeypatch.setattr(resource_workflow, "PlanningAgent", FakePlanningAgent)
    monkeypatch.setattr(resource_workflow, "ReviewAgent", FakeReviewAgent)
    monkeypatch.setitem(resource_workflow.AGENT_CLASSES, "content", FakeContentAgent)


    request = ResourceGenerationRequest.model_validate(
        {
            "learning_need": "复习 TCP 三次握手",
            "selected_agents": [
                {"agent_id": "content", "enabled": True, "priority": 0},
            ],
        }
    )
    emitter = AgentEventEmitter()

    result = await ResourceGenerationWorkflow(emitter=emitter, resource_service=FakeStore()).run(user_id=1, request=request, profile={"user_data": {"user_id": 1}, "profile_data": {}})
    first_event = await anext(emitter.stream())

    assert result["success"] is True
    assert "event: workflow" in first_event
    assert "资源生成任务已创建" in first_event
