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
                "ppt": {
                    "difficulty": "intermediate",
                    "lesson_depth": "standard",
                    "lesson_kind": "concept",
                    "learning_focus": "balanced",
                    "template_style": "paper-light",
                },
            },
            }
    )

    assert request.learning_need == "复习 TCP 三次握手"
    assert request.enabled_agent_ids() == ["content", "mindmap", "quiz"]
    assert request.agent_configs.quiz.difficulty_mode == "basic"
    assert request.agent_configs.quiz.question_types == ["single", "multiple", "judge", "fill"]
    assert request.agent_configs.reading.language_preference == "both"
    assert request.agent_configs.ppt.template_style == "paper-light"


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
