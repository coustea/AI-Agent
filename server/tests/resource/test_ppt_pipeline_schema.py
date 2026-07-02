"""Comprehensive schema tests for the PPT pipeline contract models."""

import pytest
from pydantic import ValidationError

from app.resource.agents.ppt_pipeline.schemas import (
    DeckBrief,
    SourcePack,
    SourceArtifact,
    StyleCandidate,
    StyleDecision,
    StaticAudit,
    VisualAudit,
    VisualQAProblem,
)


# ---------------------------------------------------------------------------
# DeckBrief
# ---------------------------------------------------------------------------

class TestDeckBrief:
    VALID_DATA = {
        "purpose": "演示计算机网络基础",
        "audience": "零基础大学生",
        "density": "speaker_led",
        "target_slide_count": 8,
        "narrative": "从物理层逐步到应用层，层层剖析",
        "required_points": ["OSI七层模型", "TCP/IP协议族"],
        "language": "en-US",
        "mood": "tech, professional",
    }

    def test_accepts_valid_data_with_all_fields(self):
        brief = DeckBrief.model_validate(self.VALID_DATA)
        assert brief.purpose == "演示计算机网络基础"
        assert brief.audience == "零基础大学生"
        assert brief.density == "speaker_led"
        assert brief.target_slide_count == 8
        assert brief.narrative == "从物理层逐步到应用层，层层剖析"
        assert brief.required_points == ["OSI七层模型", "TCP/IP协议族"]
        assert brief.language == "en-US"
        assert brief.mood == "tech, professional"

    def test_rejects_extra_fields(self):
        data = {**self.VALID_DATA, "surprise": True}
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            DeckBrief.model_validate(data)

    def test_rejects_empty_purpose(self):
        data = {**self.VALID_DATA, "purpose": ""}
        with pytest.raises(ValidationError):
            DeckBrief.model_validate(data)

    def test_rejects_empty_audience(self):
        data = {**self.VALID_DATA, "audience": ""}
        with pytest.raises(ValidationError):
            DeckBrief.model_validate(data)

    def test_rejects_empty_narrative(self):
        data = {**self.VALID_DATA, "narrative": ""}
        with pytest.raises(ValidationError):
            DeckBrief.model_validate(data)

    def test_rejects_empty_mood(self):
        data = {**self.VALID_DATA, "mood": ""}
        with pytest.raises(ValidationError):
            DeckBrief.model_validate(data)

    def test_rejects_target_slide_count_below_3(self):
        data = {**self.VALID_DATA, "target_slide_count": 2}
        with pytest.raises(ValidationError):
            DeckBrief.model_validate(data)

    def test_rejects_target_slide_count_above_40(self):
        data = {**self.VALID_DATA, "target_slide_count": 41}
        with pytest.raises(ValidationError):
            DeckBrief.model_validate(data)

    def test_accepts_target_slide_count_at_boundary_3(self):
        data = {**self.VALID_DATA, "target_slide_count": 3}
        brief = DeckBrief.model_validate(data)
        assert brief.target_slide_count == 3

    def test_accepts_target_slide_count_at_boundary_16(self):
        data = {**self.VALID_DATA, "target_slide_count": 16}
        brief = DeckBrief.model_validate(data)
        assert brief.target_slide_count == 16

    def test_defaults_language_to_zh_cn(self):
        data = {k: v for k, v in self.VALID_DATA.items() if k != "language"}
        brief = DeckBrief.model_validate(data)
        assert brief.language == "zh-CN"

    def test_rejects_invalid_density_values(self):
        data = {**self.VALID_DATA, "density": "invalid_density"}
        with pytest.raises(ValidationError):
            DeckBrief.model_validate(data)

    def test_accepts_reading_first_density(self):
        data = {**self.VALID_DATA, "density": "reading_first"}
        brief = DeckBrief.model_validate(data)
        assert brief.density == "reading_first"


# ---------------------------------------------------------------------------
# SourcePack
# ---------------------------------------------------------------------------

