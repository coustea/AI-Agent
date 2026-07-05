import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.resource.schemas import ResourceGenerationRequest
from app.shared.ppt import PPTPreferences


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
                    "structure": "progressive",
                    "include_examples": False,
                    "focus_mode": "key_concepts",
                    "depth_level": "quick",
                },
                "mindmap": {
                    "map_type": "knowledge_tree",
                    "max_depth": 2,
                    "leaf_detail": "brief_note",
                    "show_relations": False,
                },
                "code": {
                    "programming_language": "python",
                    "case_type": "basic_demo",
                    "difficulty": "beginner",
                    "focus": "syntax",
                },
                "quiz": {
                    "question_count": 5,
                    "difficulty_mode": "basic",
                    "exam_style": "school",
                    "question_types": ["single", "multiple", "judge", "fill"],
                },
                "reading": {
                    "reading_depth": "course_extended",
                    "max_items": 5,
                    "language_preference": "both",
                    "focus": "textbook",
                },
                "ppt": {
                    "template": "auto",
                    "explanation_style": "concept",
                    "density": "standard",
                    "focus": ["core_concepts"],
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
                {"agent_id": "quiz", "enabled": True, "priority": 1},
                {"agent_id": "video", "enabled": True, "priority": 2},
            ],
            "agent_configs": {
                "video": {
                    "style": "precision_light",
                    "focus": "process",
                    "voice": "teacher",
                    "aspect_ratio": "16:9",
                }
            },
        }
    )

    assert request.enabled_agent_ids() == ["content", "quiz", "video"]
    assert request.agent_configs.video.style == "precision_light"
    assert request.agent_configs.video.focus == "process"


def test_resource_generation_request_video_is_now_default_enabled():
    request = ResourceGenerationRequest.model_validate(
        {
            "learning_need": "复习操作系统进程调度",
        }
    )

    assert "video" in request.enabled_agent_ids()


# ---------------------------------------------------------------------------
# PPTPreferences
# ---------------------------------------------------------------------------


class TestPptConfig:
    def test_accepts_empty_object(self):
        config = PPTPreferences.model_validate({})
        assert config.template == "auto"
        assert config.explanation_style == "concept"

    @pytest.mark.parametrize(
        "field,value",
        [
            ("theme_id", "neon"),
            ("visual_emphasis", "high"),
            ("template_id", "corporate"),
            ("output_format", "pdf"),
        ],
    )
    def test_rejects_old_fields(self, field, value):
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            PPTPreferences.model_validate({field: value})
