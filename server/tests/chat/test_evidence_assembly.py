from __future__ import annotations

from app.chat.schemas import Evidence, EvidenceSet


def test_evidence_set_filters_answer_usable_items() -> None:
    evidence = EvidenceSet(items=[
        Evidence(evidence_type="attachment", summary="图片结论", usable_for_answer=True),
        Evidence(evidence_type="web_search", summary="低价值搜索", usable_for_answer=False),
    ])

    assert [item.summary for item in evidence.items if item.usable_for_answer] == ["图片结论"]


def test_attachment_and_search_evidence_share_the_same_interface() -> None:
    attachment = Evidence(evidence_type="attachment", summary="附件结论")
    search = Evidence(evidence_type="web_search", summary="搜索结论")

    assert set(attachment.model_dump().keys()) == set(search.model_dump().keys())
