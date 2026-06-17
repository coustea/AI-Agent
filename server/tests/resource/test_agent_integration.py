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
    return ResourceInput(
        resource_id=1,
        learning_need="Python 基础语法",
        learning_scenario="self_study",
        agent_name=agent_id,
        agent_config=config or {},
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
    async def run():
        from app.resource.agents.ppt import PptAgent
        from app.resource.agents.ppt import (
            PptPayload, PptSlide, BlockHeading, BlockText, BlockCode,
            MaterialDigest, DeckOutline, SlideContract, BlockContract,
            SlideDraft, RenderedBlock,
        )
        from unittest.mock import AsyncMock, patch

        digest = MaterialDigest(topic="Python", audience="学生", learning_goal="学习语法")
        outline = DeckOutline(
            topic="Python", title="Python 基础", theme="theme-logic-blue",
            audience_level="intermediate", narrative="从语法到执行",
            slides=[
                SlideContract(slide_id="s1", index=1, role="cover",
                    title="Python 基础", learning_objective="学习语法",
                    layout="FocusTitle",
                    blocks=[BlockContract(block_id="b1", slot="main", type="Heading",
                              required_fields=["text"], content_hint="h")]),
                SlideContract(slide_id="s2", index=2, role="agenda",
                    title="目录", learning_objective="了解结构",
                    layout="BentoGrid",
                    blocks=[BlockContract(block_id="b2", slot="main", type="Heading",
                              required_fields=["text"], content_hint="h")]),
                SlideContract(slide_id="s3", index=3, role="concept",
                    title="变量", learning_objective="理解变量",
                    layout="SplitScreen",
                    blocks=[
                        BlockContract(block_id="b3", slot="left", type="Heading",
                                      required_fields=["text"], content_hint="h"),
                        BlockContract(block_id="b4", slot="right", type="Code",
                                      required_fields=["language", "code"], content_hint="c"),
                    ]),
            ],
        )
        drafts = [
            SlideDraft(slide_id="s1", index=1, title="Python 基础",
                blocks=[RenderedBlock(block_id="b1", type="Heading", data={"text": "Python 基础"})],
                speaker_notes=""),
            SlideDraft(slide_id="s2", index=2, title="目录",
                blocks=[RenderedBlock(block_id="b2", type="Heading", data={"text": "目录"})],
                speaker_notes=""),
            SlideDraft(slide_id="s3", index=3, title="变量",
                blocks=[
                    RenderedBlock(block_id="b3", type="Heading", data={"text": "变量"}),
                    RenderedBlock(block_id="b4", type="Code", data={"language": "python", "code": "x = 1"}),
                ],
                speaker_notes="讲解变量"),
        ]

        with patch("app.resource.agents.ppt.MaterialAgent") as MockM, \
             patch("app.resource.agents.ppt.OutlineAgent") as MockO, \
             patch("app.resource.agents.ppt.SlideAgent") as MockS, \
             patch("app.resource.agents.ppt.PayloadBuilder") as MockB:

            MockM.return_value.run = AsyncMock(return_value=digest)
            MockO.return_value.run = AsyncMock(return_value=outline)
            drafts_map = {d.slide_id: d for d in drafts}
            MockS.return_value.run = AsyncMock(side_effect=lambda contract, digest, outline: drafts_map[contract.slide_id])
            MockB.return_value.build.return_value = PptPayload(
                template_id="theme-logic-blue", topic="Python 基础",
                author="AI", date="2026-06-15",
                slides=[
                    PptSlide(id="s1", layout="FocusTitle", slots={"main": [BlockHeading(id="b1", type="Heading", level=1, content="Python 基础")]}),
                    PptSlide(id="s2", layout="BentoGrid", slots={"main": [BlockHeading(id="b2", type="Heading", level=2, content="目录")]}),
                    PptSlide(id="s3", layout="SplitScreen", slots={
                        "left": [BlockHeading(id="b3", type="Heading", level=2, content="变量")],
                        "right": [BlockCode(id="b4", type="Code", language="python", code="x = 1")],
                    }),
                ],
            )

            agent = PptAgent(emitter=None)
            result = await agent.generate_resource(_make_input("ppt", {"page_count": 3}))
            assert result.success is True
            assert result.file_type == "json"
            assert result.metrics.get("page_count") == 3

    asyncio.run(run())


def test_ppt_agent_page_count_mismatch():
    async def run():
        from app.resource.agents.ppt import PptAgent
        from app.resource.agents.ppt import (
            PptPayload, PptSlide, BlockHeading, BlockText, BlockCode,
            MaterialDigest, DeckOutline, SlideContract, BlockContract,
            SlideDraft, RenderedBlock,
        )
        from unittest.mock import AsyncMock, patch

        digest = MaterialDigest(topic="Python", audience="学生", learning_goal="学习语法")
        outline = DeckOutline(
            topic="Python", title="Python 基础", theme="theme-logic-blue",
            audience_level="intermediate", narrative="从语法到执行",
            slides=[
                SlideContract(slide_id="s1", index=1, role="cover",
                    title="Python 基础", learning_objective="学习语法",
                    layout="FocusTitle",
                    blocks=[BlockContract(block_id="b1", slot="main", type="Heading",
                              required_fields=["text"], content_hint="h")]),
                SlideContract(slide_id="s2", index=2, role="agenda",
                    title="目录", learning_objective="了解结构",
                    layout="BentoGrid",
                    blocks=[BlockContract(block_id="b2", slot="main", type="Heading",
                              required_fields=["text"], content_hint="h")]),
                SlideContract(slide_id="s3", index=3, role="concept",
                    title="变量", learning_objective="理解变量",
                    layout="SplitScreen",
                    blocks=[
                        BlockContract(block_id="b3", slot="left", type="Heading",
                                      required_fields=["text"], content_hint="h"),
                        BlockContract(block_id="b4", slot="right", type="Code",
                                      required_fields=["language", "code"], content_hint="c"),
                    ]),
            ],
        )
        drafts = [
            SlideDraft(slide_id="s1", index=1, title="Python 基础",
                blocks=[RenderedBlock(block_id="b1", type="Heading", data={"text": "Python 基础"})],
                speaker_notes=""),
            SlideDraft(slide_id="s2", index=2, title="目录",
                blocks=[RenderedBlock(block_id="b2", type="Heading", data={"text": "目录"})],
                speaker_notes=""),
            SlideDraft(slide_id="s3", index=3, title="变量",
                blocks=[
                    RenderedBlock(block_id="b3", type="Heading", data={"text": "变量"}),
                    RenderedBlock(block_id="b4", type="Code", data={"language": "python", "code": "x = 1"}),
                ],
                speaker_notes="讲解变量"),
        ]

        with patch("app.resource.agents.ppt.MaterialAgent") as MockM, \
             patch("app.resource.agents.ppt.OutlineAgent") as MockO, \
             patch("app.resource.agents.ppt.SlideAgent") as MockS, \
             patch("app.resource.agents.ppt.PayloadBuilder") as MockB:

            MockM.return_value.run = AsyncMock(return_value=digest)
            MockO.return_value.run = AsyncMock(return_value=outline)
            drafts_map = {d.slide_id: d for d in drafts}
            MockS.return_value.run = AsyncMock(side_effect=lambda contract, digest, outline: drafts_map[contract.slide_id])
            MockB.return_value.build.return_value = PptPayload(
                template_id="theme-logic-blue", topic="Python 基础",
                author="AI", date="2026-06-15",
                slides=[
                    PptSlide(id="s1", layout="FocusTitle", slots={"main": [BlockHeading(id="b1", type="Heading", level=1, content="Python 基础")]}),
                    PptSlide(id="s2", layout="BentoGrid", slots={"main": [BlockHeading(id="b2", type="Heading", level=2, content="目录")]}),
                    PptSlide(id="s3", layout="SplitScreen", slots={
                        "left": [BlockHeading(id="b3", type="Heading", level=2, content="变量")],
                        "right": [BlockCode(id="b4", type="Code", language="python", code="x = 1")],
                    }),
                ],
            )

            agent = PptAgent(emitter=None)
            result = await agent.generate_resource(_make_input("ppt", {"page_count": 6}))
            assert result.success is False
            assert "期望 6 页" in result.error
            assert "实际 3 页" in result.error

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
    async def run():
        from app.resource.agents.ppt import PptAgent
        from unittest.mock import AsyncMock, patch

        with patch("app.resource.agents.ppt.MaterialAgent") as MockM:
            MockM.return_value.run = AsyncMock(side_effect=RuntimeError("素材提取失败"))
            agent = PptAgent(emitter=None)
            result = await agent.generate_resource(_make_input("ppt"))
            assert result.success is False
            assert "素材提取失败" in result.error
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

