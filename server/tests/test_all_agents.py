# -*- coding: utf-8 -*-
"""验证所有 Agent 类和核心 schema 可正常导入与实例化。"""

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.resource.schemas import ResourcePlan, DownstreamContext, AgentResult
from app.resource.agents.content import ContentAgent
from app.resource.agents.mindmap import MindmapAgent
from app.resource.agents.quiz import QuizAgent
from app.resource.agents.code import CodeAgent
from app.resource.agents.reading import ReadingAgent
from app.resource.agents.ppt import PPTAgent as PptAgent
from app.resource.agents.video import VideoAgent
from app.resource.agents.planning import PlanningAgent


def test_core_schemas_exist():
    """ResourcePlan, DownstreamContext, AgentResult 必须可用。"""
    assert hasattr(ResourcePlan, "model_validate")
    assert hasattr(DownstreamContext, "model_validate")
    assert hasattr(AgentResult, "model_validate")


def test_resource_plan_validates():
    plan = ResourcePlan(
        content="# 资源生成协同计划\n\n## 1. 用户需求理解\n- 理解三次握手\n\n### [content]\n- 生成目标：讲解TCP三次握手\n- 重点聚焦：流程\n- 必须包含：时序图\n- 应避免：拥塞控制\n\n### [mindmap]\n- 生成目标：知识结构\n- 重点聚焦：TCP连接\n- 必须包含：握手步骤\n- 应避免：重复讲解",
        title="TCP三次握手",
    )
    assert plan.agent_ids == ["content", "mindmap"]
    assert plan.has_agent("content")
    assert not plan.has_agent("quiz")


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
        VideoAgent,
        PlanningAgent,
    ]
    for cls in agent_classes:
        agent = cls()
        assert hasattr(agent, "generate_resource") or hasattr(agent, "generate_node")
