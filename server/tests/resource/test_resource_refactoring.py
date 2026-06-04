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


def test_planning_prompt_describes_learning_blueprint_contract_and_ppt_agent():
    prompt_path = Path(__file__).resolve().parents[2] / "app" / "prompts" / "resource" / "planning.md"
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


# ======================================================================
# 7. Path node resources reuse the unified resource task safely
# ======================================================================


def test_path_node_resource_request_rejects_backend_owned_context_fields():
    from app.path.schemas import PathNodeResourceRequest

    with pytest.raises(ValidationError):
        PathNodeResourceRequest.model_validate(
            {
                "learning_need": "伪造的节点学习需求",
                "profile": {"weakness": "伪造画像"},
                "user_id": 9,
                "node_id": 88,
            }
        )


def test_path_node_resource_request_rejects_unknown_frontend_fields():
    from app.path.schemas import PathNodeResourceRequest

    with pytest.raises(ValidationError):
        PathNodeResourceRequest.model_validate(
            {
                "selected_agents": [],
                "agent_configs": {},
                "output_options": {"output_format": "json"},
            }
        )


def test_path_node_resource_status_defaults_to_not_started():
    from app.infra.models import CoursePathNode

    assert CoursePathNode.model_fields["resource_status"].default == "not_started"


def test_path_generation_task_tracks_real_planning_progress():
    from app.infra.models import CoursePathGenerationTask

    task = CoursePathGenerationTask(user_id=1, goal="掌握处理机调度")

    assert task.status == "pending"
    assert task.progress == 0
    assert task.latest_message == "规划任务已创建，等待开始"
    assert task.generated_path_id is None


def test_path_plan_contract_persists_percentage_confidence_and_rationale_items():
    from app.path.schemas import AgentCoursePathPlan

    plan = AgentCoursePathPlan(
        title="操作系统进阶路径",
        confidence=82,
        adjustment_rationale=["优先补齐调度基础", "通过练习巩固算法比较"],
    )

    assert plan.confidence == 82
    assert plan.adjustment_rationale == ["优先补齐调度基础", "通过练习巩固算法比较"]