class TestSourcePack:
    VALID_DATA = {
        "learning_need": "复习 TCP 三次握手",
        "learning_scenario": "exam_prep",
        "profile": {"level": "beginner"},
        "teaching_plan": {"chapters": ["网络基础"]},
        "source_type": "resource",
        "artifacts": [
            {
                "agent_id": "content",
                "title": "TCP 协议详解",
                "summary": "涵盖三次握手和四次挥手",
                "materials": ["手写笔记", "课堂PPT"],
            }
        ],
    }

    def test_accepts_valid_data_with_all_fields(self):
        pack = SourcePack.model_validate(self.VALID_DATA)
        assert pack.learning_need == "复习 TCP 三次握手"
        assert pack.source_type == "resource"
        assert len(pack.artifacts) == 1
        assert pack.artifacts[0].agent_id == "content"

    def test_rejects_extra_fields(self):
        data = {**self.VALID_DATA, "unexpected": True}
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            SourcePack.model_validate(data)

    def test_accepts_profile_as_dict(self):
        data = {**self.VALID_DATA, "profile": {"level": "advanced", "goal": "考研"}}
        pack = SourcePack.model_validate(data)
        assert isinstance(pack.profile, dict)

    def test_accepts_profile_as_str(self):
        data = {**self.VALID_DATA, "profile": "大三计算机专业学生"}
        pack = SourcePack.model_validate(data)
        assert isinstance(pack.profile, str)

    def test_accepts_teaching_plan_as_dict(self):
        data = {**self.VALID_DATA, "teaching_plan": {"chapters": ["网络基础"]}}
        pack = SourcePack.model_validate(data)
        assert isinstance(pack.teaching_plan, dict)

    def test_accepts_teaching_plan_as_none(self):
        data = {**self.VALID_DATA, "teaching_plan": None}
        pack = SourcePack.model_validate(data)
        assert pack.teaching_plan is None

    def test_requires_source_type_resource_or_node(self):
        data = {**self.VALID_DATA, "source_type": "resource"}
        assert SourcePack.model_validate(data).source_type == "resource"
        data = {**self.VALID_DATA, "source_type": "node"}
        assert SourcePack.model_validate(data).source_type == "node"

    def test_rejects_invalid_source_type(self):
        data = {**self.VALID_DATA, "source_type": "lecture"}
        with pytest.raises(ValidationError):
            SourcePack.model_validate(data)

    def test_rejects_empty_learning_need(self):
        data = {**self.VALID_DATA, "learning_need": ""}
        with pytest.raises(ValidationError):
            SourcePack.model_validate(data)

    def test_rejects_empty_learning_scenario(self):
        data = {**self.VALID_DATA, "learning_scenario": ""}
        with pytest.raises(ValidationError):
            SourcePack.model_validate(data)


# ---------------------------------------------------------------------------
# StyleDecision
# ---------------------------------------------------------------------------

class TestStyleDecision:
    CANDIDATES = [
        {
            "name": "Neon Cyber",
            "source": "preset",
            "rationale": "适合科技类主题",
            "design_recipe": "--bg-primary: #0a0f1c; --accent: #00ffcc;",
            "font_urls": ["https://example.com/font.css"],
        },
        {
            "name": "Bold Dark",
            "source": "bold_template",
            "rationale": "高对比度适合代码演示",
            "design_recipe": "--bg-primary: #1a1a2e; --accent: #e94560;",
            "font_urls": [],
        },
        {
            "name": "Custom Slate",
            "source": "custom",
            "rationale": "沉稳色调适合学术讲解",
            "design_recipe": "--bg-primary: #2d3436; --accent: #74b9ff;",
            "font_urls": [],
        },
    ]

    def _make_data(self, **overrides):
        base = {
            "candidates": self.CANDIDATES,
            "selected_index": 0,
            "density": "speaker_led",
        }
        base.update(overrides)
        return base

    def test_accepts_valid_3_candidate_data(self):
        decision = StyleDecision.model_validate(self._make_data())
        assert len(decision.candidates) == 3
        sources = [c.source for c in decision.candidates]
        assert sources == ["preset", "bold_template", "custom"]

    def test_rejects_1_candidate(self):
        data = self._make_data(candidates=[self.CANDIDATES[0]])
        with pytest.raises(ValidationError):
            StyleDecision.model_validate(data)

    def test_rejects_2_candidates(self):
        data = self._make_data(candidates=self.CANDIDATES[:2])
        with pytest.raises(ValidationError):
            StyleDecision.model_validate(data)

    def test_rejects_4_candidates(self):
        extra = {
            "name": "Extra",
            "source": "preset",
            "rationale": "r",
            "design_recipe": "d",
        }
        data = self._make_data(candidates=self.CANDIDATES + [extra])
        with pytest.raises(ValidationError):
            StyleDecision.model_validate(data)

    def test_rejects_wrong_source_order(self):
        reordered = [self.CANDIDATES[1], self.CANDIDATES[0], self.CANDIDATES[2]]
        data = self._make_data(candidates=reordered)
        with pytest.raises(ValidationError):
            StyleDecision.model_validate(data)

    def test_selected_index_must_be_0_to_2(self):
        for idx in (0, 1, 2):
            decision = StyleDecision.model_validate(self._make_data(selected_index=idx))
            assert decision.selected_index == idx

    def test_rejects_selected_index_below_0(self):
        with pytest.raises(ValidationError):
            StyleDecision.model_validate(self._make_data(selected_index=-1))

    def test_rejects_selected_index_above_2(self):
        with pytest.raises(ValidationError):
            StyleDecision.model_validate(self._make_data(selected_index=3))

    def test_selected_property_returns_correct_candidate(self):
        for idx in (0, 1, 2):
            decision = StyleDecision.model_validate(self._make_data(selected_index=idx))
            assert decision.selected.name == self.CANDIDATES[idx]["name"]

    def test_rejects_extra_fields(self):
        data = self._make_data(unexpected=True)
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            StyleDecision.model_validate(data)


