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


@pytest.mark.skip(reason="Obsolete PPT refactor components")
def test_ppt_agent_execute_success():
    """PPT Agent 使用新的两阶段架构生成课件。"""
    async def run():
        from app.resource.agents.ppt import PPTAgent as PptAgent
        from app.resource.ppt_contract import (
            DeckBlueprint, SlideBlueprint,
            CompiledDeck, CompiledBatch, CompiledSlide,
            CompiledBlock, BlockBudget,
            BatchDraft, SlideContentDraft,
            CardListBlock, DiagramBlock, DiagramEdge, DiagramNode,
            FlowChartBlock, FlowStep,
            KeyPointBlock, CardItem, TextBlock,
        )
        from unittest.mock import AsyncMock, patch

        blueprint = DeckBlueprint(
            template_id="teaching-lesson",
            title="Python 基础",
            audience="计算机专业学生",
            slides=[
                SlideBlueprint(
                    slide_id="slide-01",
                    index=1,
                    role="cover",
                    title="Python 基础",
                    teaching_intent="介绍本节课的主题内容",
                    unique_value="建立课程主题与学习边界",
                ),
                SlideBlueprint(
                    slide_id="slide-02",
                    index=2,
                    role="objectives",
                    title="本节课要先会定义变量再识别类型",
                    teaching_intent="明确本节的学习目标",
                    unique_value="给出本节课的三项目标",
                ),
                SlideBlueprint(
                    slide_id="slide-03",
                    index=3,
                    role="roadmap",
                    title="变量与类型的知识链路是定义到判断",
                    teaching_intent="展示知识讲解的先后顺序",
                    unique_value="建立变量到类型判断的知识地图",
                ),
                SlideBlueprint(
                    slide_id="slide-04",
                    index=4,
                    role="concept",
                    title="变量名绑定的是对象而不是盒子标签",
                    teaching_intent="讲解变量的核心概念",
                    unique_value="澄清变量绑定对象的真实语义",
                ),
                SlideBlueprint(
                    slide_id="slide-05",
                    index=5,
                    role="process_demo",
                    title="运行 type 判断时会先取值再识别对象类型",
                    teaching_intent="演示类型判断的过程",
                    unique_value="展示从赋值到类型判断的执行过程",
                ),
                SlideBlueprint(
                    slide_id="slide-06",
                    index=6,
                    role="summary",
                    title="变量绑定与类型判断组成 Python 入门骨架",
                    teaching_intent="总结本节课的核心内容",
                    unique_value="用框架回收本节全部关键信息",
                ),
            ],
        )

        compiled = CompiledDeck(
            template_id="teaching-lesson",
            theme_id="logic-blue",
            title="Python 基础",
            audience="计算机专业学生",
            batches=[
                CompiledBatch(
                    batch_id="batch-01",
                    focus="课程目标与变量概念",
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
                            title="本节课要先会定义变量再识别类型",
                            subtitle=None,
                            teaching_intent="明确本节的学习目标",
                            unique_value="给出本节课的三项目标",
                            layout="CardCluster",
                            blocks=[
                                CompiledBlock(
                                    block_id="objective-summary",
                                    slot="featured",
                                    type="KeyPoint",
                                    instruction="学习目标",
                                    budget=BlockBudget(max_chars=48),
                                ),
                                CompiledBlock(
                                    block_id="objective-list",
                                    slot="cards",
                                    type="CardList",
                                    instruction="学习目标列表",
                                    budget=BlockBudget(min_items=3, max_items=5),
                                ),
                            ],
                        ),
                        CompiledSlide(
                            slide_id="slide-03",
                            index=3,
                            role="roadmap",
                            title="变量与类型的知识链路是定义到判断",
                            subtitle=None,
                            teaching_intent="展示知识讲解的先后顺序",
                            unique_value="建立变量到类型判断的知识地图",
                            layout="KnowledgeMap",
                            blocks=[
                                CompiledBlock(
                                    block_id="roadmap-diagram",
                                    slot="map",
                                    type="Diagram",
                                    instruction="知识路线图",
                                    budget=BlockBudget(min_items=3, max_items=8),
                                ),
                                CompiledBlock(
                                    block_id="roadmap-legend",
                                    slot="legend",
                                    type="Text",
                                    instruction="路线图说明",
                                    budget=BlockBudget(max_chars=80),
                                ),
                            ],
                        ),
                        CompiledSlide(
                            slide_id="slide-04",
                            index=4,
                            role="concept",
                            title="变量名绑定的是对象而不是盒子标签",
                            subtitle=None,
                            teaching_intent="讲解变量的核心概念",
                            unique_value="澄清变量绑定对象的真实语义",
                            layout="DualPane",
                            blocks=[
                                CompiledBlock(
                                    block_id="definition",
                                    slot="left",
                                    type="Text",
                                    instruction="变量定义",
                                    budget=BlockBudget(max_chars=120),
                                ),
                                CompiledBlock(
                                    block_id="keywords",
                                    slot="right",
                                    type="CardList",
                                    instruction="关键术语",
                                    budget=BlockBudget(min_items=2, max_items=4),
                                ),
                            ],
                        ),
                    ],
                ),
                CompiledBatch(
                    batch_id="batch-02",
                    focus="类型判断与总结回收",
                    slides=[
                        CompiledSlide(
                            slide_id="slide-05",
                            index=5,
                            role="process_demo",
                            title="运行 type 判断时会先取值再识别对象类型",
                            subtitle=None,
                            teaching_intent="演示类型判断的过程",
                            unique_value="展示从赋值到类型判断的执行过程",
                            layout="FlowCanvas",
                            blocks=[
                                CompiledBlock(
                                    block_id="process-flow",
                                    slot="flow",
                                    type="FlowChart",
                                    instruction="流程演示",
                                    budget=BlockBudget(min_items=3, max_items=6),
                                ),
                                CompiledBlock(
                                    block_id="process-note",
                                    slot="annotation",
                                    type="Text",
                                    instruction="流程说明",
                                    budget=BlockBudget(max_chars=100),
                                ),
                            ],
                        ),
                        CompiledSlide(
                            slide_id="slide-06",
                            index=6,
                            role="summary",
                            title="变量绑定与类型判断组成 Python 入门骨架",
                            subtitle=None,
                            teaching_intent="总结本节课的核心内容",
                            unique_value="用框架回收本节全部关键信息",
                            layout="CardCluster",
                            blocks=[
                                CompiledBlock(
                                    block_id="summary-highlight",
                                    slot="featured",
                                    type="KeyPoint",
                                    instruction="最终总结",
                                    budget=BlockBudget(max_chars=48),
                                ),
                                CompiledBlock(
                                    block_id="summary-cards",
                                    slot="cards",
                                    type="CardList",
                                    instruction="总结卡片",
                                    budget=BlockBudget(min_items=3, max_items=5),
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )

        draft_ch1 = BatchDraft(
            batch_id="batch-01",
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
                        KeyPointBlock(block_id="objective-summary", type="KeyPoint", label="目标", content="先会定义变量再读懂类型"),
                        CardListBlock(
                            block_id="objective-list",
                            type="CardList",
                            cards=[
                                CardItem(title="定义变量", content="知道赋值语句如何建立名称绑定"),
                                CardItem(title="识别类型", content="能用 type 观察对象属于哪类值"),
                                CardItem(title="避免误解", content="区分名称、值和对象三者关系"),
                            ],
                        ),
                    ],
                    takeaway="明确学习目标",
                    speaker_notes="先让学生看到路线，再进入定义细节，避免后面只记语法不懂语义。",
                ),
                SlideContentDraft(
                    slide_id="slide-03",
                    blocks=[
                        DiagramBlock(
                            block_id="roadmap-diagram",
                            type="Diagram",
                            direction="LR",
                            nodes=[
                                DiagramNode(id="n1", label="赋值语句"),
                                DiagramNode(id="n2", label="名称绑定"),
                                DiagramNode(id="n3", label="对象值"),
                                DiagramNode(id="n4", label="类型判断"),
                            ],
                            edges=[
                                DiagramEdge(source="n1", target="n2"),
                                DiagramEdge(source="n2", target="n3"),
                                DiagramEdge(source="n3", target="n4"),
                            ],
                        ),
                        TextBlock(block_id="roadmap-legend", type="Text", content="先看赋值如何建立绑定，再看对象如何决定类型。", format="plain"),
                    ],
                    takeaway="知道本节知识推进顺序",
                    speaker_notes="用一张总图让学生知道后面每一页解决哪一个问题，降低切换成本。",
                ),
                SlideContentDraft(
                    slide_id="slide-04",
                    blocks=[
                        TextBlock(block_id="definition", type="Text", content="执行 a = 3 时，名称 a 会绑定到整数对象 3，而不是向盒子里塞入数字。", format="plain"),
                        CardListBlock(
                            block_id="keywords",
                            type="CardList",
                            cards=[
                                CardItem(title="名称", content="代码里可引用对象的标识符"),
                                CardItem(title="绑定", content="名称指向某个对象的关系"),
                                CardItem(title="对象", content="真正携带值和类型的数据实体"),
                            ],
                        ),
                    ],
                    takeaway="理解变量的真实语义是绑定",
                    speaker_notes="这里重点纠正“变量是盒子”的口语化说法，否则后续引用和值传递会越来越乱。",
                ),
            ],
        )

        draft_ch2 = BatchDraft(
            batch_id="batch-02",
            slides=[
                SlideContentDraft(
                    slide_id="slide-05",
                    blocks=[
                        FlowChartBlock(
                            block_id="process-flow",
                            type="FlowChart",
                            steps=[
                                FlowStep(step_id="s1", title="赋值", description="执行 a = 3 建立名称到对象的绑定"),
                                FlowStep(step_id="s2", title="取值", description="调用 type(a) 时先找到 a 当前绑定的对象"),
                                FlowStep(step_id="s3", title="识别", description="解释器读取对象元信息并返回 int"),
                            ],
                        ),
                        TextBlock(block_id="process-note", type="Text", content="type 判断的是对象类型，不是变量名本身。", format="plain"),
                    ],
                    takeaway="理解类型判断针对的是对象",
                    speaker_notes="让学生把注意力放在“先绑定对象，再读取类型”这条链上，而不是死记函数名。",
                ),
                SlideContentDraft(
                    slide_id="slide-06",
                    blocks=[
                        KeyPointBlock(block_id="summary-highlight", type="KeyPoint", label="骨架", content="变量绑定对象，类型属于对象"),
                        CardListBlock(
                            block_id="summary-cards",
                            type="CardList",
                            cards=[
                                CardItem(title="定义", content="赋值语句建立名称与对象的绑定"),
                                CardItem(title="判断", content="type 读取对象自身的类型信息"),
                                CardItem(title="迁移", content="理解绑定关系后再学列表和函数更稳"),
                            ],
                        ),
                    ],
                    takeaway="课程总结",
                    speaker_notes="最后把定义、判断和后续迁移串起来，帮助学生形成一个稳定的认知骨架。",
                ),
            ],
        )

        with patch("app.resource.agents.ppt.DeckDirectorAgent") as MockDirector, \
             patch("app.resource.agents.ppt.SlideBatchWriterAgent") as MockWriter, \
            patch("app.resource.agents.ppt.compile_deck", return_value=compiled):

            MockDirector.return_value.run = AsyncMock(return_value=blueprint)
            MockWriter.return_value.run = AsyncMock(side_effect=[draft_ch1, draft_ch2])

            agent = PptAgent(emitter=None)
            result = await agent.generate_resource(_make_input("ppt", {"lesson_depth": "quick", "template_style": "logic-blue"}))
            assert result.success is True
            assert result.file_type == "json"
            assert result.metrics.get("page_count") == 6
            assert result.metrics.get("batch_count") == 2

    asyncio.run(run())


@pytest.mark.skip(reason="Obsolete PPT refactor components")
def test_ppt_agent_page_count_mismatch():
    """PPT Agent 在页数不符合 depth 要求时返回失败。"""
    async def run():
        from app.resource.agents.ppt import PPTAgent as PptAgent
        from unittest.mock import AsyncMock, patch

        with patch("app.resource.agents.ppt.DeckDirectorAgent") as MockDirector:
            MockDirector.return_value.run = AsyncMock(side_effect=ValueError("slide count 4 is invalid for depth standard"))
            agent = PptAgent(emitter=None)
            result = await agent.generate_resource(_make_input("ppt", {"lesson_depth": "standard"}))
            assert result.success is False
            assert "invalid for depth" in result.error

    asyncio.run(run())


@pytest.mark.skip(reason="Obsolete PPT refactor components")
def test_ppt_agent_uses_template_style_from_config():
    async def run():
        from app.resource.agents.ppt import PPTAgent as PptAgent
        from app.resource.ppt_contract import BatchDraft, DeckBlueprint, SlideBlueprint
        from unittest.mock import AsyncMock, patch
        import json

        blueprint = DeckBlueprint(
            template_id="teaching-lesson",
            title="操作系统中断机制",
            audience="计算机专业学生",
            slides=[
                SlideBlueprint(slide_id="slide-01", index=1, role="cover", title="中断机制先定义问题边界", teaching_intent="定义中断主题边界", unique_value="明确本节只处理 CPU 响应中断机制"),
                SlideBlueprint(slide_id="slide-02", index=2, role="objectives", title="学习目标先对齐响应流程", teaching_intent="明确学习目标和路径", unique_value="说明本节要掌握的三类判断点"),
                SlideBlueprint(slide_id="slide-03", index=3, role="roadmap", title="理解路径是触发到现场恢复", teaching_intent="建立讲解顺序和知识图", unique_value="让学生先看到整体响应链"),
                SlideBlueprint(slide_id="slide-04", index=4, role="concept", title="中断本质是外设打断当前执行流", teaching_intent="定义中断核心概念", unique_value="澄清中断不是异常也不是轮询"),
                SlideBlueprint(slide_id="slide-05", index=5, role="process_demo", title="响应流程先保存现场再跳转服务例程", teaching_intent="演示中断处理流程", unique_value="展示保存现场到恢复执行的流程"),
                SlideBlueprint(slide_id="slide-06", index=6, role="summary", title="中断链路由触发保存处理恢复组成", teaching_intent="总结中断处理核心链路", unique_value="用一页回收整条响应链"),
            ],
        )

        writer_draft = {
            "batch_id": "batch-01",
            "slides": [
                {
                    "slide_id": "slide-01",
                    "blocks": [
                        {"block_id": "course-title", "type": "Text", "content": "操作系统中断机制", "format": "plain"},
                        {"block_id": "chapter-title", "type": "Text", "content": "从触发到恢复", "format": "plain"},
                        {"block_id": "topic-title", "type": "KeyPoint", "label": "主题", "content": "理解中断响应链"},
                    ],
                    "takeaway": "先限定本节课范围",
                    "speaker_notes": "先让学生知道我们只讨论中断响应链，不扩展到异常和系统调用。",
                },
                {
                    "slide_id": "slide-02",
                    "blocks": [
                        {"block_id": "objective-summary", "type": "KeyPoint", "label": "目标", "content": "掌握中断响应主链"},
                        {"block_id": "objective-list", "type": "CardList", "cards": [
                            {"title": "触发", "content": "知道中断如何进入 CPU 视野"},
                            {"title": "处理", "content": "理解现场保存和跳转逻辑"},
                            {"title": "恢复", "content": "知道返回原执行流的条件"},
                        ]},
                    ],
                    "takeaway": "先对齐学习目标",
                    "speaker_notes": "让学生先知道最终要回答哪三个问题，再看细节。",
                },
                {
                    "slide_id": "slide-03",
                    "blocks": [
                        {"block_id": "roadmap-diagram", "type": "Diagram", "direction": "LR", "nodes": [
                            {"id": "n1", "label": "触发"},
                            {"id": "n2", "label": "保存现场"},
                            {"id": "n3", "label": "执行 ISR"},
                            {"id": "n4", "label": "恢复"},
                        ], "edges": [
                            {"source": "n1", "target": "n2"},
                            {"source": "n2", "target": "n3"},
                            {"source": "n3", "target": "n4"},
                        ]},
                        {"block_id": "roadmap-legend", "type": "Text", "content": "整节课按照触发、保存、处理、恢复四步展开。", "format": "plain"},
                    ],
                    "takeaway": "先建立整体链路图",
                    "speaker_notes": "让学生先看到全局，再进入每一步的细节。",
                },
                {
                    "slide_id": "slide-04",
                    "blocks": [
                        {"block_id": "definition", "type": "Text", "content": "中断是外部或内部事件要求 CPU 暂停当前流程并转去执行服务程序。", "format": "plain"},
                        {"block_id": "keywords", "type": "CardList", "cards": [
                            {"title": "暂停", "content": "当前执行流暂时被打断"},
                            {"title": "跳转", "content": "控制权进入中断服务程序"},
                        ]},
                    ],
                    "takeaway": "中断不是轮询而是打断",
                    "speaker_notes": "重点纠正学生把中断和轮询混为一谈的误解。",
                },
            ],
        }

        writer_draft_2 = {
            "batch_id": "batch-02",
            "slides": [
                {
                    "slide_id": "slide-05",
                    "blocks": [
                        {"block_id": "process-flow", "type": "FlowChart", "steps": [
                            {"step_id": "s1", "title": "触发", "description": "设备或控制器发出中断请求"},
                            {"step_id": "s2", "title": "保存", "description": "CPU 保存现场并屏蔽必要中断"},
                            {"step_id": "s3", "title": "处理", "description": "跳转到 ISR 执行服务逻辑"},
                        ]},
                        {"block_id": "process-note", "type": "Text", "content": "服务结束后还需要恢复现场并返回被打断位置。", "format": "plain"},
                    ],
                    "takeaway": "流程是触发保存处理恢复",
                    "speaker_notes": "把中断响应看成一条状态链，而不是孤立动作。",
                },
                {
                    "slide_id": "slide-06",
                    "blocks": [
                        {"block_id": "summary-highlight", "type": "KeyPoint", "label": "主线", "content": "中断处理的关键是安全切换并恢复控制流"},
                        {"block_id": "summary-cards", "type": "CardList", "cards": [
                            {"title": "触发", "content": "请求进入 CPU"},
                            {"title": "保存", "content": "现场必须先保存"},
                            {"title": "恢复", "content": "返回原控制流"},
                        ]},
                    ],
                    "takeaway": "回收到一条稳定主线",
                    "speaker_notes": "最后用三段式回收全节课，帮助学生形成稳定记忆框架。",
                },
            ],
        }

        with patch("app.resource.agents.ppt.DeckDirectorAgent") as MockDirector, \
             patch("app.resource.agents.ppt.SlideBatchWriterAgent") as MockWriter:
            MockDirector.return_value.run = AsyncMock(return_value=blueprint)
            MockWriter.return_value.run = AsyncMock(
                side_effect=[
                    BatchDraft.model_validate(writer_draft),
                    BatchDraft.model_validate(writer_draft_2),
                ]
            )

            agent = PptAgent(emitter=None)
            result = await agent.generate_resource(_make_input("ppt", {"lesson_depth": "quick", "template_style": "paper-light"}))

        assert result.success is True
        payload = json.loads(result.content)
        assert set(payload.keys()) == {"template_id", "theme_id", "title", "audience", "slides"}
        assert payload["theme_id"] == "paper-light"
        assert payload["template_id"] == "teaching-lesson"
        assert len(payload["slides"]) == 6
        assert set(payload["slides"][0].keys()) == {
            "id",
            "index",
            "role",
            "title",
            "subtitle",
            "layout",
            "slots",
            "takeaway",
            "speaker_notes",
        }
        assert "teaching_intent" not in payload["slides"][0]
        assert "unique_value" not in payload["slides"][0]
        assert "blocks" not in payload["slides"][0]

    asyncio.run(run())


@pytest.mark.skip(reason="Obsolete PPT refactor components")
def test_ppt_director_uses_flat_slide_blueprint_contract():
    async def run():
        from app.resource.agents.ppt import DeckDirectorAgent, SourcePack
        from app.resource.ppt_contract import DeckBlueprint
        from unittest.mock import patch

        captured: dict[str, Any] = {}

        class StubLlm:
            async def ainvoke_json(self, schema, input_data, **kwargs):
                captured["schema"] = schema
                captured["input"] = input_data
                captured["kwargs"] = kwargs
                return DeckBlueprint(
                    template_id="teaching-lesson",
                    title="TCP 三次握手",
                    audience="计算机专业学生",
                    slides=[
                        {
                            "slide_id": "slide-01",
                            "index": 1,
                            "role": "cover",
                            "title": "TCP 三次握手先建立连接语境",
                            "subtitle": None,
                            "teaching_intent": "建立主题和问题边界",
                            "unique_value": "明确本节只讨论三次握手的建立过程",
                        },
                        {
                            "slide_id": "slide-02",
                            "index": 2,
                            "role": "objectives",
                            "title": "先掌握状态变化再理解报文意义",
                            "subtitle": None,
                            "teaching_intent": "明确本节需要掌握的学习目标",
                            "unique_value": "给出本节目标和判断标准",
                        },
                        {
                            "slide_id": "slide-03",
                            "index": 3,
                            "role": "roadmap",
                            "title": "三次握手的学习顺序是动机到流程",
                            "subtitle": None,
                            "teaching_intent": "建立后续讲解的知识顺序",
                            "unique_value": "用路线图绑定后续页面顺序",
                        },
                        {
                            "slide_id": "slide-04",
                            "index": 4,
                            "role": "concept",
                            "title": "连接建立的本质是同步双方初始序号",
                            "subtitle": None,
                            "teaching_intent": "定义连接建立的核心概念",
                            "unique_value": "讲清为什么必须同步两端序号",
                        },
                        {
                            "slide_id": "slide-05",
                            "index": 5,
                            "role": "process_demo",
                            "title": "三次报文逐步确认双方收发能力",
                            "subtitle": None,
                            "teaching_intent": "演示三次握手的建立过程",
                            "unique_value": "逐步展示三报文如何完成确认",
                        },
                        {
                            "slide_id": "slide-06",
                            "index": 6,
                            "role": "summary",
                            "title": "状态加报文共同构成握手知识骨架",
                            "subtitle": None,
                            "teaching_intent": "收束本节涉及的核心内容",
                            "unique_value": "回收状态机和报文序列两条主线",
                        },
                    ],
                )

        source_pack = SourcePack(
            learning_need="TCP 三次握手",
            learning_scenario="self_study",
            profile={},
            teaching_plan=None,
            source_type="resource",
            artifacts=[],
        )

        with patch("app.resource.agents.ppt.get_llm", return_value=StubLlm()):
            result = await DeckDirectorAgent().run(source_pack, "quick")

        assert isinstance(result, DeckBlueprint)
        assert captured["schema"] is DeckBlueprint
        assert captured["kwargs"]["prompt_fallback"] is True
        input_text = str(captured["input"])
        assert '"top_level_fields": ["template_id", "title", "audience", "slides"]' in input_text
        assert '"forbidden_fields": ["pages", "total_pages", "chapters", "theme_id", "composition_id", "narrative", "primary_example", "terminology"]' in input_text
        assert "template_style" not in input_text

    asyncio.run(run())


@pytest.mark.skip(reason="Obsolete PPT refactor components")
def test_ppt_batch_writer_input_excludes_theme_and_template_metadata():
    async def run():
        from app.resource.agents.ppt import SlideBatchWriterAgent
        from app.resource.ppt_contract import BatchDraft, CompiledBatch, CompiledBlock, CompiledSlide, BlockBudget
        from unittest.mock import patch

        captured: dict[str, Any] = {}

        class StubLlm:
            async def ainvoke_json(self, schema, input_data, **kwargs):
                captured["schema"] = schema
                captured["input"] = input_data
                captured["kwargs"] = kwargs
                return BatchDraft.model_validate(
                    {
                        "batch_id": "batch-01",
                        "slides": [
                            {
                                "slide_id": "slide-01",
                                "blocks": [
                                    {"block_id": "course-title", "type": "Text", "content": "TCP 三次握手", "format": "plain"},
                                ],
                                "takeaway": "建立课程主题",
                                "speaker_notes": "先交代范围，再进入协议过程，避免学生在一开始就丢失主线。",
                            }
                        ],
                    }
                )

        batch = CompiledBatch(
            batch_id="batch-01",
            focus="建立课程主题",
            slides=[
                CompiledSlide(
                    slide_id="slide-01",
                    index=1,
                    role="cover",
                    title="TCP 三次握手先建立连接语境",
                    subtitle=None,
                    teaching_intent="建立主题和问题边界",
                    unique_value="明确本节只讨论三次握手的建立过程",
                    layout="HeroCover",
                    blocks=[
                        CompiledBlock(
                            block_id="course-title",
                            slot="main",
                            type="Text",
                            instruction="课程标题",
                            budget=BlockBudget(max_chars=32),
                        )
                    ],
                )
            ],
        )

        blueprint = {
            "template_id": "teaching-lesson",
            "title": "TCP 三次握手",
            "audience": "计算机专业学生",
            "slides": [],
        }

        with patch("app.resource.agents.ppt.get_llm", return_value=StubLlm()):
            result = await SlideBatchWriterAgent().run(
                batch=batch,
                blueprint=type("BlueprintLike", (), blueprint)(),
                sources=[],
            )

        assert isinstance(result, BatchDraft)
        input_text = str(captured["input"])
        assert '"title": "TCP 三次握手"' in input_text
        assert '"audience": "计算机专业学生"' in input_text
        assert "theme_id" not in input_text
        assert "template_id" not in input_text

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


@pytest.mark.skip(reason="Obsolete PPT refactor components")
def test_ppt_agent_pipeline_failure_returns_failed_result():
    """PPT Agent 在 Director 阶段失败时返回失败结果。"""
    async def run():
        from app.resource.agents.ppt import PPTAgent as PptAgent
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
