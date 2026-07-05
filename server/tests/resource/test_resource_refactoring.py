"""Tests for the resource generation refactoring.

All schemas and models are validated against the modern (version 3.0) Pydantic contracts.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Literal

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SPARK_MAX_API_PASSWORD", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest
from pydantic import ValidationError

from app.resource.schemas import (
    AGENT_DEFAULT_ENABLED,
    AGENT_DEFAULT_ORDER,
    AGENT_META,
    AgentConfigs,
    AgentSelection,
    DownstreamContext,
    ResourceAgentId,
    ResourceGenerationRequest,
    ResourceInput,
    TeachingOutlineItem,
    TeachingPlan,
    GlobalTeachingPlan,
    WorkerTask,
    AssignedSection,
    WorkerDeliverable,
    ReusableAssets,
)


def create_mock_teaching_plan() -> TeachingPlan:
    return TeachingPlan(
        schema_version="3.0",
        global_plan=GlobalTeachingPlan(
            learning_goal="OS Scheduling",
            teaching_strategy="Step-by-step introduction to FCFS and SJF.",
            difficulty="beginner",
            outline=[
                TeachingOutlineItem(id="o1", title="FCFS 调度", learning_objective="理解先来先服务", key_points=["FIFO"], must_not_miss=True),
                TeachingOutlineItem(id="o2", title="SJF 调度", learning_objective="理解最短作业优先", key_points=["SJF"], must_not_miss=True),
            ],
        ),
        worker_tasks={
            "content": WorkerTask(
                objective="Generate structural descriptions.",
                assigned_sections=[
                    AssignedSection(outline_id="o1", responsibility="primary", instruction="FCFS explanation"),
                ],
                deliverable=WorkerDeliverable(format="markdown", requirements=["clear"]),
                acceptance_criteria=["correctness"],
                exclusions=["code"],
                avoid_overlap_with=[],
            )
        }
    )


# ======================================================================
# 1. Valid Agent IDs and Configs
# ======================================================================


def test_valid_agent_ids_are_eight():
    """The public agent IDs are exactly: content, mindmap, quiz, reading, code, ppt, cartoon, video."""
    expected = {"content", "mindmap", "quiz", "reading", "code", "ppt", "cartoon", "video"}
    actual = {e.value for e in ResourceAgentId}
    assert actual == expected


def test_agent_configs_rejects_unknown_field():
    """AgentConfigs with extra="forbid" must reject unknown fields."""
    with pytest.raises(ValidationError):
        AgentConfigs(unknown_field={"layout_mode": "force"})


# ======================================================================
# 2. TeachingPlan Contracts
# ======================================================================


def test_teaching_plan_validation():
    """TeachingPlan validator must reject unsupported workers or invalid schemas."""
    plan = create_mock_teaching_plan()
    assert plan.schema_version == "3.0"
    assert len(plan.outline) == 2


def test_teaching_plan_outline_items_have_stable_ids():
    """TeachingOutlineItem ids must match pattern o1, o2, etc."""
    item = TeachingOutlineItem(
        id="o1",
        title="为什么需要三次握手",
        learning_objective="理解握手机制的必要性",
        key_points=["同步序号", "防止历史连接初始化"],
        must_not_miss=True,
    )
    assert item.id == "o1"


# ======================================================================
# 3. ResourceInput & DownstreamContext
# ======================================================================


def test_worker_state_uses_teaching_plan_field():
    """ResourceInput must have teaching_plan field."""
    plan = create_mock_teaching_plan()
    state = ResourceInput(teaching_plan=plan, learning_need="OS调度")
    assert state.teaching_plan is plan


def test_worker_state_teaching_plan_can_be_none():
    """ResourceInput.teaching_plan defaults to None."""
    state = ResourceInput(learning_need="test")
    assert state.teaching_plan is None


def test_downstream_context_fields():
    """DownstreamContext has source_agent, title, one_sentence_summary, materials."""
    ctx = DownstreamContext(
        source_agent="content",
        title="TCP 三次握手讲解",
        one_sentence_summary="解释三次握手的目的和流程",
        materials=["First packet syn", "Second packet syn-ack"],
    )
    assert ctx.source_agent == "content"
    assert ctx.materials == ["First packet syn", "Second packet syn-ack"]


def test_downstream_context_defaults():
    """DownstreamContext defaults check."""
    ctx = DownstreamContext(source_agent="quiz")
    assert ctx.title == ""
    assert ctx.one_sentence_summary == ""
    assert ctx.materials == []
    assert isinstance(ctx.reusable_assets, ReusableAssets)


# ======================================================================
# 4. ResourceGenerationRequest
# ======================================================================


def test_request_requires_learning_need():
    """ResourceGenerationRequest must use learning_need."""
    req = ResourceGenerationRequest(learning_need="OS scheduling")
    assert req.learning_need == "OS scheduling"


def test_request_rejects_extra_fields():
    """ResourceGenerationRequest with extra="forbid" must reject extra fields."""
    with pytest.raises(ValidationError):
        ResourceGenerationRequest(learning_need="test", extra_unknown_field="val")


def test_request_selected_agents_with_valid_ids():
    """selected_agents must use valid ResourceAgentId values."""
    req = ResourceGenerationRequest(
        learning_need="OS scheduling",
        selected_agents=[
            AgentSelection(agent_id="content", enabled=True, priority=0),
            AgentSelection(agent_id="mindmap", enabled=True, priority=1),
        ],
    )
    assert len(req.selected_agents) == 2
    assert req.selected_agents[0].agent_id == ResourceAgentId.CONTENT


def test_request_learning_need_cannot_be_empty():
    """learning_need must not be empty or whitespace."""
    with pytest.raises(ValidationError):
        ResourceGenerationRequest(learning_need="   ")


def test_request_default_selected_agents_when_empty():
    """When selected_agents is empty, defaults are populated."""
    req = ResourceGenerationRequest(learning_need="test")
    assert len(req.selected_agents) > 0
    assert all(s.enabled for s in req.selected_agents)
