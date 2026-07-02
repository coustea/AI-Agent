"""PPT pipeline stage tests — comprehensive stage-level unit tests with FakeLlm."""

from __future__ import annotations

import asyncio
from typing import Any

from app.resource.agents.ppt_pipeline.planner import BriefPlanner
from app.resource.agents.ppt_pipeline.director import StyleDirector
from app.resource.agents.ppt_pipeline.author import HTMLAuthor, strip_outer_html_fence
from app.resource.agents.ppt_pipeline.repair import RepairAgent
from app.resource.agents.ppt_pipeline.schemas import (
    DeckBrief,
    SourcePack,
    StyleDecision,
    StyleCandidate,
    StaticAudit,
    VisualAudit,
    VisualQAProblem,
)


# ── FakeLlm ──────────────────────────────────────────────────────────────────


class _FakeLlmResponse:
    """Mimics the LLM response object with a .content attribute."""

    def __init__(self, content: str):
        self.content = content


class FakeLlm:
    """Unified mock: supports both ainvoke and ainvoke_json with call tracking."""

    def __init__(self, text_response: str = "", json_response: Any = None):
        self._text_response = text_response
        self._json_response = json_response
        self.calls: list[dict[str, Any]] = []

    async def ainvoke(
        self,
        input_data,
        *,
        model=None,
        temperature=0,
        max_tokens=None,
    ):
        self.calls.append(
            {
                "method": "ainvoke",
                "input": input_data,
                "model": model,
                "max_tokens": max_tokens,
            }
        )
        return _FakeLlmResponse(self._text_response)

    async def ainvoke_json(
        self,
        schema,
        input_data,
        *,
        temperature=0,
        function_name=None,
        function_description=None,
        max_tokens=None,
    ):
        self.calls.append(
            {
                "method": "ainvoke_json",
                "schema": schema.__name__,
                "function_name": function_name,
                "input": input_data,
            }
        )
        if self._json_response is not None:
            return schema.model_validate(self._json_response)
        raise RuntimeError("no json_response configured")


# ── Shared fixtures ──────────────────────────────────────────────────────────


def _source_pack() -> SourcePack:
    return SourcePack(
        learning_need="学习 TCP 三次握手",
        learning_scenario="self_study",
        profile={},
        teaching_plan=None,
        source_type="resource",
        artifacts=[],
    )


def _deck_brief() -> DeckBrief:
    return DeckBrief(
        purpose="演示 TCP 连接建立过程",
        audience="零基础大学生",
        density="speaker_led",
        target_slide_count=6,
        narrative="从连接动机到三次报文逐步确认",
        required_points=["SYN", "SYN-ACK", "ACK"],
        mood="tech, professional",
        language="zh-CN",
    )


def _style_decision() -> StyleDecision:
    return StyleDecision(
        candidates=[
            StyleCandidate(
                name="neon-cyber",
                source="preset",
                rationale="用未来科技主题提升吸引力",
                design_recipe="--bg-primary: #0a0f1c; --accent: #00ffcc;",
                font_urls=["https://api.fontshare.com/v2/css?f[]=clash-display"],
            ),
            StyleCandidate(
                name="bold-dark",
                source="bold_template",
                rationale="高对比度适合代码与流程演示",
                design_recipe="--bg-primary: #1a1a2e; --accent: #e94560;",
                font_urls=[],
            ),
            StyleCandidate(
                name="custom-slate",
                source="custom",
                rationale="沉稳色调适合学术讲解",
                design_recipe="--bg-primary: #2d3436; --accent: #74b9ff;",
                font_urls=[],
            ),
        ],
        selected_index=0,
        density="speaker_led",
    )


def _style_decision_json() -> dict:
    return {
        "candidates": [
            {
                "name": "neon-cyber",
                "source": "preset",
                "rationale": "用未来科技主题提升吸引力",
                "design_recipe": "--bg-primary: #0a0f1c; --accent: #00ffcc;",
                "font_urls": ["https://api.fontshare.com/v2/css?f[]=clash-display"],
            },
            {
                "name": "bold-dark",
                "source": "bold_template",
                "rationale": "高对比度适合代码与流程演示",
                "design_recipe": "--bg-primary: #1a1a2e; --accent: #e94560;",
                "font_urls": [],
            },
            {
                "name": "custom-slate",
                "source": "custom",
                "rationale": "沉稳色调适合学术讲解",
                "design_recipe": "--bg-primary: #2d3436; --accent: #74b9ff;",
                "font_urls": [],
            },
        ],
        "selected_index": 0,
        "density": "speaker_led",
    }


