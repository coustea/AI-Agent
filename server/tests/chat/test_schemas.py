from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from app.chat.schemas import (
    Evidence,
    EvidenceSet,
    TutorAgentInput,
    TutorRequestContext,
    UploadResponse,
    normalize_tool_result,
)

from app.chat.schemas.evidence import NormalizedToolResult, SourceItem
from app.chat.schemas.diagram import (
    ComparisonDimension,
    ComparisonEntity,
    ComparisonPayload,
    FlowchartEdge,
    FlowchartNode,
    FlowchartPayload,
    FrameworkModule,
    FrameworkPayload,
    HierarchyBranch,
    HierarchyPayload,
    SequenceMessage,
    SequencePayload,
    SummaryCard,
    SummaryPayload,
    TeachingContent,
    TeachingDiagram,
    VisualSummary,
)


# ── Evidence / EvidenceSet ──


class TestEvidence:
    def test_defaults(self):
        e = Evidence(evidence_type="web_search", summary="hello")
        assert e.confidence == 0.7
        assert e.freshness == "turn"
        assert e.usable_for_answer is True
        assert e.usable_for_diagram is True
        assert e.details == {}

    def test_custom_values(self):
        e = Evidence(
            evidence_type="knowledge_base",
            summary="info",
            confidence=0.95,
            freshness="persistent",
            usable_for_answer=False,
        )
        assert e.confidence == 0.95
        assert e.freshness == "persistent"
        assert e.usable_for_answer is False


class TestEvidenceSet:
    def test_for_answer_filters(self):
        items = [
            Evidence(evidence_type="web_search", summary="a", usable_for_answer=True),
            Evidence(evidence_type="knowledge_base", summary="b", usable_for_answer=False),
        ]
        es = EvidenceSet(items=items)
        answer_items = [i for i in es.items if i.usable_for_answer]
        assert len(answer_items) == 1
        assert answer_items[0].summary == "a"

    def test_for_diagram_filters(self):
        items = [
            Evidence(evidence_type="web_search", summary="a", usable_for_diagram=True),
            Evidence(evidence_type="knowledge_base", summary="b", usable_for_diagram=False),
        ]
        es = EvidenceSet(items=items)
        diagram_items = [i for i in es.items if i.usable_for_diagram]
        assert len(diagram_items) == 1
        assert diagram_items[0].summary == "a"

    def test_extend(self):
        es = EvidenceSet()
        es.extend([Evidence(evidence_type="web_search", summary="x")])
        assert len(es.items) == 1

    def test_empty_set(self):
        es = EvidenceSet()
        assert es.items == []


# ── New Domain Models ──


class TestSourceItem:
    def test_defaults(self):
        s = SourceItem(source="web")
        assert s.title == ""
        assert s.url == ""
        assert s.published_at is None


class TestNormalizedToolResult:
    def test_defaults(self):
        r = NormalizedToolResult()
        assert r.text == ""
        assert r.sources == []
        assert r.metadata == {}


# ── normalize_tool_result ──


class TestNormalizeToolResult:
    def test_none(self):
        result = normalize_tool_result(None)
        assert result.text == ""
        assert result.sources == []

    def test_string(self):
        result = normalize_tool_result("hello world")
        assert result.text == "hello world"
        assert result.sources == []

    def test_empty_string(self):
        result = normalize_tool_result("")
        assert result.text == ""

    def test_dict_with_text(self):
        result = normalize_tool_result({"text": "answer", "url": "http://x"})
        assert result.text == "answer"
        assert result.metadata.get("url") == "http://x"

    def test_dict_with_message(self):
        result = normalize_tool_result({"message": "fallback text"})
        assert result.text == "fallback text"

    def test_dict_with_sources(self):
        result = normalize_tool_result({
            "text": "info",
            "sources": [{"source": "web", "url": "http://x", "title": "X"}],
        })
        assert result.text == "info"
        assert len(result.sources) == 1
        assert result.sources[0].url == "http://x"

    def test_dict_no_text_no_message(self):
        result = normalize_tool_result({"key": "value"})
        assert result.text == ""

    def test_pydantic_model(self):
        class FakeModel(BaseModel):
            text: str = ""
            extra: bool = False
        result = normalize_tool_result(FakeModel(text="from model", extra=True))
        assert result.text == "from model"
        assert result.metadata.get("extra") is True

    def test_int(self):
        result = normalize_tool_result(42)
        assert result.text == "42"


# ── UploadResponse ──


class TestUploadResponse:
    def test_minimal(self):
        r = UploadResponse(url="/api/v1/ai/chat/uploads/1/s1/f.txt")
        assert r.url == "/api/v1/ai/chat/uploads/1/s1/f.txt"
        assert r.file_type == "document"
        assert r.original_name == ""
        assert r.size_bytes == 0

    def test_full(self):
        r = UploadResponse(
            url="/u",
            file_type="image",
            original_name="pic.png",
            size_bytes=1024,
            storage_key="1/s1/pic.png",
            mime_type="image/png",
            extension=".png",
        )
        assert r.mime_type == "image/png"


# ── TutorRequestContext ──


class TestTutorRequestContext:
    def test_defaults(self):
        ctx = TutorRequestContext(user_id=1, username="test", session_id="s1", user_input="hi")
        assert ctx.enable_web_search is False
        assert ctx.need_teaching_diagram is False
        assert ctx.attachments == []


# ── TutorAgentInput ──


class TestTutorAgentInput:
    def test_minimal(self):
        inp = TutorAgentInput(user_id=1, username="test", session_id="s1", user_message_id=1, question="hi")
        assert inp.attachments == []
        assert inp.enable_web_search is False