# ---------------------------------------------------------------------------
# StaticAudit
# ---------------------------------------------------------------------------

class TestStaticAudit:
    def test_accepts_valid_data(self):
        audit = StaticAudit.model_validate(
            {"passed": True, "problems": ["slide 3 too long"], "slide_count": 8}
        )
        assert audit.passed is True
        assert audit.problems == ["slide 3 too long"]
        assert audit.slide_count == 8

    def test_rejects_extra_fields(self):
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            StaticAudit.model_validate(
                {"passed": True, "slide_count": 5, "extra": True}
            )

    def test_default_problems_is_empty_list(self):
        audit = StaticAudit.model_validate({"passed": True, "slide_count": 5})
        assert audit.problems == []

    def test_slide_count_must_be_non_negative(self):
        with pytest.raises(ValidationError):
            StaticAudit.model_validate({"passed": True, "slide_count": -1})

    def test_slide_count_accepts_zero(self):
        audit = StaticAudit.model_validate({"passed": False, "slide_count": 0})
        assert audit.slide_count == 0


# ---------------------------------------------------------------------------
# VisualQAProblem
# ---------------------------------------------------------------------------

class TestVisualQAProblem:
    VALID_DATA = {
        "slide_index": 3,
        "viewport": "desktop",
        "problem_type": "overflow",
        "element_summary": "div.slide-content-area > p",
        "severity": "critical",
    }

    def test_accepts_valid_data(self):
        problem = VisualQAProblem.model_validate(self.VALID_DATA)
        assert problem.slide_index == 3
        assert problem.viewport == "desktop"
        assert problem.problem_type == "overflow"
        assert problem.severity == "critical"

    def test_rejects_extra_fields(self):
        data = {**self.VALID_DATA, "extra": True}
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            VisualQAProblem.model_validate(data)

    def test_severity_must_be_warning_or_critical(self):
        for severity in ("warning", "critical"):
            data = {**self.VALID_DATA, "severity": severity}
            problem = VisualQAProblem.model_validate(data)
            assert problem.severity == severity

    def test_rejects_invalid_severity(self):
        data = {**self.VALID_DATA, "severity": "low"}
        with pytest.raises(ValidationError):
            VisualQAProblem.model_validate(data)

    @pytest.mark.parametrize(
        "problem_type",
        [
            "overflow",
            "overlap",
            "empty",
            "script_error",
            "stage_geometry",
            "font_size",
            "navigation",
            "other",
        ],
    )
    def test_accepts_all_8_problem_types(self, problem_type):
        data = {**self.VALID_DATA, "problem_type": problem_type}
        problem = VisualQAProblem.model_validate(data)
        assert problem.problem_type == problem_type

    def test_rejects_invalid_problem_type(self):
        data = {**self.VALID_DATA, "problem_type": "typo"}
        with pytest.raises(ValidationError):
            VisualQAProblem.model_validate(data)

    def test_slide_index_must_be_non_negative(self):
        data = {**self.VALID_DATA, "slide_index": -1}
        with pytest.raises(ValidationError):
            VisualQAProblem.model_validate(data)

    def test_slide_index_accepts_zero(self):
        data = {**self.VALID_DATA, "slide_index": 0}
        problem = VisualQAProblem.model_validate(data)
        assert problem.slide_index == 0


# ---------------------------------------------------------------------------
# VisualAudit
# ---------------------------------------------------------------------------

class TestVisualAudit:
    def test_accepts_valid_data(self):
        audit = VisualAudit.model_validate(
            {
                "passed": False,
                "problems": [
                    {
                        "slide_index": 2,
                        "viewport": "desktop",
                        "problem_type": "overlap",
                        "element_summary": "h1 overlap with text",
                        "severity": "warning",
                    }
                ],
            }
        )
        assert audit.passed is False
        assert len(audit.problems) == 1
        assert audit.problems[0].problem_type == "overlap"

    def test_rejects_extra_fields(self):
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            VisualAudit.model_validate({"passed": True, "extra": True})

    def test_default_problems_is_empty_list(self):
        audit = VisualAudit.model_validate({"passed": True})
        assert audit.problems == []
