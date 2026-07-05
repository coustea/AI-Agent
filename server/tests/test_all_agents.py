# -*- coding: utf-8 -*-
"""验证所有 Agent 类和核心 schema 可正常导入与实例化。"""

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.resource.schemas import TeachingPlan, DownstreamContext, AgentResult, ReusableAssets
from app.resource.agents.content import ContentAgent
from app.resource.agents.mindmap import MindmapAgent
from app.resource.agents.quiz import QuizAgent
from app.resource.agents.code import CodeAgent
from app.resource.agents.reading import ReadingAgent
from app.resource.agents.ppt import PPTAgent as PptAgent
from app.resource.agents.video import VideoAgent
from app.resource.agents.planning import PlanningAgent


def test_core_schemas_exist():
    """TeachingPlan, DownstreamContext, AgentResult 必须可用。"""
    assert hasattr(TeachingPlan, "model_validate")
    assert hasattr(DownstreamContext, "model_validate")
    assert hasattr(AgentResult, "model_validate")


def test_teaching_plan_validates():
    plan = TeachingPlan.model_validate({
        "schema_version": "3.0",
        "global_plan": {
            "learning_goal": "理解三次握手和可靠传输",
            "teaching_strategy": "先直观类比，再协议细节",
            "difficulty": "beginner",
            "outline": [
                {
                    "id": "o1",
                    "title": "TCP 要解决的问题",
                    "learning_objective": "理解可靠传输的目标",
                    "key_points": ["连接", "确认", "重传"],
                    "must_not_miss": True,
                },
                {
                    "id": "o2",
                    "title": "三次握手流程",
                    "learning_objective": "理解握手流程",
                    "key_points": ["SYN", "ACK"],
                    "must_not_miss": True,
                },
                {
                    "id": "o3",
                    "title": "可靠传输实现",
                    "learning_objective": "理解重传机制",
                    "key_points": ["滑动窗口"],
                    "must_not_miss": False,
                }
            ]
        },
        "worker_tasks": {
            "content": {
                "objective": "编写讲解文本",
                "assigned_sections": [
                    {
                        "outline_id": "o1",
                        "responsibility": "primary",
                        "instruction": "详细讲解可靠传输目标"
                    },
                    {
                        "outline_id": "o2",
                        "responsibility": "supporting",
                        "instruction": "配合图解流程"
                    }
                ],
                "deliverable": {
                    "format": "markdown",
                    "requirements": ["字数不少于500字"]
                },
                "acceptance_criteria": ["大纲点全覆盖"],
                "exclusions": ["不谈拥塞控制"],
                "avoid_overlap_with": []
            }
        }
    })
    assert plan.outline[0].id == "o1"


def test_downstream_context_validates():
    ctx = DownstreamContext(
        source_agent="content",
        title="TCP 内容",
        one_sentence_summary="讲解 TCP 三次握手",
        reusable_assets=ReusableAssets(
            examples=["电话拨通比喻"],
            misconceptions=["两次握手足够"],
            visual_ideas=["时序箭线图"],
            practice_refs=[],
            code_refs=[]
        )
    )
    assert ctx.source_agent == "content"
    assert ctx.title == "TCP 内容"


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
