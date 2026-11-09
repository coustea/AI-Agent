"""针对统一 ResourceGenerationRequest 契约模型的单元测试。"""

from __future__ import annotations

import sys
from pathlib import Path
import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.resource.schemas import ResourceGenerationRequest
from app.shared.ppt import PPTPreferences


def test_resource_generation_request_rebuilds_for_fastapi_body_validation() -> None:
    """验证 FastAPI 启动依赖的 Request 模型能够安全重构。"""
    assert ResourceGenerationRequest.model_rebuild(force=True) is True


def test_resource_generation_request_accepts_unified_payload() -> None:
    """验证接收重构后的扁平统一参数载荷。"""
    request = ResourceGenerationRequest.model_validate(
        {
            "topic": "复习 TCP 三次握手",
            "learning_goal": "深入理解连接建立、报文标志位及状态机演化",
            "target_resources": ["content", "mindmap", "quiz", "ppt"],
            "difficulty": "intermediate",
            "preferences": {
                "programming_language": "python",
                "voice": "teacher",
            },
        }
    )

    assert request.topic == "复习 TCP 三次握手"
    assert request.learning_goal == "深入理解连接建立、报文标志位及状态机演化"
    assert request.target_resources == ["content", "mindmap", "quiz", "ppt"]
    assert request.difficulty == "intermediate"
    assert request.preferences["programming_language"] == "python"
    assert request.enabled_agent_ids() == ["content", "mindmap", "quiz", "ppt"]


def test_resource_generation_request_requires_topic() -> None:
    """验证统一请求模型强制要求 topic 字段且拒绝缺失情况。"""
    with pytest.raises(ValidationError):
        ResourceGenerationRequest.model_validate({})


def test_resource_generation_request_default_values() -> None:
    """验证统一请求模型的默认值行为。"""
    request = ResourceGenerationRequest.model_validate(
        {
            "topic": "操作系统进程调度",
        }
    )

    assert request.difficulty == "intermediate"
    assert request.target_resources == ["content", "mindmap", "quiz"]
    assert "content" in request.enabled_agent_ids()
    assert request.preferences == {}


class TestPptConfig:
    """PPTPreferences 配置模型校验测试。"""

    def test_accepts_empty_object(self) -> None:
        """测试缺省空配置时的默认值解析。"""
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
    def test_rejects_old_fields(self, field: str, value: str) -> None:
        """测试严谨拦截已弃用的旧版字段。"""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            PPTPreferences.model_validate({field: value})
