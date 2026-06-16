from app.resource.agents.common import (
    build_basic_handoff,
    first_content_excerpt,
    outline_coverage_summary,
    outline_ids_from_plan,
    select_outline_ids_by_keywords,
)
from app.resource.schemas import DownstreamContext, TeachingOutlineItem, TeachingPlan


def _plan() -> TeachingPlan:
    return TeachingPlan(
        topic="TCP",
        outline=[
            TeachingOutlineItem(id="o1", title="连接建立", goal="理解三次握手", key_points=["SYN", "ACK"]),
            TeachingOutlineItem(id="o2", title="可靠传输", goal="理解重传", key_points=["超时重传", "滑动窗口"]),
            TeachingOutlineItem(id="o3", title="代码实践", goal="用代码观察 TCP", key_points=["socket", "抓包"]),
        ],
    )


def test_build_basic_handoff_does_not_claim_all_outline_ids_by_default():
    handoff = build_basic_handoff(
        source_agent="code",
        title="TCP 代码示例",
        summary="使用 socket 演示连接建立",
        teaching_plan=_plan(),
        material_type="code",
    )

    assert handoff.covered_outline_ids == ["o1"]
    assert handoff.materials[0].outline_id == "o1"


def test_build_basic_handoff_filters_unknown_outline_ids():
    handoff = build_basic_handoff(
        source_agent="content",
        title="TCP 内容",
        summary="讲解 TCP",
        teaching_plan=_plan(),
        material_type="explanation",
        covered_outline_ids=["o1", "missing", "o2"],
        material_outline_id="missing",
    )

    assert handoff.covered_outline_ids == ["o1", "o2"]
    assert handoff.materials[0].outline_id == "o1"


def test_select_outline_ids_by_keywords_prefers_matching_outline():
    ids = select_outline_ids_by_keywords(_plan(), ["代码", "socket"])

    assert ids == ["o3"]


def test_outline_coverage_summary_reports_missing_ids():
    plan = _plan()
    handoffs = {
        "content": DownstreamContext(source_agent="content", covered_outline_ids=["o1", "o2"]),
        "code": DownstreamContext(source_agent="code", covered_outline_ids=["o3"]),
        "reading": DownstreamContext(source_agent="reading", covered_outline_ids=["bad"]),
    }

    summary = outline_coverage_summary(plan, handoffs)

    assert summary["teaching_plan_outline_ids"] == ["o1", "o2", "o3"]
    assert summary["covered_source_outline_ids"] == ["o1", "o2", "o3"]
    assert summary["missing_source_outline_ids"] == []
    assert outline_ids_from_plan(plan) == ["o1", "o2", "o3"]


def test_first_content_excerpt_extracts_first_non_heading_line():
    assert first_content_excerpt("# Title\n\nSome real content\nMore text") == "Some real content"
    assert first_content_excerpt("") == ""
    assert first_content_excerpt("---\n- bullet\nReal line") == "bullet"
