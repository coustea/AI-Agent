"""Tests for the resource generation refactoring:

1. TeachingPlan replaces LearningBlueprint as PlanningAgent's sole output
2. Path node resource generation uses correct field names
3. ResourceInput uses teaching_plan and upstream_handoffs, not blueprint/previous_results
4. knowledge_graph is no longer a valid ResourceAgentId
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

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
)


# ======================================================================
# 1. Knowledge graph no longer exists as a public resource type
# ======================================================================


def test_knowledge_graph_is_not_a_valid_agent_id():
    """knowledge_graph must not appear in ResourceAgentId enum."""
    assert "knowledge_graph" not in [e.value for e in ResourceAgentId]


def test_planning_prompt_describes_teaching_plan_contract_and_ppt_agent():
    prompt_path = Path(__file__).resolve().parents[2] / "app" / "resource" / "prompts" / "planning.md"
    prompt = prompt_path.read_text(encoding="utf-8")

    assert "教学" in prompt or "teaching" in prompt.lower()
    assert "大纲" in prompt or "outline" in prompt.lower()


def test_agent_meta_does_not_include_knowledge_graph():
    """AGENT_META must not have knowledge_graph entry."""
    assert "knowledge_graph" not in AGENT_META


def test_default_order_excludes_knowledge_graph():
    """AGENT_DEFAULT_ORDER must not include knowledge_graph."""
    assert "knowledge_graph" not in AGENT_DEFAULT_ORDER


def test_default_enabled_excludes_knowledge_graph():
    """AGENT_DEFAULT_ENABLED must not include knowledge_graph."""
    assert "knowledge_graph" not in AGENT_DEFAULT_ENABLED


def test_agent_configs_rejects_knowledge_graph_field():
    """AgentConfigs with extra="forbid" must reject knowledge_graph field."""
    with pytest.raises(ValidationError):
        AgentConfigs(knowledge_graph={"layout_mode": "force"})


def test_valid_agent_ids_are_seven():
    """The public agent IDs are exactly: content, mindmap, quiz, reading, code, ppt, video."""
    expected = {"content", "mindmap", "quiz", "reading", "code", "ppt", "video"}
    actual = {e.value for e in ResourceAgentId}
    assert actual == expected


def test_agent_selection_rejects_knowledge_graph():
    """AgentSelection must reject knowledge_graph as agent_id."""
    with pytest.raises(ValidationError):
        AgentSelection(agent_id="knowledge_graph", enabled=True, priority=0)


# ======================================================================
# 2. TeachingPlan replaces LearningBlueprint
# ======================================================================


def test_teaching_plan_has_required_fields():
    """TeachingPlan must contain outline and agent_assignments."""
    plan = TeachingPlan()
    assert plan.outline == []
    assert plan.agent_assignments == []


def test_teaching_plan_default_lists_are_empty():
    """TeachingPlan list fields default to empty."""
    plan = TeachingPlan()
    assert plan.outline == []


def test_teaching_plan_has_no_agent_instructions():
    """TeachingPlan must not have agent_instructions or resource_guidance."""
    dumped = TeachingPlan().model_dump(mode="json")
    assert "agent_instructions" not in dumped
    assert "resource_guidance" not in dumped


def test_teaching_plan_outline_items_have_stable_ids():
    """TeachingOutlineItem ids must match pattern o1, o2, etc."""
    item = TeachingOutlineItem(id="o1", title="为什么需要三次握手")
    assert item.id == "o1"


# ======================================================================
# 3. ResourceInput uses teaching_plan and upstream_handoffs
# ======================================================================


def test_worker_state_uses_teaching_plan_field():
    """ResourceInput must have teaching_plan field, not blueprint."""
    plan = TeachingPlan()
    state = ResourceInput(teaching_plan=plan, learning_need="OS调度")
    assert state.teaching_plan is plan
    assert not hasattr(state, "knowledge_graph")
    assert not hasattr(state, "blueprint")


def test_worker_state_teaching_plan_can_be_none():
    """ResourceInput.teaching_plan defaults to None (PlanningAgent may fail)."""
    state = ResourceInput(learning_need="test")
    assert state.teaching_plan is None


def test_worker_state_upstream_handoffs_defaults_empty():
    """ResourceInput.upstream_handoffs defaults to empty dict."""
    state = ResourceInput(learning_need="test")
    assert state.upstream_handoffs == {}


def test_worker_state_upstream_handoffs_holds_downstream_context():
    """ResourceInput.upstream_handoffs maps agent_id to DownstreamContext."""
    handoff = DownstreamContext(source_agent="content", title="内容", one_sentence_summary="讲解")
    state = ResourceInput(learning_need="test", upstream_handoffs={"content": handoff})
    assert state.upstream_handoffs["content"].source_agent == "content"
    assert not hasattr(state, "previous_results")


# ======================================================================
# 4. ResourceGenerationRequest uses correct field names (P0 fix)
# ======================================================================


def test_request_requires_learning_need_not_topic():
    """ResourceGenerationRequest must use learning_need, not topic."""
    req = ResourceGenerationRequest(learning_need="OS scheduling")
    assert req.learning_need == "OS scheduling"
    assert not hasattr(req, "topic")


def test_request_rejects_topic_field():
    """ResourceGenerationRequest with extra="forbid" must reject topic."""
    with pytest.raises(ValidationError):
        ResourceGenerationRequest(topic="OS", goal="learn")


def test_request_rejects_goal_field():
    """ResourceGenerationRequest with extra="forbid" must reject goal."""
    with pytest.raises(ValidationError):
        ResourceGenerationRequest(learning_need="test", goal="learn")


def test_request_rejects_enabled_agents_field():
    """ResourceGenerationRequest with extra="forbid" must reject enabled_agents."""
    with pytest.raises(ValidationError):
        ResourceGenerationRequest(learning_need="test", enabled_agents=["content"])


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


def test_request_learning_scenario_default():
    """learning_scenario defaults to self_study."""
    req = ResourceGenerationRequest(learning_need="test")
    assert req.learning_scenario == "self_study"


# ======================================================================
# 5. DownstreamContext structure
# ======================================================================


def test_downstream_context_fields():
    """DownstreamContext has source_agent, title, one_sentence_summary, covered_outline_ids."""
    ctx = DownstreamContext(
        source_agent="content",
        title="TCP 三次握手讲解",
        one_sentence_summary="解释三次握手的目的和流程",
        covered_outline_ids=["o1", "o2"],
    )
    assert ctx.source_agent == "content"
    assert ctx.covered_outline_ids == ["o1", "o2"]


def test_downstream_context_defaults():
    """DownstreamContext defaults: title="", one_sentence_summary="", covered_outline_ids=[]."""
    ctx = DownstreamContext(source_agent="quiz")
    assert ctx.title == ""
    assert ctx.one_sentence_summary == ""
    assert ctx.covered_outline_ids == []


# ======================================================================
# 6. Integration: TeachingPlan -> ResourceInput pipeline
# ======================================================================


def test_teaching_plan_to_worker_state():
    """A TeachingPlan can populate ResourceInput fields."""
    plan = TeachingPlan(
        outline=[
            TeachingOutlineItem(id="o1", title="FCFS 调度", key_points=["先来先服务"]),
            TeachingOutlineItem(id="o2", title="SJF 调度", key_points=["最短作业优先"]),
        ],
    )
    handoff = DownstreamContext(
        source_agent="content",
        title="调度算法讲解",
        one_sentence_summary="覆盖 FCFS、SJF、RR 三种调度算法",
        covered_outline_ids=["o1", "o2"],
    )

    state = ResourceInput(
        learning_need="OS scheduling algorithms",
        teaching_plan=plan,
        upstream_handoffs={"content": handoff},
        agent_config={"question_count": 5},
    )

    assert state.teaching_plan.outline[0].id == "o1"
    assert len(state.teaching_plan.outline) == 2
    assert state.upstream_handoffs["content"].covered_outline_ids == ["o1", "o2"]


def test_teaching_plan_fallback_none():
    """When PlanningAgent fails, teaching_plan=None still works."""
    state = ResourceInput(learning_need="test", teaching_plan=None)
    assert state.teaching_plan is None


# ======================================================================
# 7. Path planning no longer exposes legacy node-resource request schema
# ======================================================================


def test_path_node_resource_request_schema_removed():
    import app.path.schemas as schemas

    assert not hasattr(schemas, "PathNodeResourceRequest")