# ── TeachingDiagram payload variants ──


class TestComparisonPayload:
    def _make(self):
        return ComparisonPayload(
            left_entity=ComparisonEntity(name="TCP", core_label="可靠协议", short_desc="面向连接"),
            right_entity=ComparisonEntity(name="UDP", core_label="不可靠协议", short_desc="无连接"),
            dimensions=[
                ComparisonDimension(name="连接", left="面向连接", right="无连接"),
                ComparisonDimension(name="可靠性", left="可靠", right="不可靠"),
            ],
            visual_summary=VisualSummary(left_keyword="可靠", right_keyword="快速", center_conclusion="各有适用场景"),
        )

    def test_min_length_violation(self):
        with pytest.raises(ValidationError):
            ComparisonPayload(
                left_entity=ComparisonEntity(name="A", core_label="a", short_desc="a"),
                right_entity=ComparisonEntity(name="B", core_label="b", short_desc="b"),
                dimensions=[ComparisonDimension(name="x", left="1", right="2")],
                visual_summary=VisualSummary(left_keyword="a", right_keyword="b", center_conclusion="c"),
            )

    def test_valid(self):
        p = self._make()
        assert len(p.dimensions) == 2


class TestFlowchartPayload:
    def _make(self):
        return FlowchartPayload(
            nodes=[
                FlowchartNode(id="n1", title="Start", type="start"),
                FlowchartNode(id="n2", title="End", type="end"),
            ],
            edges=[FlowchartEdge(from_="n1", to="n2")],
        )

    def test_valid(self):
        p = self._make()
        assert p.direction == "vertical"

    def test_edge_alias(self):
        edge = FlowchartEdge(**{"from": "a", "to": "b"})
        assert edge.from_ == "a"


class TestSequencePayload:
    def _make(self):
        return SequencePayload(
            actors=["Client", "Server"],
            messages=[SequenceMessage(from_="Client", to="Server", label="SYN")],
        )

    def test_valid(self):
        p = self._make()
        assert len(p.actors) == 2


class TestFrameworkPayload:
    def _make(self):
        return FrameworkPayload(
            center="Networking",
            modules=[
                FrameworkModule(title="L1", items=["Physical"]),
                FrameworkModule(title="L2", items=["Data Link"]),
            ],
        )

    def test_valid(self):
        p = self._make()
        assert len(p.modules) == 2


class TestSummaryPayload:
    def _make(self):
        return SummaryPayload(
            cards=[SummaryCard(title="Key", short_desc="desc"), SummaryCard(title="Key2", short_desc="desc2")]
        )

    def test_valid(self):
        p = self._make()
        assert len(p.cards) == 2


class TestHierarchyPayload:
    def _make(self):
        return HierarchyPayload(
            root="Root",
            branches=[
                HierarchyBranch(title="A", children=["a1"]),
                HierarchyBranch(title="B", children=["b1"]),
            ],
        )

    def test_valid(self):
        p = self._make()
        assert len(p.branches) == 2


# ── TeachingDiagram cross-type validation ──


class TestTeachingDiagram:
    def _base_content(self):
        return TeachingContent(core_explanation="test", summary="test summary")

    def test_comparison_valid(self):
        td = TeachingDiagram(
            graph_type="comparison",
            title="TCP vs UDP",
            teaching_goal="对比",
            visual_content=ComparisonPayload(
                left_entity=ComparisonEntity(name="A", core_label="a", short_desc="a"),
                right_entity=ComparisonEntity(name="B", core_label="b", short_desc="b"),
                dimensions=[
                    ComparisonDimension(name="x", left="1", right="2"),
                    ComparisonDimension(name="y", left="3", right="4"),
                ],
                visual_summary=VisualSummary(left_keyword="a", right_keyword="b", center_conclusion="c"),
            ),
            teaching_content=self._base_content(),
        )
        assert td.graph_type == "comparison"

    def test_mismatch_raises(self):
        with pytest.raises(ValidationError, match="visual_content must match graph_type"):
            TeachingDiagram(
                graph_type="flowchart",
                title="Mismatch",
                teaching_goal="test",
                visual_content=ComparisonPayload(
                    left_entity=ComparisonEntity(name="A", core_label="a", short_desc="a"),
                    right_entity=ComparisonEntity(name="B", core_label="b", short_desc="b"),
                    dimensions=[
                        ComparisonDimension(name="x", left="1", right="2"),
                        ComparisonDimension(name="y", left="3", right="4"),
                    ],
                    visual_summary=VisualSummary(left_keyword="a", right_keyword="b", center_conclusion="c"),
                ),
                teaching_content=self._base_content(),
            )

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            ComparisonPayload(
                left_entity=ComparisonEntity(name="A", core_label="a", short_desc="a"),
                right_entity=ComparisonEntity(name="B", core_label="b", short_desc="b"),
                dimensions=[
                    ComparisonDimension(name="x", left="1", right="2"),
                    ComparisonDimension(name="y", left="3", right="4"),
                ],
                visual_summary=VisualSummary(left_keyword="a", right_keyword="b", center_conclusion="c"),
                bogus_field="nope",
            )

    def test_empty_title_rejected(self):
        with pytest.raises(ValidationError):
            TeachingDiagram(
                graph_type="summary",
                title="",
                teaching_goal="test",
                visual_content=SummaryPayload(
                    cards=[SummaryCard(title="A", short_desc="a"), SummaryCard(title="B", short_desc="b")]
                ),
                teaching_content=self._base_content(),
            )
