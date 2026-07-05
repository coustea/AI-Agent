import pytest
import json
from pydantic import ValidationError

from app.resource.schemas import (
    AgentResult,
    DownstreamContext,
    ResourceInput,
    ReusableAssets,
    TeachingOutlineItem,
    TeachingPlan,
    GlobalTeachingPlan,
    WorkerTask,
    AssignedSection,
    WorkerDeliverable,
)
from app.resource.agents.planning import PlanningAgent


def create_mock_teaching_plan() -> TeachingPlan:
    return TeachingPlan(
        schema_version="3.0",
        global_plan=GlobalTeachingPlan(
            learning_goal="理解三次握手",
            teaching_strategy="逐步引入",
            difficulty="beginner",
            outline=[
                TeachingOutlineItem(
                    id="o1",
                    title="为什么需要三次握手",
                    learning_objective="理解目的",
                    key_points=["确认双方收发能力"],
                    must_not_miss=True,
                ),
            ],
        ),
        worker_tasks={
            "content": WorkerTask(
                objective="讲解基础概念",
                assigned_sections=[
                    AssignedSection(outline_id="o1", responsibility="primary", instruction="FCFS"),
                ],
                deliverable=WorkerDeliverable(format="markdown", requirements=[]),
                acceptance_criteria=[],
                exclusions=[],
                avoid_overlap_with=[],
            )
        }
    )


def test_teaching_plan_has_global_direction_and_outline():
    plan = create_mock_teaching_plan()
    dumped = plan.model_dump(mode="json")

    assert dumped["schema_version"] == "3.0"
    assert dumped["global_plan"]["outline"][0]["id"] == "o1"


def test_downstream_context_is_bounded_and_outline_mapped():
    ctx = DownstreamContext(
        source_agent="content",
        title="TCP 三次握手讲解",
        one_sentence_summary="解释三次握手的目的、流程和常见误区。",
        materials=["o1", "o2"],
        reusable_assets=ReusableAssets(
            examples=["打电话确认双方能听能说"],
            misconceptions=["三次握手不是身份认证"],
            visual_ideas=["客户端和服务端时序图"],
        ),
    )

    assert ctx.source_agent == "content"
    assert ctx.materials == ["o1", "o2"]


def test_downstream_context_accepts_oversized_excerpt():
    ctx = DownstreamContext(
        source_agent="content",
        one_sentence_summary="x" * 1000,
    )
    assert len(ctx.one_sentence_summary) == 1000


def test_resource_input_uses_teaching_plan_and_handoffs_only():
    plan = create_mock_teaching_plan()
    handoff = DownstreamContext(source_agent="content", title="内容", one_sentence_summary="讲解 TCP")
    resource_input = ResourceInput(
        resource_id=1,
        learning_need="学习 TCP",
        agent_name="video",
        teaching_plan=plan,
        upstream_handoffs={"content": handoff},
    )

    dumped = resource_input.model_dump(mode="json")

    assert "teaching_plan" in dumped
    assert dumped["teaching_plan"]["outline"] == plan.outline
    assert set(dumped["upstream_handoffs"].keys()) == {"content"}
    assert "blueprint" not in dumped
    assert "instruction" not in dumped
    assert "previous_results" not in dumped


def test_agent_result_fields():
    result = AgentResult(
        success=True,
        content="# TCP",
        file_type="markdown",
        title="TCP 内容",
        summary="生成内容",
        metrics={"char_count": 5},
        metadata={"agent_id": "content"},
    )

    dumped = result.model_dump(mode="json")

    assert dumped["metrics"]["char_count"] == 5
    assert dumped["title"] == "TCP 内容"
    assert "summary_data" not in dumped


@pytest.mark.asyncio
async def test_planning_agent_returns_teaching_plan_without_agent_instructions(monkeypatch):
    call_count = 0

    # Mock response models
    incorrect_plan = create_mock_teaching_plan()
    incorrect_plan.worker_tasks = {}  # Empty worker tasks triggers ValueError: worker tasks do not match selected base Agents

    correct_plan = create_mock_teaching_plan()
    # Mock selected base agents: "content", "mindmap"
    correct_plan.worker_tasks = {
        "content": WorkerTask(
            objective="obj",
            assigned_sections=[AssignedSection(outline_id="o1", responsibility="primary", instruction="FCFS")],
            deliverable=WorkerDeliverable(format="markdown", requirements=[]),
            acceptance_criteria=[],
            exclusions=[],
            avoid_overlap_with=[],
        ),
        "mindmap": WorkerTask(
            objective="obj2",
            assigned_sections=[AssignedSection(outline_id="o1", responsibility="primary", instruction="FCFS")],
            deliverable=WorkerDeliverable(format="markdown", requirements=[]),
            acceptance_criteria=[],
            exclusions=[],
            avoid_overlap_with=[],
        ),
    }

    class FakeLlm:
        async def ainvoke_json(self, model, message, **kwargs):
            nonlocal call_count
            call_count += 1
            assert model is TeachingPlan
            assert "为每个启用的资源 Agent" not in message
            if call_count == 1:
                return incorrect_plan
            return correct_plan

    agent = PlanningAgent()
    agent.llm = FakeLlm()

    result = await agent.generate_resource(
        ResourceInput(
            resource_id=1,
            learning_need="学习 TCP 三次握手",
            agent_config={"enabled_agents": ["content", "mindmap"]},
        )
    )

    payload = json.loads(result.content)

    assert result.success is True
    assert result.downstream_context is None
    assert result.metadata["agent_id"] == "planning"
    assert result.metadata["teaching_plan"]["teaching_strategy"] != ""
    assert call_count == 2  # 首次失败触发了一次重试