# ── 1. BriefPlanner ─────────────────────────────────────────────────────────


def test_brief_planner_calls_ainvoke_json_with_deck_brief_schema():
    """BriefPlanner.plan should call ainvoke_json with the DeckBrief schema."""

    async def run():
        json_resp = {
            "purpose": "演示 TCP 连接建立过程",
            "audience": "零基础大学生",
            "density": "speaker_led",
            "target_slide_count": 6,
            "narrative": "从连接动机到三次报文逐步确认",
            "required_points": ["SYN", "SYN-ACK", "ACK"],
            "mood": "tech, professional",
            "language": "zh-CN",
        }
        fake_llm = FakeLlm(json_response=json_resp)
        planner = BriefPlanner(llm=fake_llm)

        brief = await planner.plan(source_pack=_source_pack())

        # Verify return type and fields
        assert isinstance(brief, DeckBrief)
        assert brief.purpose == "演示 TCP 连接建立过程"
        assert brief.target_slide_count == 6
        assert brief.density == "speaker_led"
        assert brief.language == "zh-CN"

        # Verify ainvoke_json called with DeckBrief schema
        assert len(fake_llm.calls) == 1
        call = fake_llm.calls[0]
        assert call["method"] == "ainvoke_json"
        assert call["schema"] == "DeckBrief"

    asyncio.run(run())


def test_brief_planner_prompt_contains_source_pack_data():
    """The prompt sent to the model must include source_pack fields."""

    async def run():
        json_resp = {
            "purpose": "演示 TCP 连接建立过程",
            "audience": "零基础大学生",
            "density": "speaker_led",
            "target_slide_count": 6,
            "narrative": "从连接动机到三次报文逐步确认",
            "required_points": ["SYN", "SYN-ACK", "ACK"],
            "mood": "tech, professional",
            "language": "zh-CN",
        }
        fake_llm = FakeLlm(json_response=json_resp)
        planner = BriefPlanner(llm=fake_llm)

        await planner.plan(source_pack=_source_pack())

        call = fake_llm.calls[0]
        prompt_text = call["input"]
        # SourcePack fields must appear in the rendered prompt
        assert "学习 TCP 三次握手" in prompt_text
        assert "self_study" in prompt_text

    asyncio.run(run())


# ── 2. StyleDirector ────────────────────────────────────────────────────────


def test_style_director_calls_ainvoke_json_with_style_decision_schema():
    """StyleDirector.direct should call ainvoke_json with StyleDecision schema."""

    async def run():
        fake_llm = FakeLlm(json_response=_style_decision_json())
        director = StyleDirector(llm=fake_llm)

        decision = await director.direct(
            brief=_deck_brief(),
            source_pack=_source_pack(),
        )

        # Verify return type: 3-candidate StyleDecision
        assert isinstance(decision, StyleDecision)
        assert len(decision.candidates) == 3
        assert decision.candidates[0].source == "preset"
        assert decision.candidates[1].source == "bold_template"
        assert decision.candidates[2].source == "custom"
        assert decision.selected.name == "neon-cyber"
        assert decision.selected.source == "preset"
        assert decision.density == "speaker_led"

        # Verify ainvoke_json called with StyleDecision schema
        assert len(fake_llm.calls) == 1
        call = fake_llm.calls[0]
        assert call["method"] == "ainvoke_json"
        assert call["schema"] == "StyleDecision"

    asyncio.run(run())


def test_style_director_prompt_contains_safe_presets_and_bold_templates():
    """The prompt must include safe_presets and bold_templates from assets."""

    async def run():
        fake_llm = FakeLlm(json_response=_style_decision_json())
        director = StyleDirector(llm=fake_llm)

        await director.direct(
            brief=_deck_brief(),
            source_pack=_source_pack(),
        )

        call = fake_llm.calls[0]
        prompt_text = call["input"]
        # The director renders safe_presets and bold_templates into the prompt
        # via the template labels "Safe presets" and "Bold templates"
        assert "Safe presets" in prompt_text
        assert "Bold templates" in prompt_text

    asyncio.run(run())


# ── 3. HTMLAuthor ────────────────────────────────────────────────────────────


