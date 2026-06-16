"""Tests for the resource generation refactoring:

1. LearningBlueprint replaces KnowledgeGraph as internal coordination structure
2. Path node resource generation uses correct field names
3. ResourceInput uses blueprint instead of knowledge_graph
4. knowledge_graph is no longer a valid ResourceAgentId
"""

from __future__ import annotations

import json
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
    ResourceInput,
)


# ======================================================================
# 1. Knowledge graph no longer exists as a public resource type
# ======================================================================


def test_knowledge_graph_is_not_a_valid_agent_id():
    """knowledge_graph must not appear in ResourceAgentId enum."""
    assert "knowledge_graph" not in [e.value for e in ResourceAgentId]


def test_planning_prompt_describes_learning_blueprint_contract_and_ppt_agent():
    prompt_path = Path(__file__).resolve().parents[2] / "app" / "resource" / "prompts" / "planning.md"
    prompt = prompt_path.read_text(encoding="utf-8")

    assert '"blueprint"' in prompt
    assert '"learning_blueprint"' not in prompt
    assert '"core_concepts"' in prompt
    assert "**ppt**" in prompt


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
# 3. ResourceInput uses blueprint, not knowledge_graph
# ======================================================================


def test_worker_state_uses_blueprint_field():
    """ResourceInput must have blueprint field, not knowledge_graph."""
    bp = LearningBlueprint(topic="test")
    state = ResourceInput(blueprint=bp, learning_need="OS调度")
    assert state.blueprint is bp
    assert not hasattr(state, "knowledge_graph")


def test_worker_state_blueprint_can_be_none():
    """ResourceInput.blueprint defaults to None (PlanningAgent may fail)."""
    state = ResourceInput(learning_need="test")
    assert state.blueprint is None


def test_worker_state_instruction_can_be_none():
    """ResourceInput.instruction defaults to None."""
    state = ResourceInput(learning_need="test")
    assert state.instruction is None


def test_worker_state_instruction_field_exists():
    """ResourceInput must have an instruction field for AgentInstruction."""
    instr = AgentInstruction(agent_id="quiz", focus="scheduling algorithms")
    state = ResourceInput(learning_need="test", instruction=instr)
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
# 6. Integration: ExecutionPlan -> ResourceInput pipeline
# ======================================================================


def test_execution_plan_to_worker_state():
    """A full ExecutionPlan can populate ResourceInput fields."""
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

    state = ResourceInput(
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
    state = ResourceInput(learning_need="test", blueprint=plan.blueprint)
    assert state.blueprint.topic == "fallback topic"


# ======================================================================
# 7. Path planning no longer exposes legacy node-resource request schema
# ======================================================================


def test_path_node_resource_request_schema_removed():
    import app.path.schemas as schemas

    assert not hasattr(schemas, "PathNodeResourceRequest")


def test_path_plan_contract_persists_percentage_confidence_and_rationale_items():
    from app.path.schemas import AgentLearningPathPlan, AgentStage, AgentPathNode

    plan = AgentLearningPathPlan(
        title="操作系统进阶路径",
        confidence=82,
        adjustment_rationale=["优先补齐调度基础", "通过练习巩固算法比较"],
        stages=[AgentStage(stage_id="stage-1", title="基础", description="基础阶段")],
        nodes=[AgentPathNode(node_id="n1", stage_id="stage-1", title="节点1")],
    )

    assert plan.confidence == 82
    assert plan.adjustment_rationale == ["优先补齐调度基础", "通过练习巩固算法比较"]


@pytest.mark.asyncio
async def test_path_planner_uses_request_knowledge_preferences_and_plans_all_stages():
    from app.path.agents.planner import PathPlannerAgent
    from app.path.schemas import AgentLearningPathPlan, AgentStage, AgentPathNode, CreateLearningPathRequest

    class CapturingLLM:
        messages = []

        async def ainvoke_json(self, schema, messages):
            self.messages = messages
            return AgentLearningPathPlan(
                title="处理机调度学习路径",
                stages=[AgentStage(stage_id="stage-1", title="调度基础", description="调度基础阶段")],
                nodes=[AgentPathNode(node_id="n1", stage_id="stage-1", title="处理机调度")],
            )

    agent = PathPlannerAgent()
    llm = CapturingLLM()
    agent.llm = llm

    await agent.generate_plan(
        CreateLearningPathRequest(
            goal="掌握调度算法",
            topic="操作系统处理机调度",
            current_knowledge=["进程状态"],
            preferences={"learning_style": "案例驱动"},
        ),
        {"weak_points": ["响应时间计算"]},
    )

    prompt = llm.messages[-1].content
    assert "进程状态" in prompt
    assert "案例驱动" in prompt
    assert "所有阶段" in agent.system_prompt
    assert "仅包含第 1 阶段" not in agent.system_prompt


def test_persisted_resource_item_exposes_real_card_status():
    from types import SimpleNamespace

    from app.resource.service import ResourceService

    item = SimpleNamespace(
        id=1001,
        agent_type="ppt",
        status="completed",
        error_message=None,
        created_at=None,
        updated_at=None,
        content_format="json",
        title="调度算法 PPT",
        summary="教学演示",
        content_json={"content": {"slides": []}},
        content_text=None,
        metadata_json={"agent_id": "ppt"},
        execution_report=None,
    )

    mapped = ResourceService._db_item_to_resource_item(object(), item)

    assert mapped.status == "completed"
    assert mapped.error_message is None
