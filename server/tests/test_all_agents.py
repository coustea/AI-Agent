# -*- coding: utf-8 -*-
"""验证 Resource 模块核心 schema 与请求契约可正常导入与校验。"""

import os
import sys

import pytest
from pydantic import ValidationError

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.resource.schemas import (
    AgentResult,
    ResourceGenerationRequest,
    ResourcePreferences,
    ResourceRunState,
)


def test_core_schemas_exist() -> None:
    """ResourceGenerationRequest, ResourceRunState, AgentResult 必须可用。"""
    assert hasattr(ResourceGenerationRequest, "model_validate")
    assert hasattr(ResourceRunState, "model_validate")
    assert hasattr(AgentResult, "model_validate")


def test_resource_request_validates() -> None:
    """验证 ResourceGenerationRequest 能够正确校验用户请求。"""
    req = ResourceGenerationRequest(
        topic="TCP 三次握手",
        learning_goal="掌握TCP三次握手与四次挥手的核心原理与状态流转过程",
        target_resources=["content", "mindmap"],
        difficulty="advanced",
        preferences=ResourcePreferences(programming_language="typescript", voice="coach"),
    )
    assert req.topic == "TCP 三次握手"
    assert req.target_resources == ["content", "mindmap"]
    assert req.difficulty == "advanced"
    assert req.preferences.programming_language == "typescript"
    assert req.preferences.voice == "coach"
    assert req.enabled_agent_ids() == ["content", "mindmap"]


def test_resource_run_state_validates() -> None:
    """验证 ResourceRunState 完整快照模型能够正确校验。"""
    state = ResourceRunState(
        run_id="run-test-123",
        resource_id=1,
        target_resources=["content", "quiz"],
        topic="操作系统死锁",
        learning_goal="理解死锁产生的4个必要条件",
        difficulty="intermediate",
    )
    assert state.run_id == "run-test-123"
    assert state.target_resources == ["content", "quiz"]
    assert state.topic == "操作系统死锁"
    assert state.status == "queued"


def test_agent_result_rejects_unknown_fields() -> None:
    """验证 AgentResult extra='forbid' 限制。"""
    with pytest.raises(ValidationError):
        AgentResult.model_validate({
            "success": True,
            "content": "hello",
            "previous_results": {},
        })