def test_html_author_calls_ainvoke_not_ainvoke_json():
    """HTMLAuthor.author should call ainvoke (plain text), not ainvoke_json."""

    async def run():
        fake_markup = "<section class=\"slide\"><h1>TCP 三次握手</h1></section>"
        fake_llm = FakeLlm(text_response=fake_markup)
        author = HTMLAuthor(llm=fake_llm)

        html_out = await author.author(
            source_pack=_source_pack(),
            brief=_deck_brief(),
            style=_style_decision(),
        )

        assert len(fake_llm.calls) == 1
        assert fake_llm.calls[0]["method"] == "ainvoke"
        assert isinstance(html_out, str)
        assert "TCP 三次握手" in html_out

    asyncio.run(run())


def test_html_author_returns_raw_html_without_fence():
    """Raw HTML from the model (no fence) should pass through unchanged."""

    async def run():
        raw_html = (
            "<section class=\"slide active visible\">\n"
            "  <h1>TCP 三次握手</h1>\n"
            "</section>"
        )
        fake_llm = FakeLlm(text_response=raw_html)
        author = HTMLAuthor(llm=fake_llm)

        html_out = await author.author(
            source_pack=_source_pack(),
            brief=_deck_brief(),
            style=_style_decision(),
        )

        assert html_out == raw_html.strip()

    asyncio.run(run())


def test_html_author_strips_html_lang_fence():
    """HTML wrapped in ```html fence should have the fence stripped."""

    async def run():
        inner = "<section class=\"slide\"><h1>Hello</h1></section>"
        fenced = f"```html\n{inner}\n```"
        fake_llm = FakeLlm(text_response=fenced)
        author = HTMLAuthor(llm=fake_llm)

        html_out = await author.author(
            source_pack=_source_pack(),
            brief=_deck_brief(),
            style=_style_decision(),
        )

        assert html_out == inner
        assert "```" not in html_out

    asyncio.run(run())


def test_html_author_strips_plain_fence():
    """HTML wrapped in ``` fence (no language tag) should have the fence stripped."""

    async def run():
        inner = "<section class=\"slide\"><p>Content</p></section>"
        fenced = f"```\n{inner}\n```"
        fake_llm = FakeLlm(text_response=fenced)
        author = HTMLAuthor(llm=fake_llm)

        html_out = await author.author(
            source_pack=_source_pack(),
            brief=_deck_brief(),
            style=_style_decision(),
        )

        assert html_out == inner
        assert "```" not in html_out

    asyncio.run(run())


def test_html_author_fence_stripping_preserves_internal_content():
    """Fence stripping must not alter the HTML content inside."""

    async def run():
        # HTML that itself contains backtick-like patterns or code blocks
        inner = (
            "<section class=\"slide\">\n"
            "  <pre><code>const x = `hello`;</code></pre>\n"
            "  <p>Some text with ``` in it</p>\n"
            "</section>"
        )
        fenced = f"```html\n{inner}\n```"
        fake_llm = FakeLlm(text_response=fenced)
        author = HTMLAuthor(llm=fake_llm)

        html_out = await author.author(
            source_pack=_source_pack(),
            brief=_deck_brief(),
            style=_style_decision(),
        )

        # Internal content is preserved exactly (minus outer fence)
        assert "const x = `hello`;" in html_out
        assert "<pre><code>" in html_out
        assert "Some text with ``` in it" in html_out

    asyncio.run(run())


# ── 4. RepairAgent ───────────────────────────────────────────────────────────


def test_repair_agent_calls_ainvoke():
    """RepairAgent.repair should call ainvoke (plain text)."""

    async def run():
        broken_html = (
            "<section class=\"slide active visible\">\n"
            "  <h1>TCP 三次握手</h1>\n"
            "  <p style=\"overflow: hidden;\">超长文本溢出问题</p>\n"
            "</section>"
        )
        fake_llm = FakeLlm(text_response=broken_html)
        repair = RepairAgent(llm=fake_llm)

        static_audit = StaticAudit(
            passed=False,
            problems=["slide 2: text overflow"],
            slide_count=1,
        )
        visual_audit = VisualAudit(
            passed=False,
            problems=[
                VisualQAProblem(
                    slide_index=0,
                    viewport="desktop",
                    problem_type="overflow",
                    element_summary="p overflow",
                    severity="critical",
                ),
            ],
        )

        result = await repair.repair(
            html=broken_html,
            brief=_deck_brief(),
            style=_style_decision(),
            static_audit=static_audit,
            visual_audit=visual_audit,
        )

        assert len(fake_llm.calls) == 1
        assert fake_llm.calls[0]["method"] == "ainvoke"
        assert isinstance(result, str)
        assert "TCP" in result

    asyncio.run(run())


