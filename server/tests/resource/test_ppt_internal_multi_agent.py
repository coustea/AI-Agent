"""Tests for ppt_models.py — DeckOutline validation, PptPayload backward compat,
MaterialBundle, and SlideDraft schemas."""

import os
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("SPARK_MAX_API_PASSWORD", "test-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.resource.agents.ppt_manifest import (
    PPT_TEMPLATE_MANIFEST,
    get_block_required_fields,
    get_layout_slots,
    validate_contract_against_manifest,
)
from app.resource.agents.ppt_models import (
    BlockContract,
    DeckConstraints,
    DeckOutline,
    MaterialArtifact,
    MaterialBundle,
    MaterialDigest,
    PptPayload,
    PptSlide,
    RenderedBlock,
    SlideContract,
    SlideDraft,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _cover_contract() -> SlideContract:
    return SlideContract(
        slide_id="s1",
        index=1,
        role="cover",
        title="TCP 三次握手",
        learning_objective="理解三次握手原理",
        layout="FocusTitle",
        blocks=[
            BlockContract(
                block_id="b1",
                slot="main",
                type="Heading",
                required_fields=["level", "content"],
                content_hint="Main title",
            ),
        ],
    )


def _agenda_contract() -> SlideContract:
    return SlideContract(
        slide_id="s2",
        index=2,
        role="agenda",
        title="课程大纲",
        learning_objective="概览本课内容",
        layout="BentoGrid",
        blocks=[
            BlockContract(
                block_id="b2",
                slot="main",
                type="Text",
                required_fields=["content"],
                content_hint="Agenda items",
            ),
        ],
    )


def _concept_contract() -> SlideContract:
    return SlideContract(
        slide_id="s3",
        index=3,
        role="concept",
        title="核心概念",
        learning_objective="掌握核心概念",
        layout="SplitScreen",
        blocks=[
            BlockContract(
                block_id="b3",
                slot="left",
                type="Text",
                required_fields=["content"],
                content_hint="Concept explanation",
            ),
        ],
    )


def _valid_outline() -> DeckOutline:
    return DeckOutline(
        topic="TCP 三次握手",
        title="TCP 三次握手详解",
        theme="theme-logic-blue",
        audience_level="beginner",
        narrative="从连接建立的角度理解三次握手的必要性",
        slides=[_cover_contract(), _agenda_contract(), _concept_contract()],
    )


def _valid_ppt_payload() -> dict:
    return {
        "template_id": "theme-logic-blue",
        "topic": "TCP 三次握手",
        "author": "AI",
        "date": "2026-06-15",
        "slides": [
            {
                "id": "slide-1",
                "layout": "FocusTitle",
                "slots": {
                    "main": [
                        {"id": "b1", "type": "Heading", "level": 1, "content": "TCP 三次握手"},
                    ],
                },
                "metadata": {},
            },
            {
                "id": "slide-2",
                "layout": "BentoGrid",
                "slots": {
                    "main": [
                        {"id": "b2", "type": "Text", "content": "Agenda"},
                    ],
                },
                "metadata": {},
            },
            {
                "id": "slide-3",
                "layout": "SplitScreen",
                "slots": {
                    "left": [
                        {"id": "b3", "type": "Text", "content": "Concept"},
                    ],
                },
                "metadata": {},
            },
        ],
    }


# ── DeckOutline validation ──────────────────────────────────────────────────


class TestDeckOutlineValidation:
    def test_valid_outline_passes(self):
        outline = _valid_outline()
        assert len(outline.slides) == 3
        assert outline.slides[0].role == "cover"
        assert outline.slides[0].layout == "FocusTitle"

    def test_first_slide_must_be_cover(self):
        slides = [_agenda_contract(), _cover_contract(), _concept_contract()]
        # Fix indexes to be contiguous
        slides[0].index = 1
        slides[1].index = 2
        slides[2].index = 3
        with pytest.raises(ValidationError, match="cover"):
            DeckOutline(
                topic="TCP",
                title="TCP",
                theme="theme-logic-blue",
                audience_level="beginner",
                narrative="test",
                slides=slides,
            )

    def test_first_slide_must_use_focus_title_layout(self):
        bad_cover = SlideContract(
            slide_id="s1",
            index=1,
            role="cover",
            title="Cover",
            learning_objective="Intro",
            layout="SplitScreen",  # wrong layout for cover
            blocks=[
                BlockContract(
                    block_id="b1",
                    slot="main",
                    type="Heading",
                    required_fields=["level", "content"],
                    content_hint="Title",
                ),
            ],
        )
        with pytest.raises(ValidationError, match="FocusTitle"):
            DeckOutline(
                topic="TCP",
                title="TCP",
                theme="theme-logic-blue",
                audience_level="beginner",
                narrative="test",
                slides=[bad_cover, _agenda_contract(), _concept_contract()],
            )

    def test_indexes_must_be_contiguous_from_1(self):
        slides = [_cover_contract(), _agenda_contract(), _concept_contract()]
        slides[0].index = 1
        slides[1].index = 3  # gap
        slides[2].index = 4
        with pytest.raises(ValidationError, match="contiguous"):
            DeckOutline(
                topic="TCP",
                title="TCP",
                theme="theme-logic-blue",
                audience_level="beginner",
                narrative="test",
                slides=slides,
            )

    def test_empty_slides_rejected(self):
        with pytest.raises(ValidationError, match="at least one slide"):
            DeckOutline(
                topic="TCP",
                title="TCP",
                theme="theme-logic-blue",
                audience_level="beginner",
                narrative="test",
                slides=[],
            )

    def test_slide_with_no_blocks_rejected(self):
        empty_slide = SlideContract(
            slide_id="s1",
            index=1,
            role="cover",
            title="Cover",
            learning_objective="Intro",
            layout="FocusTitle",
            blocks=[],  # no blocks
        )
        with pytest.raises(ValidationError, match="no blocks"):
            DeckOutline(
                topic="TCP",
                title="TCP",
                theme="theme-logic-blue",
                audience_level="beginner",
                narrative="test",
                slides=[empty_slide, _agenda_contract(), _concept_contract()],
            )


# ── PptPayload backward compat ──────────────────────────────────────────────


class TestPptPayloadBackwardCompat:
    def test_valid_payload_passes(self):
        payload = PptPayload.model_validate(_valid_ppt_payload())
        assert payload.template_id == "theme-logic-blue"
        assert len(payload.slides) == 3

    def test_rejects_too_few_slides(self):
        data = _valid_ppt_payload()
        data["slides"] = data["slides"][:2]
        with pytest.raises(ValidationError, match="at least 3"):
            PptPayload.model_validate(data)

    def test_extra_fields_forbidden(self):
        data = _valid_ppt_payload()
        data["extra_field"] = "not allowed"
        with pytest.raises(ValidationError, match="extra"):
            PptPayload.model_validate(data)

    def test_import_from_ppt_module_still_works(self):
        """Existing code that imports from ppt.py must still work."""
        from app.resource.agents.ppt import PptPayload as PptPayloadFromPpt
        from app.resource.agents.ppt import PptSlide as PptSlideFromPpt

        assert PptPayloadFromPpt is PptPayload
        assert PptSlideFromPpt is PptSlide


# ── MaterialBundle ──────────────────────────────────────────────────────────


class TestMaterialBundle:
    def test_create_with_no_artifacts(self):
        bundle = MaterialBundle(learning_need="TCP 三次握手")
        assert bundle.learning_need == "TCP 三次握手"
        assert bundle.artifacts == {}

    def test_create_with_artifacts(self):
        artifact = MaterialArtifact(
            agent_id="content",
            title="TCP 详解",
            summary="核心内容",
            content="详细内容...",
        )
        bundle = MaterialBundle(
            learning_need="TCP",
            artifacts={"content": artifact},
        )
        assert "content" in bundle.artifacts
        assert bundle.artifacts["content"].title == "TCP 详解"
        assert bundle.artifacts["content"].success is True

    def test_artifact_defaults(self):
        artifact = MaterialArtifact(agent_id="code")
        assert artifact.title == ""
        assert artifact.summary == ""
        assert artifact.content == ""
        assert artifact.success is True

    def test_bundle_with_profile_and_blueprint(self):
        bundle = MaterialBundle(
            learning_need="Python",
            profile={"level": "beginner"},
            blueprint={"sections": ["basics", "control flow"]},
        )
        assert bundle.profile["level"] == "beginner"
        assert bundle.blueprint["sections"][0] == "basics"


# ── SlideDraft ──────────────────────────────────────────────────────────────


class TestSlideDraft:
    def test_create_with_rendered_blocks(self):
        draft = SlideDraft(
            slide_id="s1",
            index=1,
            title="Intro",
            blocks=[
                RenderedBlock(
                    block_id="b1",
                    type="Heading",
                    data={"level": 1, "content": "Welcome"},
                ),
                RenderedBlock(
                    block_id="b2",
                    type="Text",
                    data={"content": "Some text here"},
                ),
            ],
            speaker_notes="Welcome the audience.",
        )
        assert len(draft.blocks) == 2
        assert draft.blocks[0].type == "Heading"
        assert draft.blocks[1].data["content"] == "Some text here"
        assert draft.source_refs == []

    def test_with_source_refs(self):
        draft = SlideDraft(
            slide_id="s3",
            index=3,
            title="Code Demo",
            blocks=[
                RenderedBlock(block_id="b1", type="Code", data={"code": "print('hi')"}),
            ],
            speaker_notes="Show the code",
            source_refs=["code", "content"],
        )
        assert draft.source_refs == ["code", "content"]


# ── DeckConstraints ─────────────────────────────────────────────────────────


class TestDeckConstraints:
    def test_defaults(self):
        c = DeckConstraints(page_count=6)
        assert c.difficulty == "normal"
        assert c.theme is None

    def test_page_count_bounds(self):
        with pytest.raises(ValidationError):
            DeckConstraints(page_count=2)
        with pytest.raises(ValidationError):
            DeckConstraints(page_count=21)
        DeckConstraints(page_count=3)
        DeckConstraints(page_count=20)


# ── MaterialDigest ──────────────────────────────────────────────────────────


class TestMaterialDigest:
    def test_create_with_all_fields(self):
        digest = MaterialDigest(
            topic="TCP",
            audience="beginners",
            learning_goal="Understand TCP handshake",
            core_concepts=["SYN", "ACK"],
            examples=["Three-way handshake example"],
            source_map={"SYN": ["content"], "ACK": ["content", "code"]},
        )
        assert len(digest.core_concepts) == 2
        assert digest.source_map["ACK"] == ["content", "code"]

    def test_defaults(self):
        digest = MaterialDigest(
            topic="TCP",
            audience="beginners",
            learning_goal="Understand handshake",
        )
        assert digest.core_concepts == []
        assert digest.source_map == {}


# ── PPT Manifest ────────────────────────────────────────────────────────────


class TestGetLayoutSlots:
    def test_focus_title_slots(self):
        slots = get_layout_slots("FocusTitle")
        assert "main" in slots
        assert "Heading" in slots["main"]

    def test_split_screen_slots(self):
        slots = get_layout_slots("SplitScreen")
        assert "left" in slots
        assert "right" in slots
        assert "Terminal" in slots["right"]

    def test_bento_grid_slots(self):
        slots = get_layout_slots("BentoGrid")
        assert "main" in slots

    def test_layer_stack_slots(self):
        slots = get_layout_slots("LayerStack")
        assert "main" in slots
        assert "Timeline" in slots["main"]

    def test_raises_for_unsupported_layout(self):
        with pytest.raises(ValueError, match="not in the manifest"):
            get_layout_slots("NonExistentLayout")  # type: ignore[arg-type]


class TestGetBlockRequiredFields:
    @pytest.mark.parametrize(
        "block_type,expected",
        [
            ("Heading", ["text"]),
            ("Text", ["text"]),
            ("Callout", ["text", "tone"]),
            ("Code", ["language", "code"]),
            ("BigNumber", ["value", "label"]),
            ("Formula", ["latex"]),
            ("Timeline", ["items"]),
            ("Terminal", ["command", "output"]),
        ],
    )
    def test_returns_correct_fields(self, block_type, expected):
        assert get_block_required_fields(block_type) == expected

    def test_raises_for_unsupported_block_type(self):
        with pytest.raises(ValueError, match="not in the manifest"):
            get_block_required_fields("NonExistentBlock")  # type: ignore[arg-type]


class TestValidateContractAgainstManifest:
    def test_valid_focus_title_cover_contract(self):
        contract = SlideContract(
            slide_id="s1",
            index=1,
            role="cover",
            title="TCP",
            learning_objective="Understand",
            layout="FocusTitle",
            blocks=[
                BlockContract(
                    block_id="b1",
                    slot="main",
                    type="Heading",
                    required_fields=["text"],
                    content_hint="Title",
                ),
            ],
        )
        validate_contract_against_manifest(contract)  # no error

    def test_valid_split_screen_concept_contract(self):
        contract = SlideContract(
            slide_id="s2",
            index=2,
            role="concept",
            title="Concept",
            learning_objective="Learn",
            layout="SplitScreen",
            blocks=[
                BlockContract(
                    block_id="b1",
                    slot="left",
                    type="Text",
                    required_fields=["text"],
                    content_hint="Explanation",
                ),
                BlockContract(
                    block_id="b2",
                    slot="right",
                    type="Code",
                    required_fields=["language", "code"],
                    content_hint="Example code",
                ),
            ],
        )
        validate_contract_against_manifest(contract)  # no error

    def test_fails_for_unsupported_layout(self):
        contract = SlideContract(
            slide_id="s1",
            index=1,
            role="cover",
            title="Bad",
            learning_objective="None",
            layout="FocusTitle",
            blocks=[
                BlockContract(
                    block_id="b1",
                    slot="main",
                    type="Heading",
                    required_fields=["text"],
                    content_hint="Title",
                ),
            ],
        )
        # Manually set an invalid layout value
        contract.layout = "NonExistentLayout"  # type: ignore[assignment]
        with pytest.raises(ValueError, match="not in the manifest"):
            validate_contract_against_manifest(contract)

    def test_fails_for_unsupported_slot(self):
        contract = SlideContract(
            slide_id="s1",
            index=1,
            role="cover",
            title="Bad",
            learning_objective="None",
            layout="FocusTitle",
            blocks=[
                BlockContract(
                    block_id="b1",
                    slot="nonexistent_slot",
                    type="Heading",
                    required_fields=["text"],
                    content_hint="Title",
                ),
            ],
        )
        with pytest.raises(ValueError, match="not defined in layout"):
            validate_contract_against_manifest(contract)

    def test_fails_for_unsupported_block_type_in_slot(self):
        contract = SlideContract(
            slide_id="s1",
            index=1,
            role="cover",
            title="Bad",
            learning_objective="None",
            layout="FocusTitle",
            blocks=[
                BlockContract(
                    block_id="b1",
                    slot="main",
                    type="Terminal",
                    required_fields=["commands"],
                    content_hint="Terminal",
                ),
            ],
        )
        with pytest.raises(ValueError, match="not allowed in slot"):
            validate_contract_against_manifest(contract)

    def test_fails_for_wrong_required_fields(self):
        contract = SlideContract(
            slide_id="s1",
            index=1,
            role="cover",
            title="Bad",
            learning_objective="None",
            layout="FocusTitle",
            blocks=[
                BlockContract(
                    block_id="b1",
                    slot="main",
                    type="Heading",
                    required_fields=["level", "content"],
                    content_hint="Title",
                ),
            ],
        )
        with pytest.raises(ValueError, match="required_fields"):
            validate_contract_against_manifest(contract)


# ── MaterialAgent ────────────────────────────────────────────────────────────


class TestMaterialAgent:
    @pytest.mark.asyncio
    async def test_material_agent_requests_material_digest(self, monkeypatch):
        """MaterialAgent 调用 LLM 并请求 MaterialDigest schema。"""
        from app.resource.agents.ppt_internal import MaterialAgent
        from app.resource.agents.ppt_models import MaterialBundle, MaterialDigest

        captured_schema = None
        captured_fn_name = None

        class FakeLlm:
            async def ainvoke_json(self, schema, input_data, **kwargs):
                nonlocal captured_schema, captured_fn_name
                captured_schema = schema
                captured_fn_name = kwargs.get("function_name")
                return MaterialDigest(
                    topic="TCP 三次握手",
                    audience="计算机专业学生",
                    learning_goal="理解 TCP 连接建立过程",
                    core_concepts=["SYN", "ACK", "三次握手"],
                    examples=["TCP 连接建立示例"],
                    misconceptions=["两次握手就够了"],
                )

        from app.resource.agents import ppt_internal as mod
        monkeypatch.setattr(mod, "get_llm", lambda: FakeLlm())

        bundle = MaterialBundle(learning_need="学习 TCP")
        agent = MaterialAgent()
        result = await agent.run(bundle)

        assert captured_schema is MaterialDigest
        assert captured_fn_name == "ppt_material"
        assert result.topic == "TCP 三次握手"


# ── OutlineAgent ─────────────────────────────────────────────────────────────


class TestOutlineAgent:
    @pytest.mark.asyncio
    async def test_outline_agent_requests_deck_outline(self, monkeypatch):
        """OutlineAgent 调用 LLM 并请求 DeckOutline schema，返回含 SlideContract。"""
        from app.resource.agents.ppt_internal import OutlineAgent
        from app.resource.agents.ppt_models import (
            MaterialDigest, DeckConstraints, DeckOutline, SlideContract,
            BlockContract, ThemeType, LayoutType,
        )

        captured_schema = None
        captured_fn_name = None

        class FakeLlm:
            async def ainvoke_json(self, schema, input_data, **kwargs):
                nonlocal captured_schema, captured_fn_name
                captured_schema = schema
                captured_fn_name = kwargs.get("function_name")
                return DeckOutline(
                    topic="TCP",
                    title="TCP 三次握手",
                    theme="theme-logic-blue",
                    audience_level="intermediate",
                    narrative="从连接建立到可靠性保证",
                    slides=[
                        SlideContract(
                            slide_id="s1", index=1, role="cover",
                            title="TCP 三次握手", learning_objective="理解连接建立",
                            layout="FocusTitle",
                            blocks=[
                                BlockContract(block_id="b1", slot="main", type="Heading",
                                              required_fields=["text"], content_hint="主标题"),
                                BlockContract(block_id="b2", slot="main", type="Text",
                                              required_fields=["text"], content_hint="副标题"),
                            ],
                        ),
                        SlideContract(
                            slide_id="s2", index=2, role="concept",
                            title="SYN 报文交换机制", learning_objective="理解 SYN 报文",
                            source_agents=["content"],
                            layout="SplitScreen",
                            blocks=[
                                BlockContract(block_id="b3", slot="left", type="Heading",
                                              required_fields=["text"], content_hint="左侧标题"),
                                BlockContract(block_id="b4", slot="right", type="Code",
                                              required_fields=["language", "code"], content_hint="代码示例"),
                            ],
                        ),
                        SlideContract(
                            slide_id="s3", index=3, role="summary",
                            title="总结", learning_objective="回顾要点",
                            layout="FocusTitle",
                            blocks=[
                                BlockContract(block_id="b5", slot="main", type="Heading",
                                              required_fields=["text"], content_hint="总结标题"),
                            ],
                        ),
                    ],
                )

        from app.resource.agents import ppt_internal as mod
        monkeypatch.setattr(mod, "get_llm", lambda: FakeLlm())

        digest = MaterialDigest(topic="TCP", audience="学生", learning_goal="理解握手")
        constraints = DeckConstraints(page_count=3, difficulty="normal")
        agent = OutlineAgent()
        result = await agent.run(digest, constraints)

        assert captured_schema is DeckOutline
        assert captured_fn_name == "ppt_outline"
        assert len(result.slides) == 3
        assert result.slides[0].role == "cover"
        assert result.slides[1].layout == "SplitScreen"


    @pytest.mark.asyncio
    async def test_outline_agent_rejects_wrong_page_count(self, monkeypatch):
        """OutlineAgent must reject outlines that do not match DeckConstraints.page_count."""
        from app.resource.agents.ppt_internal import OutlineAgent
        from app.resource.agents.ppt_models import (
            MaterialDigest, DeckConstraints, DeckOutline, SlideContract, BlockContract,
        )

        class FakeLlm:
            async def ainvoke_json(self, schema, input_data, **kwargs):
                return DeckOutline(
                    topic="TCP",
                    title="TCP 三次握手",
                    theme="theme-logic-blue",
                    audience_level="intermediate",
                    narrative="从连接建立到可靠性保证",
                    slides=[
                        SlideContract(
                            slide_id="s1", index=1, role="cover",
                            title="TCP 三次握手", learning_objective="理解连接建立",
                            layout="FocusTitle",
                            blocks=[
                                BlockContract(block_id="b1", slot="main", type="Heading",
                                              required_fields=["text"], content_hint="主标题"),
                            ],
                        ),
                        SlideContract(
                            slide_id="s2", index=2, role="agenda",
                            title="本讲要点", learning_objective="了解本课结构",
                            layout="BentoGrid",
                            blocks=[
                                BlockContract(block_id="b2", slot="main", type="Text",
                                              required_fields=["text"], content_hint="目录要点"),
                            ],
                        ),
                    ],
                )

        from app.resource.agents import ppt_internal as mod
        monkeypatch.setattr(mod, "get_llm", lambda: FakeLlm())

        digest = MaterialDigest(topic="TCP", audience="学生", learning_goal="理解握手")
        constraints = DeckConstraints(page_count=3, difficulty="normal")

        with pytest.raises(ValueError, match="page_count"):
            await OutlineAgent().run(digest, constraints)


# ── SlideAgent ───────────────────────────────────────────────────────────────


class TestSlideAgent:
    @pytest.mark.asyncio
    async def test_slide_agent_requests_slide_draft(self, monkeypatch):
        """SlideAgent 调用 LLM 并请求 SlideDraft schema。"""
        from app.resource.agents.ppt_internal import SlideAgent
        from app.resource.agents.ppt_models import (
            SlideDraft, SlideContract, BlockContract, RenderedBlock,
            DeckOutline, MaterialDigest,
        )

        captured_schema = None
        captured_fn_name = None

        class FakeLlm:
            async def ainvoke_json(self, schema, input_data, **kwargs):
                nonlocal captured_schema, captured_fn_name
                captured_schema = schema
                captured_fn_name = kwargs.get("function_name")
                return SlideDraft(
                    slide_id="s1",
                    index=1,
                    title="TCP 三次握手",
                    blocks=[
                        RenderedBlock(block_id="b1", type="Heading", data={"text": "TCP 三次握手"}),
                        RenderedBlock(block_id="b2", type="Text", data={"text": "可靠连接的建立机制"}),
                    ],
                    speaker_notes="这是封面页",
                )

        from app.resource.agents import ppt_internal as mod
        monkeypatch.setattr(mod, "get_llm", lambda: FakeLlm())

        contract = SlideContract(
            slide_id="s1", index=1, role="cover",
            title="TCP 三次握手", learning_objective="理解连接建立",
            layout="FocusTitle",
            blocks=[
                BlockContract(block_id="b1", slot="main", type="Heading",
                              required_fields=["text"], content_hint="主标题"),
                BlockContract(block_id="b2", slot="main", type="Text",
                              required_fields=["text"], content_hint="副标题"),
            ],
        )
        digest = MaterialDigest(topic="TCP", audience="学生", learning_goal="理解握手")
        outline = DeckOutline(
            topic="TCP", title="TCP", theme="theme-logic-blue",
            audience_level="intermediate", narrative="narrative",
            slides=[contract],
        )
        agent = SlideAgent()
        result = await agent.run(contract, digest, outline)

        assert captured_schema is SlideDraft
        assert captured_fn_name == "ppt_slide"
        assert result.slide_id == "s1"
        assert len(result.blocks) == 2

    @pytest.mark.asyncio
    async def test_slide_agent_rejects_missing_blocks(self, monkeypatch):
        """SlideDraft 缺少合约中声明的 block_id 时应失败。"""
        from app.resource.agents.ppt_internal import SlideAgent
        from app.resource.agents.ppt_models import (
            SlideDraft, SlideContract, BlockContract, RenderedBlock,
            DeckOutline, MaterialDigest,
        )

        class FakeLlm:
            async def ainvoke_json(self, schema, input_data, **kwargs):
                return SlideDraft(
                    slide_id="s1", index=1, title="测试",
                    blocks=[
                        RenderedBlock(block_id="b1", type="Heading", data={"text": "标题"}),
                        # Missing b2
                    ],
                    speaker_notes="备注",
                )

        from app.resource.agents import ppt_internal as mod
        monkeypatch.setattr(mod, "get_llm", lambda: FakeLlm())

        contract = SlideContract(
            slide_id="s1", index=1, role="cover",
            title="测试", learning_objective="测试",
            layout="FocusTitle",
            blocks=[
                BlockContract(block_id="b1", slot="main", type="Heading",
                              required_fields=["text"], content_hint="标题"),
                BlockContract(block_id="b2", slot="main", type="Text",
                              required_fields=["text"], content_hint="内容"),
            ],
        )
        digest = MaterialDigest(topic="TCP", audience="学生", learning_goal="理解握手")
        outline = DeckOutline(
            topic="TCP", title="TCP", theme="theme-logic-blue",
            audience_level="intermediate", narrative="narrative",
            slides=[contract],
        )
        agent = SlideAgent()
        with pytest.raises(ValueError, match="missing blocks"):
            await agent.run(contract, digest, outline)

    @pytest.mark.asyncio
    async def test_slide_agent_rejects_extra_blocks(self, monkeypatch):
        """SlideDraft 包含合约中未声明的 block_id 时应失败。"""
        from app.resource.agents.ppt_internal import SlideAgent
        from app.resource.agents.ppt_models import (
            SlideDraft, SlideContract, BlockContract, RenderedBlock,
            DeckOutline, MaterialDigest,
        )

        class FakeLlm:
            async def ainvoke_json(self, schema, input_data, **kwargs):
                return SlideDraft(
                    slide_id="s1", index=1, title="测试",
                    blocks=[
                        RenderedBlock(block_id="b1", type="Heading", data={"text": "标题"}),
                        RenderedBlock(block_id="b_extra", type="Text", data={"text": "多余"}),
                    ],
                    speaker_notes="备注",
                )

        from app.resource.agents import ppt_internal as mod
        monkeypatch.setattr(mod, "get_llm", lambda: FakeLlm())

        contract = SlideContract(
            slide_id="s1", index=1, role="cover",
            title="测试", learning_objective="测试",
            layout="FocusTitle",
            blocks=[
                BlockContract(block_id="b1", slot="main", type="Heading",
                              required_fields=["text"], content_hint="标题"),
            ],
        )
        digest = MaterialDigest(topic="TCP", audience="学生", learning_goal="理解握手")
        outline = DeckOutline(
            topic="TCP", title="TCP", theme="theme-logic-blue",
            audience_level="intermediate", narrative="narrative",
            slides=[contract],
        )
        agent = SlideAgent()
        with pytest.raises(ValueError, match="undeclared blocks"):
            await agent.run(contract, digest, outline)

    @pytest.mark.asyncio
    async def test_slide_agent_rejects_missing_required_block_field(self, monkeypatch):
        """SlideDraft data must include every required field from BlockContract.required_fields."""
        from app.resource.agents.ppt_internal import SlideAgent
        from app.resource.agents.ppt_models import (
            SlideDraft, SlideContract, BlockContract, RenderedBlock,
            DeckOutline, MaterialDigest,
        )

        class FakeLlm:
            async def ainvoke_json(self, schema, input_data, **kwargs):
                return SlideDraft(
                    slide_id="s1", index=1, title="代码演示",
                    blocks=[
                        RenderedBlock(block_id="b1", type="Code", data={"language": "python"}),
                    ],
                    speaker_notes="讲解代码",
                )

        from app.resource.agents import ppt_internal as mod
        monkeypatch.setattr(mod, "get_llm", lambda: FakeLlm())

        contract = SlideContract(
            slide_id="s1", index=1, role="cover",
            title="代码演示", learning_objective="理解代码",
            layout="FocusTitle",
            blocks=[
                BlockContract(block_id="b1", slot="main", type="Code",
                              required_fields=["language", "code"], content_hint="代码块"),
            ],
        )
        outline = DeckOutline(
            topic="Python", title="Python", theme="theme-logic-blue",
            audience_level="intermediate", narrative="代码讲解", slides=[contract],
        )
        digest = MaterialDigest(topic="Python", audience="学生", learning_goal="理解代码")

        with pytest.raises(ValueError, match="missing required field"):
            await SlideAgent().run(contract, digest, outline)

    @pytest.mark.asyncio
    async def test_slide_agent_rejects_empty_required_block_field(self, monkeypatch):
        """Required string fields must not be blank."""
        from app.resource.agents.ppt_internal import SlideAgent
        from app.resource.agents.ppt_models import (
            SlideDraft, SlideContract, BlockContract, RenderedBlock,
            DeckOutline, MaterialDigest,
        )

        class FakeLlm:
            async def ainvoke_json(self, schema, input_data, **kwargs):
                return SlideDraft(
                    slide_id="s1", index=1, title="空正文",
                    blocks=[
                        RenderedBlock(block_id="b1", type="Text", data={"text": "   "}),
                    ],
                    speaker_notes="讲解正文",
                )

        from app.resource.agents import ppt_internal as mod
        monkeypatch.setattr(mod, "get_llm", lambda: FakeLlm())

        contract = SlideContract(
            slide_id="s1", index=1, role="cover",
            title="空正文", learning_objective="避免空正文",
            layout="FocusTitle",
            blocks=[
                BlockContract(block_id="b1", slot="main", type="Text",
                              required_fields=["text"], content_hint="正文"),
            ],
        )
        outline = DeckOutline(
            topic="Python", title="Python", theme="theme-logic-blue",
            audience_level="intermediate", narrative="正文讲解", slides=[contract],
        )
        digest = MaterialDigest(topic="Python", audience="学生", learning_goal="理解正文")

        with pytest.raises(ValueError, match="empty required field"):
            await SlideAgent().run(contract, digest, outline)


# ── write_slides_concurrently ────────────────────────────────────────────────


class TestWriteSlidesConcurrently:
    @pytest.mark.asyncio
    async def test_concurrent_slide_writing_preserves_order(self, monkeypatch):
        """并发写幻灯片保持顺序。"""
        from app.resource.agents.ppt_internal import write_slides_concurrently, SlideAgent
        from app.resource.agents.ppt_models import (
            SlideDraft, SlideContract, BlockContract, RenderedBlock,
            DeckOutline, MaterialDigest,
        )

        # Use a shared mutable list to track which contracts are processed
        call_count = 0

        class FakeLlm:
            async def ainvoke_json(self, schema, input_data, **kwargs):
                nonlocal call_count
                call_count += 1
                # Parse the slide_contract from input to return matching draft.
                # The input is "prompt_text\n\n{json}" — find the JSON by
                # locating the first '{' character.
                idx = call_count
                sid = f"s{idx}"
                if isinstance(input_data, str):
                    brace_pos = input_data.find("{")
                    if brace_pos >= 0:
                        import json as _json
                        try:
                            data = _json.loads(input_data[brace_pos:])
                            contract_data = data.get("slide_contract", {})
                            sid = contract_data.get("slide_id", sid)
                            idx = contract_data.get("index", idx)
                        except Exception:
                            pass
                return SlideDraft(
                    slide_id=sid, index=idx, title="测试",
                    blocks=[
                        RenderedBlock(block_id="b1", type="Heading", data={"text": "标题"}),
                    ],
                    speaker_notes="备注",
                )

        from app.resource.agents import ppt_internal as mod
        monkeypatch.setattr(mod, "get_llm", lambda: FakeLlm())

        contracts = [
            SlideContract(
                slide_id="s1", index=1, role="cover",
                title="封面", learning_objective="概览",
                layout="FocusTitle",
                blocks=[
                    BlockContract(block_id="b1", slot="main", type="Heading",
                                  required_fields=["text"], content_hint="标题"),
                ],
            ),
            SlideContract(
                slide_id="s2", index=2, role="concept",
                title="Slide 2", learning_objective="Objective 2",
                layout="FocusTitle",
                blocks=[
                    BlockContract(block_id="b1", slot="main", type="Heading",
                                  required_fields=["text"], content_hint="标题"),
                ],
            ),
            SlideContract(
                slide_id="s3", index=3, role="concept",
                title="Slide 3", learning_objective="Objective 3",
                layout="FocusTitle",
                blocks=[
                    BlockContract(block_id="b1", slot="main", type="Heading",
                                  required_fields=["text"], content_hint="标题"),
                ],
            ),
        ]
        outline = DeckOutline(
            topic="测试", title="测试", theme="theme-logic-blue",
            audience_level="intermediate", narrative="narrative",
            slides=contracts,
        )
        digest = MaterialDigest(topic="测试", audience="学生", learning_goal="测试")

        agent = SlideAgent()
        drafts = await write_slides_concurrently(agent, outline, digest, concurrency=2)

        assert len(drafts) == 3
        assert [d.index for d in drafts] == [1, 2, 3]


# ── PayloadBuilder ────────────────────────────────────────────────────────────


class TestPayloadBuilder:
    def _make_outline_and_drafts(self):
        """Helper to create a minimal DeckOutline + matching SlideDrafts for 3 slides."""
        from app.resource.agents.ppt_models import (
            DeckOutline, SlideContract, BlockContract,
            SlideDraft, RenderedBlock,
        )
        outline = DeckOutline(
            topic="TCP", title="TCP 三次握手", theme="theme-logic-blue",
            audience_level="intermediate", narrative="从连接到可靠性",
            slides=[
                SlideContract(
                    slide_id="s1", index=1, role="cover",
                    title="TCP 三次握手", learning_objective="理解连接建立",
                    layout="FocusTitle",
                    blocks=[
                        BlockContract(block_id="b1", slot="main", type="Heading",
                                      required_fields=["text"], content_hint="主标题"),
                        BlockContract(block_id="b2", slot="main", type="Text",
                                      required_fields=["text"], content_hint="副标题"),
                    ],
                ),
                SlideContract(
                    slide_id="s2", index=2, role="agenda",
                    title="本讲要点", learning_objective="了解课程结构",
                    layout="BentoGrid",
                    blocks=[
                        BlockContract(block_id="b3", slot="main", type="Heading",
                                      required_fields=["text"], content_hint="标题"),
                        BlockContract(block_id="b4", slot="main", type="Text",
                                      required_fields=["text"], content_hint="要点列表"),
                    ],
                ),
                SlideContract(
                    slide_id="s3", index=3, role="concept",
                    title="SYN 报文交换", learning_objective="理解 SYN 机制",
                    layout="SplitScreen",
                    blocks=[
                        BlockContract(block_id="b5", slot="left", type="Heading",
                                      required_fields=["text"], content_hint="左侧标题"),
                        BlockContract(block_id="b6", slot="right", type="Code",
                                      required_fields=["language", "code"], content_hint="代码示例"),
                    ],
                ),
            ],
        )
        drafts = [
            SlideDraft(
                slide_id="s1", index=1, title="TCP 三次握手",
                blocks=[
                    RenderedBlock(block_id="b1", type="Heading", data={"text": "TCP 三次握手", "level": 1}),
                    RenderedBlock(block_id="b2", type="Text", data={"text": "可靠连接的建立机制"}),
                ],
                speaker_notes="这是封面页",
            ),
            SlideDraft(
                slide_id="s2", index=2, title="本讲要点",
                blocks=[
                    RenderedBlock(block_id="b3", type="Heading", data={"text": "本讲要点"}),
                    RenderedBlock(block_id="b4", type="Text", data={"text": "1. 连接建立 2. 可靠性 3. 流量控制"}),
                ],
                speaker_notes="介绍本讲内容",
            ),
            SlideDraft(
                slide_id="s3", index=3, title="SYN 报文交换",
                blocks=[
                    RenderedBlock(block_id="b5", type="Heading", data={"text": "SYN 报文"}),
                    RenderedBlock(block_id="b6", type="Code", data={"language": "python", "code": "syn = packet()"}),
                ],
                speaker_notes="讲解 SYN 报文",
                source_refs=["content"],
            ),
        ]
        return outline, drafts

    def test_build_cover_slide(self):
        """PayloadBuilder 正确构建封面页。"""
        from app.resource.agents.ppt_builder import PayloadBuilder
        outline, drafts = self._make_outline_and_drafts()
        builder = PayloadBuilder()
        payload = builder.build(outline, drafts)

        cover = payload.slides[0]
        assert cover.layout == "FocusTitle"
        assert cover.id == "s1"
        assert "main" in cover.slots
        assert len(cover.slots["main"]) == 2
        assert cover.slots["main"][0].type == "Heading"
        assert cover.slots["main"][0].content == "TCP 三次握手"

    def test_build_agenda_slide(self):
        """PayloadBuilder 正确构建目录页。"""
        from app.resource.agents.ppt_builder import PayloadBuilder
        outline, drafts = self._make_outline_and_drafts()
        builder = PayloadBuilder()
        payload = builder.build(outline, drafts)

        agenda = payload.slides[1]
        assert agenda.layout == "BentoGrid"
        assert agenda.id == "s2"

    def test_build_split_screen_concept(self):
        """PayloadBuilder 正确构建 SplitScreen 概念页。"""
        from app.resource.agents.ppt_builder import PayloadBuilder
        outline, drafts = self._make_outline_and_drafts()
        builder = PayloadBuilder()
        payload = builder.build(outline, drafts)

        concept = payload.slides[2]
        assert concept.layout == "SplitScreen"
        assert "left" in concept.slots
        assert "right" in concept.slots
        assert concept.slots["right"][0].type == "Code"

    def test_build_full_payload(self):
        """PayloadBuilder 生成完整的 PptPayload。"""
        from app.resource.agents.ppt_builder import PayloadBuilder
        outline, drafts = self._make_outline_and_drafts()
        builder = PayloadBuilder()
        payload = builder.build(outline, drafts)

        assert payload.template_id == "theme-logic-blue"
        assert payload.topic == "TCP 三次握手"
        assert len(payload.slides) == 3

    def test_build_fails_on_missing_draft(self):
        """缺少 draft 时 PayloadBuilder 失败。"""
        from app.resource.agents.ppt_builder import PayloadBuilder
        from app.resource.agents.ppt_models import (
            DeckOutline, SlideContract, BlockContract,
        )
        outline = DeckOutline(
            topic="T", title="T", theme="theme-logic-blue",
            audience_level="beginner", narrative="n",
            slides=[
                SlideContract(
                    slide_id="s1", index=1, role="cover",
                    title="T", learning_objective="T",
                    layout="FocusTitle",
                    blocks=[
                        BlockContract(block_id="b1", slot="main", type="Heading",
                                      required_fields=["text"], content_hint="h"),
                    ],
                ),
            ],
        )
        builder = PayloadBuilder()
        with pytest.raises(ValueError, match="Missing draft"):
            builder.build(outline, [])

    def test_speaker_notes_in_metadata(self):
        """speaker_notes 存入 slide metadata。"""
        from app.resource.agents.ppt_builder import PayloadBuilder
        outline, drafts = self._make_outline_and_drafts()
        builder = PayloadBuilder()
        payload = builder.build(outline, drafts)

        assert payload.slides[2].metadata.get("speaker_notes") == "讲解 SYN 报文"
        assert payload.slides[2].metadata.get("source_refs") == ["content"]

    def test_builder_rejects_missing_required_text_instead_of_empty_output(self):
        """PayloadBuilder must not silently create an empty Text block."""
        from app.resource.agents.ppt_builder import PayloadBuilder
        from app.resource.agents.ppt_models import (
            DeckOutline, SlideContract, BlockContract,
            SlideDraft, RenderedBlock,
        )

        outline = DeckOutline(
            topic="T", title="T", theme="theme-logic-blue",
            audience_level="beginner", narrative="n",
            slides=[
                SlideContract(
                    slide_id="s1", index=1, role="cover",
                    title="T", learning_objective="T", layout="FocusTitle",
                    blocks=[BlockContract(block_id="b1", slot="main", type="Text",
                                          required_fields=["text"], content_hint="正文")],
                ),
                SlideContract(
                    slide_id="s2", index=2, role="agenda",
                    title="目录", learning_objective="目录", layout="BentoGrid",
                    blocks=[BlockContract(block_id="b2", slot="main", type="Text",
                                          required_fields=["text"], content_hint="目录")],
                ),
                SlideContract(
                    slide_id="s3", index=3, role="summary",
                    title="总结", learning_objective="总结", layout="FocusTitle",
                    blocks=[BlockContract(block_id="b3", slot="main", type="Text",
                                          required_fields=["text"], content_hint="总结")],
                ),
            ],
        )
        drafts = [
            SlideDraft(slide_id="s1", index=1, title="T",
                blocks=[RenderedBlock(block_id="b1", type="Text", data={})],
                speaker_notes="封面"),
            SlideDraft(slide_id="s2", index=2, title="目录",
                blocks=[RenderedBlock(block_id="b2", type="Text", data={"text": "目录"})],
                speaker_notes="目录"),
            SlideDraft(slide_id="s3", index=3, title="总结",
                blocks=[RenderedBlock(block_id="b3", type="Text", data={"text": "总结"})],
                speaker_notes="总结"),
        ]

        with pytest.raises(ValueError, match="missing required field"):
            PayloadBuilder().build(outline, drafts)

    def test_code_demo_block(self):
        """Code block 正确转换。"""
        from app.resource.agents.ppt_builder import PayloadBuilder
        from app.resource.agents.ppt_models import (
            DeckOutline, SlideContract, BlockContract,
            SlideDraft, RenderedBlock,
        )
        outline = DeckOutline(
            topic="T", title="T", theme="theme-logic-blue",
            audience_level="beginner", narrative="n",
            slides=[
                SlideContract(slide_id="s1", index=1, role="cover",
                    title="T", learning_objective="T", layout="FocusTitle",
                    blocks=[BlockContract(block_id="b1", slot="main", type="Heading",
                              required_fields=["text"], content_hint="h")]),
                SlideContract(slide_id="s2", index=2, role="agenda",
                    title="T", learning_objective="T", layout="BentoGrid",
                    blocks=[BlockContract(block_id="b2", slot="main", type="Text",
                              required_fields=["text"], content_hint="t")]),
                SlideContract(slide_id="s3", index=3, role="code_demo",
                    title="Code Demo", learning_objective="Code", layout="SplitScreen",
                    blocks=[
                        BlockContract(block_id="b5", slot="left", type="Heading",
                                      required_fields=["text"], content_hint="h"),
                        BlockContract(block_id="b6", slot="right", type="Code",
                                      required_fields=["language", "code"], content_hint="c"),
                    ]),
            ],
        )
        drafts = [
            SlideDraft(slide_id="s1", index=1, title="T",
                blocks=[RenderedBlock(block_id="b1", type="Heading", data={"text": "T"})],
                speaker_notes=""),
            SlideDraft(slide_id="s2", index=2, title="T",
                blocks=[RenderedBlock(block_id="b2", type="Text", data={"text": "agenda"})],
                speaker_notes=""),
            SlideDraft(slide_id="s3", index=3, title="Code Demo",
                blocks=[
                    RenderedBlock(block_id="b5", type="Heading", data={"text": "Demo"}),
                    RenderedBlock(block_id="b6", type="Code", data={"language": "go", "code": "func main() {}"}),
                ],
                speaker_notes="代码演示"),
        ]
        builder = PayloadBuilder()
        payload = builder.build(outline, drafts)

        code_slide = payload.slides[2]
        assert code_slide.layout == "SplitScreen"
        code_block = code_slide.slots["right"][0]
        assert code_block.type == "Code"
        assert code_block.language == "go"
        assert code_block.code == "func main() {}"
