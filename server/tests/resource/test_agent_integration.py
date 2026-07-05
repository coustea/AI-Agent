"""所有 Agent 集成测试 — mock LLM，验证每个 agent 的 generate_resource 流程和日志输出。"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import patch, AsyncMock

import pytest

from app.resource.agents.base import AGENT_REGISTRY
from app.resource.schemas import ResourceInput


# ── Mock LLM ──────────────────────────────────────────────────────────────


class FakeLlm:
    """统一 mock：支持 ainvoke 和 ainvoke_json。"""

    def __init__(self, text_response: str = "", json_response: Any = None):
        self._text_response = text_response
        self._json_response = json_response
        self.calls: list[dict[str, Any]] = []

    async def ainvoke(self, input_data, *, model=None, temperature=0, max_tokens=None, **kwargs):
        self.calls.append({"method": "ainvoke", "input": input_data, "model": model})
        return _FakeLlmResponse(self._text_response)

    async def ainvoke_json(self, schema, input_data, *, temperature=0, function_name=None, function_description=None, max_tokens=None, **kwargs):
        self.calls.append({
            "method": "ainvoke_json", "schema": schema.__name__,
            "function_name": function_name, "input": input_data,
        })
        if self._json_response is not None:
            return schema.model_validate(self._json_response)
        raise RuntimeError("no json_response configured")


class _FakeLlmResponse:
    def __init__(self, content: str):
        self.content = content


# ── 辅助 ──────────────────────────────────────────────────────────────────


def _make_input(agent_id: str, config: dict[str, Any] | None = None) -> ResourceInput:
    from app.resource.schemas import (
        TeachingPlan,
        TeachingOutlineItem,
        GlobalTeachingPlan,
        WorkerTask,
        AssignedSection,
        WorkerDeliverable,
    )

    teaching_plan = TeachingPlan(
        schema_version="3.0",
        global_plan=GlobalTeachingPlan(
            learning_goal="Python 基础语法",
            teaching_strategy="从基础概念到实际应用",
            difficulty="beginner",
            outline=[
                TeachingOutlineItem(
                    id="o1",
                    title="变量与数据类型",
                    learning_objective="理解 Python 变量和基本数据类型",
                    key_points=["变量定义", "数据类型分类"],
                    must_not_miss=True,
                ),
                TeachingOutlineItem(
                    id="o2",
                    title="控制流",
                    learning_objective="掌握条件判断和循环",
                    key_points=["if-else", "for/while 循环"],
                    must_not_miss=False,
                ),
                TeachingOutlineItem(
                    id="o3",
                    title="函数基础",
                    learning_objective="学会定义和调用函数",
                    key_points=["函数定义", "参数传递"],
                    must_not_miss=False,
                ),
            ],
        ),
        worker_tasks={
            "content": WorkerTask(
                objective="讲解基础概念",
                assigned_sections=[
                    AssignedSection(outline_id="o1", responsibility="primary", instruction="FCFS"),
                ],
                deliverable=WorkerDeliverable(format="markdown", requirements=["Default requirement"]),
                acceptance_criteria=["Default criterion"],
                exclusions=["Default exclusion"],
                avoid_overlap_with=[],
            ),
            "mindmap": WorkerTask(
                objective="生成思维导图",
                assigned_sections=[
                    AssignedSection(outline_id="o1", responsibility="primary", instruction="FCFS"),
                ],
                deliverable=WorkerDeliverable(format="markdown", requirements=["Default requirement"]),
                acceptance_criteria=["Default criterion"],
                exclusions=["Default exclusion"],
                avoid_overlap_with=[],
            ),
            "quiz": WorkerTask(
                objective="生成测验",
                assigned_sections=[
                    AssignedSection(outline_id="o1", responsibility="primary", instruction="FCFS"),
                ],
                deliverable=WorkerDeliverable(format="json", requirements=["Default requirement"]),
                acceptance_criteria=["Default criterion"],
                exclusions=["Default exclusion"],
                avoid_overlap_with=[],
            ),
            "code": WorkerTask(
                objective="生成代码",
                assigned_sections=[
                    AssignedSection(outline_id="o1", responsibility="primary", instruction="FCFS"),
                ],
                deliverable=WorkerDeliverable(format="markdown", requirements=["Default requirement"]),
                acceptance_criteria=["Default criterion"],
                exclusions=["Default exclusion"],
                avoid_overlap_with=[],
            ),
            "reading": WorkerTask(
                objective="生成阅读材料",
                assigned_sections=[
                    AssignedSection(outline_id="o1", responsibility="primary", instruction="FCFS"),
                ],
                deliverable=WorkerDeliverable(format="json", requirements=["Default requirement"]),
                acceptance_criteria=["Default criterion"],
                exclusions=["Default exclusion"],
                avoid_overlap_with=[],
            ),
        },
    )
    return ResourceInput(
        resource_id=1,
        learning_need="Python 基础语法",
        learning_scenario="self_study",
        agent_name=agent_id,
        agent_config=config or {},
        teaching_plan=teaching_plan,
    )


# ── Content Agent ──────────────────────────────────────────────────────────


def test_content_agent_execute_success():
    async def run():
        from app.resource.agents.content import ContentAgent
        agent = ContentAgent(emitter=None)
        agent.llm = FakeLlm(text_response="# Python 基础\n\n变量、数据类型、控制流")
        result = await agent.generate_resource(_make_input("content"))
        assert result.success is True
        assert "Python" in result.content
        assert result.file_type == "markdown"
        assert len(agent.llm.calls) == 1
        assert agent.llm.calls[0]["method"] == "ainvoke"
        _assert_valid_handoff(result, "content")

    asyncio.run(run())


def test_content_agent_with_config():
    async def run():
        from app.resource.agents.content import ContentAgent
        agent = ContentAgent(emitter=None)
        agent.llm = FakeLlm(text_response="## 深度内容\n\n详细讲解")
        config = {"structure": "progressive", "depth_level": "deep", "focus_mode": "key_concepts"}
        result = await agent.generate_resource(_make_input("content", config))
        assert result.success is True
        call_input = str(agent.llm.calls[0]["input"])
        assert "progressive" in call_input
        assert "deep" in call_input

    asyncio.run(run())


# ── Code Agent ─────────────────────────────────────────────────────────────


def test_code_agent_execute_success():
    async def run():
        from app.resource.agents.code import CodeAgent
        agent = CodeAgent(emitter=None)
        agent.llm = FakeLlm(text_response="```python\nprint('hello')\n```")
        result = await agent.generate_resource(_make_input("code", {"language": "python", "case_type": "basic_demo"}))
        assert result.success is True
        assert result.file_type == "markdown"
        assert result.metadata.get("language") == "python"
        assert result.metrics.get("language") == "python"
        _assert_valid_handoff(result, "code")

    asyncio.run(run())


# ── Mindmap Agent ──────────────────────────────────────────────────────────


def test_mindmap_agent_execute_success():
    async def run():
        from app.resource.agents.mindmap import MindmapAgent
        md_content = "# Python\n## 基础语法\n- 变量\n- 数据类型\n## 常见误区\n- 易错：可变对象陷阱"
        agent = MindmapAgent(emitter=None)
        agent.llm = FakeLlm(text_response=md_content)
        result = await agent.generate_resource(_make_input("mindmap"))
        assert result.success is True
        assert result.file_type == "markdown"
        assert "基础语法" in result.metrics.get("branches", [])
        assert len(result.metrics.get("weak_points", [])) > 0
        _assert_valid_handoff(result, "mindmap")

    asyncio.run(run())


# ── Quiz Agent ─────────────────────────────────────────────────────────────


def test_quiz_agent_execute_success():
    async def run():
        from app.resource.agents.quiz import QuizAgent
        fake_llm = FakeLlm()
        fake_llm._json_response = {
            "title": "Python 基础测试",
            "summary": "测试基础语法",
            "questions": [
                {
                    "id": 1, "type": "single_choice",
                    "question": "Python 中哪个关键字用于定义函数？",
                    "options": [
                        {"label": "A", "content": "func"},
                        {"label": "B", "content": "def"},
                        {"label": "C", "content": "function"},
                        {"label": "D", "content": "define"},
                    ],
                    "answer": "B",
                    "explanation": "Python 使用 def 关键字",
                    "difficulty": "basic",
                    "knowledge_points": ["函数定义"],
                },
            ],
        }
        agent = QuizAgent(emitter=None)
        agent.llm = fake_llm
        result = await agent.generate_resource(_make_input("quiz", {"question_count": 1}))
        assert result.success is True
        assert result.file_type == "json"
        assert result.metrics.get("total_count") == 1
        _assert_valid_handoff(result, "quiz")

    asyncio.run(run())


# ── Reading Agent ──────────────────────────────────────────────────────────


def test_reading_agent_execute_success():
    async def run():
        from app.resource.agents.reading import ReadingAgent
        fake_llm = FakeLlm()
        fake_llm._json_response = {
            "title": "Python 拓展阅读",
            "summary": "推荐资源",
            "resources": [
                {
                    "id": "R1", "type": "book", "title": "Python Cookbook",
                    "authors": ["David Beazley"], "url": "",
                    "language": "中文", "difficulty": "medium",
                    "suitable_for": "进阶学习者",
                    "related_knowledge_points": ["基础语法"],
                    "description": "Python 实用技巧", "recommend_reason": "经典",
                    "how_to_use": "按章节阅读", "estimated_time": "4h", "note": "",
                },
            ],
            "learning_path": [{"step": 1, "title": "入门", "description": "", "resource_ids": ["R1"], "goal": ""}],
            "follow_up_suggestions": ["多练习"],
        }
        agent = ReadingAgent(emitter=None)
        agent.llm = fake_llm
        with patch.object(agent, "search", new_callable=AsyncMock) as mock_search:
            from app.shared.research.schemas import ResearchReport, ResearchSourceItem
            mock_search.return_value = ResearchReport(
                query="Python 基础语法 教程",
                sources=[
                    ResearchSourceItem(
                        source="duckduckgo_search",
                        title="Python Cookbook",
                        url="https://example.com",
                        summary="Python Cookbook",
                    )
                ],
            )
            result = await agent.generate_resource(_make_input("reading", {"reading_depth": "course_extended", "max_items": 3}))
        assert result.success is True
        assert result.file_type == "json"
        assert result.metrics.get("resource_count") == 1
        _assert_valid_handoff(result, "reading")

    asyncio.run(run())


# ── Registry 完整性 ────────────────────────────────────────────────────────


def test_all_agents_registered():
    expected = {"content", "mindmap", "code", "quiz", "reading", "ppt", "video", "cartoon", "planning"}
    actual = set(AGENT_REGISTRY.keys())
    assert expected == actual, f"缺少: {expected - actual}, 多余: {actual - expected}"


def test_each_agent_has_required_fields():
    for agent_id, agent_cls in AGENT_REGISTRY.items():
        assert agent_cls.agent_id == agent_id
        assert agent_cls.agent_name, f"{agent_id} 缺少 agent_name"


# ── LLM 异常处理 ──────────────────────────────────────────────────────────


def test_content_agent_llm_failure_raises():
    async def run():
        from app.resource.agents.content import ContentAgent

        class FailLlm:
            async def ainvoke(self, *a, **kw):
                raise RuntimeError("LLM 服务不可用")

        agent = ContentAgent(emitter=None)
        agent.llm = FailLlm()
        with pytest.raises(RuntimeError, match="LLM 服务不可用"):
            await agent.generate_resource(_make_input("content"))

    asyncio.run(run())



from app.resource.schemas import DownstreamContext, TeachingOutlineItem, TeachingPlan, GlobalTeachingPlan, WorkerTask, AssignedSection, WorkerDeliverable


def _sample_teaching_plan() -> TeachingPlan:
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
                TeachingOutlineItem(
                    id="o2",
                    title="三次握手过程",
                    learning_objective="理解流程",
                    key_points=["SYN", "SYN-ACK", "ACK"],
                    must_not_miss=False,
                ),
                TeachingOutlineItem(
                    id="o3",
                    title="三次握手的状态变化",
                    learning_objective="理解状态机",
                    key_points=["LISTEN", "SYN_SENT", "ESTABLISHED"],
                    must_not_miss=False,
                ),
            ],
        ),
        worker_tasks={
            "content": WorkerTask(
                objective="讲解基础概念",
                assigned_sections=[
                    AssignedSection(outline_id="o1", responsibility="primary", instruction="FCFS"),
                ],
                deliverable=WorkerDeliverable(format="markdown", requirements=["Default requirement"]),
                acceptance_criteria=["Default criterion"],
                exclusions=["Default exclusion"],
                avoid_overlap_with=[],
            ),
        }
    )


def _assert_valid_handoff(result: AgentResult, source_agent: str):
    assert result.metadata.get("agent_id") == source_agent
    assert result.title
    assert result.summary
    assert len(result.summary) <= 180


def test_build_resource_context_uses_teaching_plan_and_handoffs_only():
    from app.resource.agents.common import build_resource_context
    from app.resource.schemas import ResourceInput

    plan = _sample_teaching_plan()
    handoff = DownstreamContext(
        source_agent="content",
        title="TCP 内容",
        one_sentence_summary="解释 TCP 三次握手。",
    )

    parts = build_resource_context(
        ResourceInput(
            learning_need="学习 TCP",
            agent_name="content",
            teaching_plan=plan,
            upstream_handoffs={"content": handoff},
        )
    )
    joined = "\n\n".join(parts)

    assert "## 教学计划" in joined
    assert "## 上游交接摘要" in joined
    assert "previous_results" not in joined
    assert "规划师指令" not in joined
