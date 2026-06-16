"""Review envelope context control — base resources use handoffs, not full content."""

from app.resource.review import (
    build_pre_audit_envelope,
    build_ppt_audit_envelope,
    build_video_audit_envelope,
)
from app.resource.schemas import (
    AgentResult,
    AgentSelection,
    DownstreamContext,
    DownstreamMaterial,
    ReusableAssets,
    ResourceGenerationRequest,
)


def _handoff(source_agent: str, title: str = "", summary: str = "", outline_ids: list[str] | None = None) -> DownstreamContext:
    return DownstreamContext(
        source_agent=source_agent,
        title=title or f"{source_agent} result",
        one_sentence_summary=summary or f"{source_agent} summary",
        covered_outline_ids=outline_ids or [],
        materials=[DownstreamMaterial(outline_id="", type="explanation", summary=summary or f"{source_agent} summary")],
        reusable_assets=ReusableAssets(),
    )


def _result(agent_id: str, content: str = "full content here", handoff: DownstreamContext | None = None) -> AgentResult:
    return AgentResult(
        success=True,
        content=content,
        title=f"{agent_id} title",
        summary=f"{agent_id} summary",
        downstream_context=handoff or _handoff(agent_id),
    )


def _request() -> ResourceGenerationRequest:
    return ResourceGenerationRequest(
        learning_need="learn TCP",
        learning_scenario="self_study",
        selected_agents=[
            AgentSelection(agent_id="content", enabled=True),
            AgentSelection(agent_id="mindmap", enabled=True),
            AgentSelection(agent_id="quiz", enabled=True),
            AgentSelection(agent_id="code", enabled=True),
            AgentSelection(agent_id="reading", enabled=True),
            AgentSelection(agent_id="ppt", enabled=True),
            AgentSelection(agent_id="video", enabled=True),
        ],
    )


def test_pre_audit_uses_handoff_not_full_content():
    results = {
        "content": _result("content", "long content text" * 100),
        "reading": _result("reading", "reading full text" * 100),
        "mindmap": _result("mindmap"),
        "quiz": _result("quiz"),
        "code": _result("code"),
    }
    envelope, missing = build_pre_audit_envelope(
        request=_request(),
        results=results,
        profile={},
        teaching_plan=None,
    )
    assert not missing
    deep = envelope["deep_audit_resources"]
    assert len(deep) == 2
    for item in deep:
        assert "audit_content" not in item
        assert "source_content" not in item
        assert "covered_outline_ids" in item
    agents_in_deep = {item["agent_id"] for item in deep}
    assert agents_in_deep == {"content", "reading"}


def test_ppt_audit_uses_handoff_for_base_sources():
    results = {
        "content": _result("content", "long content text" * 100),
        "reading": _result("reading", "reading full text" * 100),
        "ppt": _result("ppt", '{"slides": [...]}'),
    }
    envelope, missing = build_ppt_audit_envelope(
        request=_request(),
        results=results,
        profile={},
        teaching_plan=None,
    )
    assert not missing
    approved = envelope["approved_sources"]
    for item in approved:
        assert "source_content" not in item
        assert "covered_outline_ids" in item
    ppt = envelope["ppt_resource"]
    assert ppt is not None
    assert "audit_content" in ppt


def test_video_audit_uses_handoff_for_base_sources():
    results = {
        "content": _result("content", "long content text" * 100),
        "reading": _result("reading", "reading full text" * 100),
        "video": _result("video", '{"scenes": [...]}'),
    }
    envelope, missing = build_video_audit_envelope(
        request=_request(),
        results=results,
        profile={},
        teaching_plan=None,
    )
    assert not missing
    approved = envelope["approved_sources"]
    for item in approved:
        assert "source_content" not in item
        assert "covered_outline_ids" in item
    video = envelope["video_resource"]
    assert video is not None
    assert "audit_content" in video


def test_envelope_includes_upstream_handoffs():
    results = {
        "content": _result("content", "content text", _handoff("content", outline_ids=["o1", "o2"])),
        "reading": _result("reading", "reading text", _handoff("reading", outline_ids=["o1"])),
    }
    envelope, _ = build_pre_audit_envelope(
        request=_request(),
        results=results,
        profile={},
        teaching_plan=None,
    )
    handoffs = envelope["upstream_handoffs"]
    assert "content" in handoffs
    assert handoffs["content"]["covered_outline_ids"] == ["o1", "o2"]
