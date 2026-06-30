import pytest
from pydantic import ValidationError

from app.resource.schemas import (
    AgentResult,
    DownstreamContext,
    ResourceInput,
    ReusableAssets,
    TeachingOutlineItem,
    TeachingPlan,
)


def test_teaching_plan_has_only_global_direction_and_outline():
    plan = TeachingPlan(
        teaching_strategy="问题引入 -> 流程讲解 -> 误区辨析 -> 练习巩固",
        outline=[
            TeachingOutlineItem(
                id="o1",
                title="为什么需要三次握手",
                goal="理解连接建立前双方需要确认通信能力和初始状态",
                key_points=["确认客户端发送能力", "确认服务端接收和发送能力"],
                common_misconceptions=["三次握手不是身份认证"],
                suggested_examples=["打电话确认双方能听能说"],
                suggested_visuals=["时序图"],
                must_not_miss=True,
            )
        ],
    )

    dumped = plan.model_dump(mode="json")

    assert "agent_instructions" not in dumped
    assert "resource_guidance" not in dumped
    assert dumped["outline"][0]["id"] == "o1"


def test_downstream_context_is_bounded_and_outline_mapped():
    ctx = DownstreamContext(
        source_agent="content",
        title="TCP 三次握手讲解",
        one_sentence_summary="解释三次握手的目的、流程和常见误区。",
        covered_outline_ids=["o1", "o2"],
        reusable_assets=ReusableAssets(
            examples=["打电话确认双方能听能说"],
            misconceptions=["三次握手不是身份认证"],
            visual_ideas=["客户端和服务端时序图"],
        ),
    )

    assert ctx.source_agent == "content"
    assert ctx.covered_outline_ids == ["o1", "o2"]


def test_downstream_context_accepts_oversized_excerpt():
    ctx = DownstreamContext(
        source_agent="content",
        one_sentence_summary="x" * 1000,
    )
    assert len(ctx.one_sentence_summary) == 1000


def test_resource_input_uses_teaching_plan_and_handoffs_only():
    plan = TeachingPlan(outline=[])
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
    assert dumped["teaching_plan"]["outline"] == []
    assert set(dumped["upstream_handoffs"].keys()) == {"content"}
    assert "blueprint" not in dumped
    assert "instruction" not in dumped
    assert "previous_results" not in dumped


def test_agent_result_uses_metrics_and_downstream_context():
    handoff = DownstreamContext(source_agent="content", title="内容", one_sentence_summary="讲解 TCP")
    result = AgentResult(
        success=True,
        content="# TCP",
        file_type="markdown",
        title="TCP 内容",
        summary="生成内容",
        metrics={"char_count": 5},
        downstream_context=handoff,
        metadata={"agent_id": "content"},
    )

    dumped = result.model_dump(mode="json")

    assert dumped["metrics"]["char_count"] == 5
    assert dumped["downstream_context"]["source_agent"] == "content"
    assert "summary_data" not in dumped


import json

import pytest

from app.resource.agents.planning import PlanningAgent
from app.resource.schemas import ResourceInput, TeachingPlan


@pytest.mark.asyncio
async def test_planning_agent_returns_teaching_plan_without_agent_instructions(monkeypatch):
    from app.resource.schemas.plan import AgentAssignment

    call_count = 0

    class FakeLlm:
        async def ainvoke_json(self, model, message, **kwargs):
            nonlocal call_count
            call_count += 1
            assert model is TeachingPlan
            assert "为每个启用的资源 Agent" not in message
            # 首次返回空 assignments 触发重试，重试返回完整 assignments
            if call_count == 1:
                return TeachingPlan(
                    teaching_strategy="先直观类比，再协议细节",
                    outline=[],
                )
            return TeachingPlan(
                teaching_strategy="先直观类比，再协议细节",
                outline=[],
                agent_assignments=[
                    AgentAssignment(agent_id="content", assigned_outline_ids=[]),
                    AgentAssignment(agent_id="mindmap", assigned_outline_ids=[]),
                    AgentAssignment(agent_id="ppt", assigned_outline_ids=[]),
                    AgentAssignment(agent_id="video", assigned_outline_ids=[]),
                ],
            )

    agent = PlanningAgent()
    agent.llm = FakeLlm()

    result = await agent.generate_resource(
        ResourceInput(
            resource_id=1,
            learning_need="学习 TCP 三次握手",
            agent_config={"enabled_agents": ["content", "mindmap", "ppt", "video"]},
        )
    )

    payload = json.loads(result.content)

    assert result.success is True
    assert result.downstream_context is None
    assert result.metadata["agent_id"] == "planning"
    assert result.metadata["teaching_plan"]["teaching_strategy"] != ""
    assert "agent_instructions" not in payload
    assert call_count == 2  # 首次空 assignments 触发了一次重试

