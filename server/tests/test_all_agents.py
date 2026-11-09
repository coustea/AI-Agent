# -*- coding: utf-8 -*-
"""验证所有 Agent 类和核心 schema 可正常导入与实例化。"""

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.resource.schemas import ResourcePlan, DownstreamContext, AgentResult, ResourcePlanTask
from app.resource.agents import (
    ContentAgent,
    MindmapAgent,
    QuizAgent,
    CodeAgent,
    ReadingAgent,
    PPTAgent as PptAgent,
    PlanningAgent,
)


def test_core_schemas_exist():
    """ResourcePlan, DownstreamContext, AgentResult 必须可用。"""
    assert hasattr(ResourcePlan, "model_validate")
    assert hasattr(DownstreamContext, "model_validate")
    assert hasattr(AgentResult, "model_validate")


def test_resource_plan_validates():
    plan = ResourcePlan(
        schema_version=1,
        learner_goal="掌握TCP三次握手与四次挥手的核心原理与状态流转过程",
        scope=["三次握手流程", "SYN/ACK标志位", "连接建立状态"],
        tasks=[
            ResourcePlanTask(
                agent_id="content",
                objective="系统化梳理TCP握手的状态迁移与报文结构",
                focus=["状态迁移", "报文序列号"],
                required_elements=["SYN标志位", "ACK标志位"],
                avoid=["拥塞控制算法"],
            ),
            ResourcePlanTask(
                agent_id="mindmap",
                objective="构建TCP握手整体知识脉络与关联考点思维导图",
                focus=["知识架构", "关键步骤"],
                required_elements=["三次握手结构"],
                avoid=["细节过度展开"],
            ),
        ],
    )
    assert plan.agent_ids == ["content", "mindmap"]
    assert "content" in plan.agent_ids
    assert "quiz" not in plan.agent_ids


def test_downstream_context_validates():
    ctx = DownstreamContext(
        source_agent="content",
        title="TCP 内容",
        one_sentence_summary="讲解 TCP 三次握手",
        materials=["电话拨通比喻", "时序箭线图"],
    )
    assert ctx.source_agent == "content"
    assert ctx.title == "TCP 内容"
    assert len(ctx.materials) == 2


def test_agent_result_rejects_unknown_fields():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        AgentResult.model_validate({
            "success": True,
            "content": "hello",
            "previous_results": {},
        })


def test_all_agents_instantiable():
    """每个 Agent 类应该可以无参数实例化。"""
    agent_classes = [
        ContentAgent,
        MindmapAgent,
        QuizAgent,
        CodeAgent,
        ReadingAgent,
        PptAgent,
        PlanningAgent,
    ]
    for cls in agent_classes:
        agent = cls()
        assert hasattr(agent, "generate_resource") or hasattr(agent, "generate_node")