@pytest.mark.asyncio
async def test_path_planner_uses_request_knowledge_preferences_and_plans_all_stages():
    from app.path.agents.planner import PathPlannerAgent
    from app.path.schemas import AgentCoursePathPlan, GeneratePathRequest

    class CapturingLLM:
        messages = []

        async def ainvoke_json(self, schema, messages):
            self.messages = messages
            return AgentCoursePathPlan(title="处理机调度学习路径")

    agent = PathPlannerAgent()
    llm = CapturingLLM()
    agent.llm = llm

    await agent.generate_plan(
        GeneratePathRequest(
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


class PathMutationSession:
    def __init__(self, query_results):
        self.query_results = list(query_results)
        self.committed = False

    async def exec(self, statement):
        values = self.query_results.pop(0)

        class Result:
            def __init__(self, rows):
                self.rows = rows if isinstance(rows, list) else [rows]

            def first(self):
                return self.rows[0] if self.rows else None

            def all(self):
                return self.rows

        return Result(values)

    async def commit(self):
        self.committed = True


def make_path_node(**overrides):
    from types import SimpleNamespace

    data = {
        "id": 1,
        "path_id": 100,
        "user_id": 9,
        "node_id": "foundation",
        "stage_id": "stage-1",
        "title": "调度基础",
        "status": "available",
        "resource_status": "ready",
        "progress": 0,
        "priority": 1,
        "prerequisites": [],
        "mastery_target": "理解调度目标",
        "estimated_minutes": 20,
        "difficulty": "beginner",
        "recommendation_reason": "先建立基础",
        "started_at": None,
        "completed_at": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def make_course_path():
    from types import SimpleNamespace

    return SimpleNamespace(
        id=100,
        module="mentor",
        title="调度学习路径",
        goal="掌握调度算法",
        overall_progress=0,
        current_stage_id="stage-1",
        current_node_id="foundation",
        eta_days=7,
        confidence=82,
        status="active",
        stages_json=[],
        created_at=None,
    )


@pytest.mark.asyncio
async def test_start_path_node_marks_ready_node_in_progress():
    from app.path.service import CoursePathService

    node = make_path_node()
    path = make_course_path()
    session = PathMutationSession([node, path, [node], []])
    service = object.__new__(CoursePathService)
    service.session = session

    response = await service.start_node(user_id=9, node_id=1)

    assert node.status == "in_progress"
    assert node.started_at is not None
    assert path.current_node_id == "foundation"
    assert response.nodes[0].status == "in_progress"
    assert session.committed is True


@pytest.mark.asyncio
async def test_complete_path_node_unlocks_successor_and_updates_path_progress():
    from app.path.service import CoursePathService

    current = make_path_node(status="in_progress", progress=20)
    successor = make_path_node(
        id=2,
        node_id="rr",
        title="时间片轮转",
        status="locked",
        resource_status="not_started",
        prerequisites=["foundation"],
    )
    path = make_course_path()
    session = PathMutationSession([current, path, [current, successor], []])
    service = object.__new__(CoursePathService)
    service.session = session

    response = await service.complete_node(user_id=9, node_id=1)

    assert current.status == "completed"
    assert current.progress == 100
    assert successor.status == "available"
    assert path.overall_progress == 50
    assert path.current_node_id == "rr"
    assert [node.status for node in response.nodes] == ["completed", "available"]


@pytest.mark.asyncio
async def test_completing_last_path_node_keeps_current_path_readable_until_replanned():
    from app.path.service import CoursePathService

    node = make_path_node(status="in_progress")
    path = make_course_path()
    session = PathMutationSession([node, path, [node], []])
    service = object.__new__(CoursePathService)
    service.session = session

    await service.complete_node(user_id=9, node_id=1)

    assert path.overall_progress == 100
    assert path.status == "active"


@pytest.mark.asyncio
async def test_path_endpoint_reuses_ready_resource_without_rescheduling(monkeypatch):
    from types import SimpleNamespace

    from fastapi import BackgroundTasks

    from app.path import api
    from app.path.schemas import PathNodeResourceRequest

    class FakeService:
        def __init__(self, session):
            pass

        async def generate_node_resources(self, **kwargs):
            return {
                "resource_id": 31,
                "node_id": 7,
                "status": "ready",
                "should_schedule": False,
            }

    monkeypatch.setattr(api, "CoursePathService", FakeService)
    tasks = BackgroundTasks()
    response = await api.generate_node_resources(
        node_id=7,
        payload=PathNodeResourceRequest(),
        background_tasks=tasks,
        current_user=SimpleNamespace(id=1),
        session=object(),
    )

    assert response["data"]["status"] == "ready"
    assert tasks.tasks == []


@pytest.mark.asyncio
async def test_path_generate_endpoint_queues_background_task_instead_of_waiting_for_plan(monkeypatch):
    from types import SimpleNamespace

    from fastapi import BackgroundTasks

    from app.path import api
    from app.path.schemas import GeneratePathRequest, PathGenerationTaskResponse

    class FakeService:
        def __init__(self, session):
            pass

        async def start_generation_task(self, *, user_id, request):
            return {
                "task": PathGenerationTaskResponse(
                    task_id=77,
                    module=request.module,
                    goal=request.goal,
                    status="pending",
                    progress=0,
                    latest_message="规划任务已创建，等待开始",
                ),
                "should_schedule": True,
            }

    async def fake_bg_task(task_id):
        return task_id

    monkeypatch.setattr(api, "CoursePathService", FakeService)
    monkeypatch.setattr(api, "bg_generate_path_task", fake_bg_task)
    tasks = BackgroundTasks()

    response = await api.generate_path(
        request=GeneratePathRequest(goal="掌握调度算法"),
        background_tasks=tasks,
        current_user=SimpleNamespace(id=1),
        session=object(),
    )

    assert response["data"]["task_id"] == 77
    assert response["data"]["status"] == "pending"
    assert len(tasks.tasks) == 1


@pytest.mark.asyncio
async def test_path_task_creation_reuses_active_task_without_duplicate_schedule():
    from app.infra.models import CoursePathGenerationTask
    from app.path.schemas import GeneratePathRequest
    from app.path.service import CoursePathService

    active_task = CoursePathGenerationTask(
        id=16,
        user_id=1,
        module="mentor",
        goal="旧目标",
        status="planning",
        progress=30,
        latest_message="路径规划智能体正在编排学习节点",
    )

    class Result:
        def first(self):
            return active_task

    class FakeSession:
        async def exec(self, statement):
            return Result()

    service = object.__new__(CoursePathService)
    service.session = FakeSession()

    result = await service.start_generation_task(
        user_id=1,
        request=GeneratePathRequest(goal="新目标", module="mentor"),
    )

    assert result["task"].task_id == 16
    assert result["task"].status == "planning"
    assert result["should_schedule"] is False


@pytest.mark.asyncio
async def test_start_path_resource_task_binds_active_task_before_generation():
    from types import SimpleNamespace

    from app.infra.models import CoursePathNode, CoursePathResourceBinding, GeneratedResource
    from app.resource.service import ResourceUsecases

    node = SimpleNamespace(user_id=1, resource_status="not_started")

    class EmptyResult:
        def first(self):
            return None

    class FakeSession:
        def __init__(self):
            self.added: list[object] = []

        def add(self, value):
            self.added.append(value)

        async def flush(self):
            for value in self.added:
                if isinstance(value, GeneratedResource):
                    value.id = 42

        async def get(self, model, object_id):
            if model is CoursePathNode and object_id == 8:
                return node
            return None

        async def exec(self, statement):
            return EmptyResult()

        async def commit(self):
            return None

        async def rollback(self):
            return None

        async def refresh(self, value):
            return None

    session = FakeSession()
    result = await ResourceUsecases(session).start_resource_task(
        user_id=1,
        request=ResourceGenerationRequest(learning_need="处理机调度"),
        source="path_node",
        node_id=8,
        profile={},
    )

    binding = next(value for value in session.added if isinstance(value, CoursePathResourceBinding))
    assert result["resource_id"] == 42
    assert binding.resource_id == 42
    assert node.resource_status == "generating"


def test_persisted_resource_item_exposes_real_card_status():
    from types import SimpleNamespace

    from app.resource.service import ResourceUsecases

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

    mapped = ResourceUsecases._db_item_to_resource_item(object(), item)

    assert mapped.status == "completed"
    assert mapped.error_message is None