def test_repair_agent_prompt_contains_static_and_visual_problems():
    """The repair prompt must include both static_problems and visual_problems."""

    async def run():
        broken_html = "<section><h1>Bug</h1></section>"
        fake_llm = FakeLlm(text_response=broken_html)
        repair = RepairAgent(llm=fake_llm)

        static_audit = StaticAudit(
            passed=False,
            problems=["slide 1: missing closing tag", "slide 2: text overflow"],
            slide_count=2,
        )
        visual_audit = VisualAudit(
            passed=False,
            problems=[
                VisualQAProblem(
                    slide_index=0,
                    viewport="desktop",
                    problem_type="overlap",
                    element_summary="title overlaps image",
                    severity="critical",
                ),
                VisualQAProblem(
                    slide_index=1,
                    viewport="mobile",
                    problem_type="overflow",
                    element_summary="paragraph overflows container",
                    severity="warning",
                ),
            ],
        )

        await repair.repair(
            html=broken_html,
            brief=_deck_brief(),
            style=_style_decision(),
            static_audit=static_audit,
            visual_audit=visual_audit,
        )

        prompt_text = fake_llm.calls[0]["input"]
        # static_problems are rendered into the prompt
        assert "missing closing tag" in prompt_text
        assert "text overflow" in prompt_text
        # visual_problems are rendered into the prompt with slide index, viewport, type
        assert "overlap" in prompt_text
        assert "desktop" in prompt_text
        assert "mobile" in prompt_text
        assert "paragraph overflows container" in prompt_text

    asyncio.run(run())


def test_repair_agent_strips_fence_from_output():
    """Fence stripping should also work on repair agent output."""

    async def run():
        inner = (
            "<section class=\"slide active visible\">\n"
            "  <h1>Repaired</h1>\n"
            "</section>"
        )
        fenced = f"```html\n{inner}\n```"
        fake_llm = FakeLlm(text_response=fenced)
        repair = RepairAgent(llm=fake_llm)

        static_audit = StaticAudit(passed=True, problems=[], slide_count=1)
        visual_audit = VisualAudit(passed=True, problems=[])

        result = await repair.repair(
            html="<section><h1>Broken</h1></section>",
            brief=_deck_brief(),
            style=_style_decision(),
            static_audit=static_audit,
            visual_audit=visual_audit,
        )

        assert result == inner
        assert "```" not in result
        assert "Repaired" in result

    asyncio.run(run())


# ── 5. strip_outer_html_fence unit tests ────────────────────────────────────


def test_strip_fence_no_fence_returns_as_is():
    """Content without a fence should be returned unchanged."""
    content = "<div><h1>Hello</h1></div>"
    assert strip_outer_html_fence(content) == content


def test_strip_fence_html_lang_fence():
    """```html fence should be stripped, content preserved."""
    inner = "<div><h1>Hello</h1></div>"
    fenced = f"```html\n{inner}\n```"
    assert strip_outer_html_fence(fenced) == inner


def test_strip_fence_plain_fence():
    """``` fence with no language tag should be stripped."""
    inner = "<div><p>World</p></div>"
    fenced = f"```\n{inner}\n```"
    assert strip_outer_html_fence(fenced) == inner


def test_strip_fence_with_whitespace():
    """Fence with leading/trailing whitespace should still be stripped."""
    inner = "<div>content</div>"
    fenced = f"  \n  ```html\n{inner}\n```  \n  "
    assert strip_outer_html_fence(fenced) == inner


def test_strip_fence_multiple_fences_only_outer_stripped():
    """When multiple fences exist, only the outermost fence should be stripped."""
    inner = "```\ncode inside\n```"
    fenced = f"```html\n{inner}\n```"
    result = strip_outer_html_fence(fenced)
    # The inner fence remains
    assert "```\ncode inside\n```" in result
    # The outer fence is gone
    assert result.startswith("```")
    assert result.endswith("```")
    # But it should not start with ```html anymore
    assert not result.startswith("```html")


def test_strip_fence_preserves_internal_content():
    """Content inside the fence must not be modified by stripping."""
    inner = (
        "<section>\n"
        "  <pre><code>const msg = `hello world`;</code></pre>\n"
        "  <p>Text with ``` backticks</p>\n"
        "</section>"
    )
    fenced = f"```html\n{inner}\n```"
    result = strip_outer_html_fence(fenced)
    assert "const msg = `hello world`;" in result
    assert "Text with ``` backticks" in result
    assert "<pre><code>" in result
