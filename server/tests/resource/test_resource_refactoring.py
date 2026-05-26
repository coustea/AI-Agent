"""Tests for the resource generation refactoring:

1. LearningBlueprint replaces KnowledgeGraph as internal coordination structure
2. Path node resource generation uses correct field names
3. WorkerState uses blueprint instead of knowledge_graph
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
    AgentInstruction,
    AgentSelection,
    ExecutionPlan,
    LearningBlueprint,
    ResourceAgentId,
    ResourceGenerationRequest,
    WorkerState,
)


# ======================================================================
# 1. Knowledge graph no longer exists as a public resource type
# ======================================================================


def test_knowledge_graph_is_not_a_valid_agent_id():
    """knowledge_graph must not appear in ResourceAgentId enum."""
    assert "knowledge_graph" not in [e.value for e in ResourceAgentId]


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


def test_valid_agent_ids_are_only_six():
    """The public agent IDs are exactly: content, mindmap, quiz, reading, code, ppt."""
    expected = {"content", "mindmap", "quiz", "reading", "code", "ppt"}
    actual = {e.value for e in ResourceAgentId}
    assert actual == expected


def test_agent_selection_rejects_knowledge_graph():
    """AgentSelection must reject knowledge_graph as agent_id."""
    with pytest.raises(ValidationError):
        AgentSelection(agent_id="knowledge_graph", enabled=True, priority=0)


# ======================================================================
# 2. LearningBlueprint replaces KnowledgeGraph
# ======================================================================


def test_learning_blueprint_has_required_fields():
    """LearningBlueprint must contain topic and learner_goal."""
    bp = LearningBlueprint(topic="操作系统处理机调度", learner_goal="理解典型调度算法")
    assert bp.topic == "操作系统处理机调度"
    assert bp.learner_goal == "理解典型调度算法"


def test_learning_blueprint_default_lists_are_empty():
    """LearningBlueprint list fields default to empty."""
    bp = LearningBlueprint(topic="test")
    assert bp.prerequisite_concepts == []
    assert bp.core_concepts == []
    assert bp.difficult_points == []
    assert bp.concept_relations == []
    assert bp.example_scenarios == []
    assert bp.practice_targets == []


def test_learning_blueprint_resource_guidance_is_dict():
    """resource_guidance maps agent_id to generation focus."""
    bp = LearningBlueprint(
        topic="test",
        resource_guidance={"content": "侧重调度算法对比", "quiz": "重点出分析题"},
    )
    assert bp.resource_guidance["content"] == "侧重调度算法对比"


def test_execution_plan_uses_blueprint():
    """ExecutionPlan uses LearningBlueprint, not knowledge_graph."""
    bp = LearningBlueprint(topic="test", learner_goal="goal")
    plan = ExecutionPlan(blueprint=bp)
    assert plan.blueprint is bp
    assert plan.blueprint.topic == "test"
    assert not hasattr(plan, "knowledge_graph")


# ======================================================================
# 3. WorkerState uses blueprint, not knowledge_graph
# ======================================================================


def test_worker_state_uses_blueprint_field():
    """WorkerState must have blueprint field, not knowledge_graph."""
    bp = LearningBlueprint(topic="test")
    state = WorkerState(blueprint=bp, learning_need="OS调度")
    assert state.blueprint is bp
    assert not hasattr(state, "knowledge_graph")


def test_worker_state_blueprint_can_be_none():
    """WorkerState.blueprint defaults to None (PlanningAgent may fail)."""
    state = WorkerState(learning_need="test")
    assert state.blueprint is None


def test_worker_state_instruction_can_be_none():
    """WorkerState.instruction defaults to None."""
    state = WorkerState(learning_need="test")
    assert state.instruction is None


def test_worker_state_instruction_field_exists():
    """WorkerState must have an instruction field for AgentInstruction."""
    instr = AgentInstruction(agent_id="quiz", focus="scheduling algorithms")
    state = WorkerState(learning_need="test", instruction=instr)
    assert state.instruction is instr
    assert state.instruction.agent_id == "quiz"


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
# 5. AgentInstruction structure
# ======================================================================


def test_agent_instruction_fields():
    """AgentInstruction has focus, difficulty, personalization_notes, constraints."""
    instr = AgentInstruction(
        agent_id="content",
        focus="scheduling algorithms comparison",
        difficulty="intermediate",
        personalization_notes="student struggles with SJF",
        constraints=["avoid code examples"],
    )
    assert instr.agent_id == "content"
    assert instr.focus == "scheduling algorithms comparison"
    assert instr.difficulty == "intermediate"
    assert instr.constraints == ["avoid code examples"]


def test_agent_instruction_defaults():
    """AgentInstruction defaults: focus="", difficulty="intermediate", constraints=[]."""
    instr = AgentInstruction(agent_id="quiz")
    assert instr.focus == ""
    assert instr.difficulty == "intermediate"
    assert instr.constraints == []


# ======================================================================
# 6. Integration: ExecutionPlan -> WorkerState pipeline
# ======================================================================


def test_execution_plan_to_worker_state():
    """A full ExecutionPlan can populate WorkerState fields."""
    bp = LearningBlueprint(
        topic="OS scheduling",
        learner_goal="understand FCFS, SJF, RR",
        prerequisite_concepts=["process states", "ready queue"],
        core_concepts=["FCFS", "SJF", "RR", "priority scheduling"],
        difficult_points=["SJF starvation", "RR time quantum choice"],
    )
    instr = AgentInstruction(
        agent_id="quiz",
        focus="scheduling algorithm comparison",
        constraints=["include analysis questions"],
    )
    plan = ExecutionPlan(
        blueprint=bp,
        agent_instructions=[instr],
        personalization_summary="student is strong on concepts but weak on analysis",
    )

    state = WorkerState(
        learning_need="OS scheduling algorithms",
        blueprint=plan.blueprint,
        instruction=instr,
        agent_config={"question_count": 5},
    )

    assert state.blueprint.topic == "OS scheduling"
    assert state.blueprint.difficult_points == ["SJF starvation", "RR time quantum choice"]
    assert state.instruction.agent_id == "quiz"
    assert state.instruction.constraints == ["include analysis questions"]


def test_execution_plan_fallback_blueprint():
    """When PlanningAgent fails, a minimal LearningBlueprint still works."""
    bp = LearningBlueprint(topic="fallback topic", learner_goal="basic goal")
    plan = ExecutionPlan(blueprint=bp)
    state = WorkerState(learning_need="test", blueprint=plan.blueprint)
    assert state.blueprint.topic == "fallback topic"