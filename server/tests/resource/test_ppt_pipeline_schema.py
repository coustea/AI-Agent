import pytest
from pydantic import ValidationError

from app.resource.agents.ppt_pipeline.schemas import (
    DeckBrief,
    StyleDecision,
    VisualAudit,
    VisualQAProblem,
)


def test_deck_brief_validation():
    # Test valid DeckBrief validation
    brief_data = {
        "purpose": "演示计算机网络基础",
        "audience": "零基础大学生",
        "density": "speaker_led",
        "target_slide_count": 8,
        "narrative": "从物理层逐步到应用层，层层剖析",
        "required_points": ["OSI七层模型", "TCP/IP协议族", "物理层传输"],
        "mood": "tech, professional",
    }
    brief = DeckBrief.model_validate(brief_data)
    assert brief.purpose == "演示计算机网络基础"
    assert brief.language == "zh-CN"  # Default value check
    assert brief.density == "speaker_led"

    # Test language override
    brief_data["language"] = "en-US"
    brief = DeckBrief.model_validate(brief_data)
    assert brief.language == "en-US"

    # Test density validation failure
    brief_data["density"] = "invalid_density"
    with pytest.raises(ValidationError):
        DeckBrief.model_validate(brief_data)


def test_style_decision_validation():
    # Test valid StyleDecision validation
    style_data = {
        "name": "Neon Cyber",
        "source": "preset",
        "rationale": "适合科技类主题，突出赛博霓虹感",
        "design_recipe": {
            "bg_primary": "#0a0f1c",
            "accent": "#00ffcc",
            "spacing": "large",
        },
        "font_urls": ["https://api.fontshare.com/v2/css?f[]=clash-display@500"],
        "density": "speaker_led",
    }
    decision = StyleDecision.model_validate(style_data)
    assert decision.name == "Neon Cyber"
    assert decision.source == "preset"
    assert decision.design_recipe["accent"] == "#00ffcc"

    # Test source literal constraint
    style_data["source"] = "invalid_source"
    with pytest.raises(ValidationError):
        StyleDecision.model_validate(style_data)


def test_visual_qa_problem_validation():
    # Test valid VisualQAProblem validation
    problem_data = {
        "slide_index": 3,
        "problem_type": "overflow",
        "element_summary": "div.slide-content-area > p",
        "severity": "critical",
    }
    problem = VisualQAProblem.model_validate(problem_data)
    assert problem.slide_index == 3
    assert problem.severity == "critical"

    # Test severity literal constraint
    problem_data["severity"] = "low"
    with pytest.raises(ValidationError):
        VisualQAProblem.model_validate(problem_data)


def test_visual_audit_validation():
    # Test valid VisualAudit validation
    audit_data = {
        "passed": False,
        "problems": [
            {
                "slide_index": 2,
                "problem_type": "overlap",
                "element_summary": "h1 overlap with text",
                "severity": "warning",
            }
        ],
    }
    audit = VisualAudit.model_validate(audit_data)
    assert not audit.passed
    assert len(audit.problems) == 1
    assert audit.problems[0].slide_index == 2
    assert audit.problems[0].severity == "warning"

    # Test defaults
    empty_audit = VisualAudit.model_validate({"passed": True})
    assert empty_audit.passed
    assert empty_audit.problems == []
