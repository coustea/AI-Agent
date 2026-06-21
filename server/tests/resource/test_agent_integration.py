"""所有 Agent 集成测试 — mock LLM，验证每个 agent 的 generate_resource 流程和日志输出。"""

from __future__ import annotations

import asyncio
from typing import Any

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

    async def ainvoke(self, input_data, *, model=None, temperature=0, max_tokens=None):
        self.calls.append({"method": "ainvoke", "input": input_data, "model": model})
        return _FakeLlmResponse(self._text_response)

    async def ainvoke_json(self, schema, input_data, *, temperature=0, function_name=None, function_description=None, max_tokens=None):
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
    from app.resource.schemas import TeachingPlan, TeachingOutlineItem, AgentAssignment

    teaching_plan = TeachingPlan(
        teaching_strategy="从基础概念到实际应用",
        outline=[
            TeachingOutlineItem(
                id="o1",
                title="变量与数据类型",
                goal="理解 Python 变量和基本数据类型",
                key_points=["变量定义", "数据类型分类"],
                must_not_miss=True,
            ),
            TeachingOutlineItem(
                id="o2",
                title="控制流",
                goal="掌握条件判断和循环",
                key_points=["if-else", "for/while 循环"],
                must_not_miss=False,
            ),
            TeachingOutlineItem(
                id="o3",
                title="函数基础",
                goal="学会定义和调用函数",
                key_points=["函数定义", "参数传递"],
                must_not_miss=False,
            ),
        ],
        agent_assignments=[
            AgentAssignment(
                agent_id="content",
                assigned_outline_ids=["o1", "o2", "o3"],
                focus_instruction="讲解基础概念",
                style_constraint="案例驱动",
            ),
        ],
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
        _assert_valid_handoff(result.downstream_context, "content")

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
        _assert_valid_handoff(result.downstream_context, "code")

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
        _assert_valid_handoff(result.downstream_context, "mindmap")

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
                    "difficulty": "easy",
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
        _assert_valid_handoff(result.downstream_context, "quiz")

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
        result = await agent.generate_resource(_make_input("reading", {"reading_depth": "course_extended", "max_items": 3}))
        assert result.success is True
        assert result.file_type == "json"
        assert result.metrics.get("resource_count") == 1
        _assert_valid_handoff(result.downstream_context, "reading")

    asyncio.run(run())


# ── PPT Agent ──────────────────────────────────────────────────────────────


def test_ppt_agent_execute_success():
    """PPT Agent 使用新的两阶段架构生成课件。"""
    async def run():
        from app.resource.agents.ppt import PptAgent
        from app.resource.ppt_contract import (
            DeckBlueprint, ChapterBlueprint, SlideBlueprint,
            CompiledDeck, CompiledChapter, CompiledSlide,
            CompiledBlock, BlockBudget,
            ChapterDraft, SlideContentDraft,
            TextBlock, KeyPointBlock,
        )
        from unittest.mock import AsyncMock, patch

        blueprint = DeckBlueprint(
            template_id="teaching-lesson",
            theme_id="logic-blue",
            title="Python 基础",
            audience="计算机专业学生",
            narrative="从语法基础到实践应用",
            primary_example="Python 变量定义",
            terminology={"变量": "存储数据的容器"},
            chapters=[
                ChapterBlueprint(
                    chapter_id="ch1",
                    title="变量基础",
                    objective="帮助学生理解变量的概念",
                    slides=[
                        SlideBlueprint(
                            slide_id="slide-01",
                            index=1,
                            role="cover",
                            title="Python 基础",
                            teaching_intent="介绍本节课的主题内容",
                            unique_value="课件封面",
                            composition_id="cover-slide",
                        ),
                        SlideBlueprint(
                            slide_id="slide-02",
                            index=2,
                            role="objectives",
                            title="学习目标",
                            teaching_intent="明确本节的学习目标",
                            unique_value="学习目标页",
                            composition_id="learning-objectives",
                        ),
                        SlideBlueprint(
                            slide_id="slide-03",
                            index=3,
                            role="concept",
                            title="变量定义",
                            teaching_intent="讲解变量的核心概念",
                            unique_value="核心概念讲解",
                            composition_id="core-concept",
                        ),
                        SlideBlueprint(
                            slide_id="slide-04",
                            index=4,
                            role="summary",
                            title="本节小结",
                            teaching_intent="总结本节课的核心内容",
                            unique_value="知识框架总结",
                            composition_id="knowledge-summary",
                        ),
                    ],
                ),
                ChapterBlueprint(
                    chapter_id="ch2",
                    title="数据类型",
                    objective="理解 Python 的基本数据类型",
                    slides=[
                        SlideBlueprint(
                            slide_id="slide-05",
                            index=5,
                            role="concept",
                            title="数据类型概述",
                            teaching_intent="介绍 Python 的基本数据类型",
                            unique_value="数据类型概念",
                            composition_id="core-concept",
                        ),
                        SlideBlueprint(
                            slide_id="slide-06",
                            index=6,
                            role="summary",
                            title="章节总结",
                            teaching_intent="总结变量与数据类型",
                            unique_value="章节收尾",
                            composition_id="knowledge-summary",
                        ),
                    ],
                ),
            ],
        )

        compiled = CompiledDeck(
            template_id="teaching-lesson",
            theme_id="logic-blue",
            title="Python 基础",
            audience="计算机专业学生",
            chapters=[
                CompiledChapter(
                    chapter_id="ch1",
                    title="变量基础",
                    objective="帮助学生理解变量的概念",
                    slides=[
                        CompiledSlide(
                            slide_id="slide-01",
                            index=1,
                            role="cover",
                            title="Python 基础",
                            subtitle=None,
                            teaching_intent="介绍本节课的主题内容",
                            unique_value="课件封面",
                            layout="HeroCover",
                            blocks=[
                                CompiledBlock(
                                    block_id="course-title",
                                    slot="main",
                                    type="Text",
                                    instruction="课程标题",
                                    budget=BlockBudget(max_chars=120),
                                ),
                                CompiledBlock(
                                    block_id="topic-title",
                                    slot="main",
                                    type="KeyPoint",
                                    instruction="主题标签",
                                    budget=BlockBudget(max_chars=64),
                                ),
                            ],
                        ),
                        CompiledSlide(
                            slide_id="slide-02",
                            index=2,
                            role="objectives",
                            title="学习目标",
                            subtitle=None,
                            teaching_intent="明确本节的学习目标",
                            unique_value="学习目标页",
                            layout="HeroCover",
                            blocks=[
                                CompiledBlock(
                                    block_id="objective-summary",
                                    slot="main",
                                    type="KeyPoint",
                                    instruction="学习目标",
                                    budget=BlockBudget(max_chars=64),
                                ),
                            ],
                        ),
                        CompiledSlide(
                            slide_id="slide-03",
                            index=3,
                            role="concept",
                            title="变量定义",
                            subtitle=None,
                            teaching_intent="讲解变量的核心概念",
                            unique_value="核心概念讲解",
                            layout="HeroCover",
                            blocks=[
                                CompiledBlock(
                                    block_id="definition",
                                    slot="main",
                                    type="Text",
                                    instruction="变量定义",
                                    budget=BlockBudget(max_chars=120),
                                ),
                            ],
                        ),
                        CompiledSlide(
                            slide_id="slide-04",
                            index=4,
                            role="summary",
                            title="本节小结",
                            subtitle=None,
                            teaching_intent="总结本节课的核心内容",
                            unique_value="知识框架总结",
                            layout="HeroCover",
                            blocks=[
                                CompiledBlock(
                                    block_id="summary-highlight",
                                    slot="main",
                                    type="KeyPoint",
                                    instruction="总结要点",
                                    budget=BlockBudget(max_chars=64),
                                ),
                            ],
                        ),
                    ],
                ),
                CompiledChapter(
                    chapter_id="ch2",
                    title="数据类型",
                    objective="理解 Python 的基本数据类型",
                    slides=[
                        CompiledSlide(
                            slide_id="slide-05",
                            index=5,
                            role="concept",
                            title="数据类型概述",
                            subtitle=None,
                            teaching_intent="介绍 Python 的基本数据类型",
                            unique_value="数据类型概念",
                            layout="HeroCover",
                            blocks=[
                                CompiledBlock(
                                    block_id="type-intro",
                                    slot="main",
                                    type="Text",
                                    instruction="数据类型介绍",
                                    budget=BlockBudget(max_chars=120),
                                ),
                            ],
                        ),
                        CompiledSlide(
                            slide_id="slide-06",
                            index=6,
                            role="summary",
                            title="章节总结",
                            subtitle=None,
                            teaching_intent="总结变量与数据类型",
                            unique_value="章节收尾",
                            layout="HeroCover",
                            blocks=[
                                CompiledBlock(
                                    block_id="final-summary",
                                    slot="main",
                                    type="KeyPoint",
                                    instruction="最终总结",
                                    budget=BlockBudget(max_chars=64),
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )

        draft_ch1 = ChapterDraft(
            chapter_id="ch1",
            slides=[
                SlideContentDraft(
                    slide_id="slide-01",
                    blocks=[
                        TextBlock(block_id="course-title", type="Text", content="Python 基础", format="plain"),
                        KeyPointBlock(block_id="topic-title", type="KeyPoint", label="主题", content="变量与数据类型"),
                    ],
                    takeaway="Python 基础入门",
                    speaker_notes="欢迎学习 Python 基础课程，今天我们将学习变量与数据类型。",
                ),
                SlideContentDraft(
                    slide_id="slide-02",
                    blocks=[
                        KeyPointBlock(block_id="objective-summary", type="KeyPoint", label="目标", content="掌握变量定义"),
                    ],
                    takeaway="明确学习目标",
                    speaker_notes="本节的学习目标是理解并掌握 Python 变量的定义和使用。",
                ),
                SlideContentDraft(
                    slide_id="slide-03",
                    blocks=[
                        TextBlock(block_id="definition", type="Text", content="变量是存储数据的容器", format="plain"),
                    ],
                    takeaway="理解变量概念",
                    speaker_notes="变量是程序中存储数据的基本单元，让我们通过示例来理解。",
                ),
                SlideContentDraft(
                    slide_id="slide-04",
                    blocks=[
                        KeyPointBlock(block_id="summary-highlight", type="KeyPoint", label="总结", content="变量是基础"),
                    ],
                    takeaway="回顾本节要点",
                    speaker_notes="本节我们学习了变量的基本概念，下节将学习数据类型。",
                ),
            ],
        )

        draft_ch2 = ChapterDraft(
            chapter_id="ch2",
            slides=[
                SlideContentDraft(
                    slide_id="slide-05",
                    blocks=[
                        TextBlock(block_id="type-intro", type="Text", content="Python 有多种数据类型", format="plain"),
                    ],
                    takeaway="认识数据类型",
                    speaker_notes="Python 支持多种数据类型，包括整数、浮点数、字符串等。",
                ),
                SlideContentDraft(
                    slide_id="slide-06",
                    blocks=[
                        KeyPointBlock(block_id="final-summary", type="KeyPoint", label="总结", content="掌握基础类型"),
                    ],
                    takeaway="课程总结",
                    speaker_notes="本课程介绍了变量和数据类型，这是 Python 编程的基础。",
                ),
            ],
        )

        with patch("app.resource.agents.ppt.DeckDirectorAgent") as MockDirector, \
             patch("app.resource.agents.ppt.ChapterWriterAgent") as MockWriter, \
             patch("app.resource.agents.ppt.compile_deck", return_value=compiled):

            MockDirector.return_value.run = AsyncMock(return_value=blueprint)
            MockWriter.return_value.run = AsyncMock(side_effect=[draft_ch1, draft_ch2])

            agent = PptAgent(emitter=None)
            result = await agent.generate_resource(_make_input("ppt", {"lesson_depth": "quick"}))
            assert result.success is True
            assert result.file_type == "json"
            assert result.metrics.get("page_count") == 6

    asyncio.run(run())


def test_ppt_agent_page_count_mismatch():
    """PPT Agent 在页数不符合 depth 要求时返回失败。"""
    async def run():
        from app.resource.agents.ppt import PptAgent
        from unittest.mock import AsyncMock, patch

        with patch("app.resource.agents.ppt.DeckDirectorAgent") as MockDirector:
            MockDirector.return_value.run = AsyncMock(side_effect=ValueError("slide count 4 is invalid for depth standard"))
            agent = PptAgent(emitter=None)
            result = await agent.generate_resource(_make_input("ppt", {"lesson_depth": "standard"}))
            assert result.success is False
            assert "invalid for depth" in result.error

    asyncio.run(run())


# ── Registry 完整性 ────────────────────────────────────────────────────────


def test_all_agents_registered():
    expected = {"content", "mindmap", "code", "quiz", "reading", "ppt", "video", "planning"}
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


def test_ppt_agent_pipeline_failure_returns_failed_result():
    """PPT Agent 在 Director 阶段失败时返回失败结果。"""
    async def run():
        from app.resource.agents.ppt import PptAgent
        from unittest.mock import AsyncMock, patch

        with patch("app.resource.agents.ppt.DeckDirectorAgent") as MockDirector:
            MockDirector.return_value.run = AsyncMock(side_effect=RuntimeError("课件规划失败"))
            agent = PptAgent(emitter=None)
            result = await agent.generate_resource(_make_input("ppt"))
            assert result.success is False
            assert "课件规划失败" in result.error
    asyncio.run(run())


from app.resource.schemas import DownstreamContext, TeachingOutlineItem, TeachingPlan


def _sample_teaching_plan() -> TeachingPlan:
    return TeachingPlan(
        topic="TCP 三次握手",
        learning_goal="理解三次握手",
        outline=[
            TeachingOutlineItem(
                id="o1",
                title="为什么需要三次握手",
                goal="理解目的",
                key_points=["确认双方收发能力"],
                suggested_visuals=["时序图"],
            ),
            TeachingOutlineItem(
                id="o2",
                title="三次握手过程",
                goal="理解流程",
                key_points=["SYN", "SYN-ACK", "ACK"],
            ),
        ],
    )


def _assert_valid_handoff(ctx: DownstreamContext, source_agent: str):
    assert ctx.source_agent == source_agent
    assert ctx.title
    assert ctx.one_sentence_summary
    assert len(ctx.one_sentence_summary) <= 180


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
            agent_name="video",
            teaching_plan=plan,
            upstream_handoffs={"content": handoff},
        )
    )
    joined = "\n\n".join(parts)

    assert "## 教学计划" in joined
    assert "## 上游交接摘要" in joined
    assert "previous_results" not in joined
    assert "规划师指令" not in joined

