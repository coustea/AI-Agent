from app.resource.agents.common import (
    build_basic_handoff,
    outline_coverage_summary,
    outline_ids_from_plan,
)
from app.resource.schemas import (
    DownstreamContext, TeachingOutlineItem, TeachingPlan, AgentAssignment,
)
import pytest


def _plan() -> TeachingPlan:
    return TeachingPlan(
        teaching_strategy="从基础到实践",
        outline=[
            TeachingOutlineItem(id="o1", title="连接建立", goal="理解三次握手", key_points=["SYN", "ACK"]),
            TeachingOutlineItem(id="o2", title="可靠传输", goal="理解重传", key_points=["超时重传", "滑动窗口"]),
            TeachingOutlineItem(id="o3", title="代码实践", goal="用代码观察 TCP", key_points=["socket", "抓包"]),
        ],
        agent_assignments=[
            AgentAssignment(agent_id="code", assigned_outline_ids=["o1", "o2", "o3"], focus_instruction="代码演示", style_constraint="简洁清晰"),
        ],
    )


def test_build_basic_handoff_requires_covered_outline_ids():
    """handoff 必须指定覆盖的大纲 ID。"""
    with pytest.raises(ValueError, match="must cover at least one outline ID"):
        build_basic_handoff(
            source_agent="code",
            title="TCP 代码示例",
            summary="使用 socket 演示连接建立",
            teaching_plan=_plan(),
        )


def test_build_basic_handoff_rejects_unknown_outline_ids():
    """handoff 不能引用不存在的大纲 ID。"""
    with pytest.raises(ValueError, match="references unknown outline IDs"):
        build_basic_handoff(
            source_agent="content",
            title="TCP 内容",
            summary="讲解 TCP",
            teaching_plan=_plan(),
            covered_outline_ids=["o1", "missing", "o2"],
        )


def test_build_basic_handoff_rejects_duplicate_outline_ids():
    """handoff 不能包含重复的大纲 ID。"""
    with pytest.raises(ValueError, match="contains duplicate outline IDs"):
        build_basic_handoff(
            source_agent="code",
            title="TCP 代码",
            summary="代码示例",
            teaching_plan=_plan(),
            covered_outline_ids=["o1", "o1", "o2"],
        )


def test_build_basic_handoff_succeeds_with_valid_outline_ids():
    """handoff 使用有效的大纲 ID 时应成功。"""
    handoff = build_basic_handoff(
        source_agent="code",
        title="TCP 代码示例",
        summary="使用 socket 演示连接建立",
        teaching_plan=_plan(),
        covered_outline_ids=["o1", "o2"],
    )

    assert handoff.source_agent == "code"
    assert handoff.covered_outline_ids == ["o1", "o2"]
    assert handoff.title == "TCP 代码示例"


def test_outline_coverage_summary_reports_coverage():
    """汇总大纲覆盖情况。"""
    plan = _plan()
    handoffs = {
        "content": DownstreamContext(source_agent="content", covered_outline_ids=["o1", "o2"]),
        "code": DownstreamContext(source_agent="code", covered_outline_ids=["o3"]),
    }

    summary = outline_coverage_summary(plan, handoffs)

    assert summary["teaching_plan_outline_ids"] == ["o1", "o2", "o3"]
    assert summary["covered_source_outline_ids"] == ["o1", "o2", "o3"]
    assert summary["missing_source_outline_ids"] == []
    assert outline_ids_from_plan(plan) == ["o1", "o2", "o3"]


def test_outline_coverage_summary_rejects_unknown_outline_id():
    """handoff 引用未知大纲 ID 时应报错。"""
    plan = _plan()
    handoffs = {
        "content": DownstreamContext(source_agent="content", covered_outline_ids=["o1", "o2"]),
        "code": DownstreamContext(source_agent="code", covered_outline_ids=["o3"]),
        "reading": DownstreamContext(source_agent="reading", covered_outline_ids=["bad"]),
    }

    with pytest.raises(ValueError, match="unknown outline ID"):
        outline_coverage_summary(plan, handoffs)
