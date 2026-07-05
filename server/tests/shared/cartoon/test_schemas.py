"""Unit tests for cartoon schemas.

Tests cover all Pydantic models in app.shared.cartoon.schemas:
- CaptionWord: word-level timing for TTS captions
- SourceArtifact: upstream agent output for video generation
- CartoonVideoRequest: top-level request schema
- SceneBrief: individual scene in the timeline
- VideoBrief: planner output with scene timeline
- StyleCandidate: visual style option
- StyleDecision: selected style with rationale
- StaticAudit: validator output

User instruction: "@app/shared/cartoon/ 按照google的python代码规范来完善代码，补充测试和修复类型注解"
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.shared.cartoon.schemas import (
    CaptionWord,
    CartoonVideoRequest,
    SceneBrief,
    SourceArtifact,
    StaticAudit,
    StyleCandidate,
    StyleDecision,
    VideoBrief,
)


class TestCaptionWord:
    """Tests for CaptionWord schema."""

    def test_valid_caption_word(self) -> None:
        """Test creating a valid CaptionWord."""
        word = CaptionWord(text="你好", start_ms=0, end_ms=500)
        assert word.text == "你好"
        assert word.start_ms == 0
        assert word.end_ms == 500

    def test_caption_word_rejects_empty_text(self) -> None:
        """Test that empty text is rejected."""
        with pytest.raises(ValidationError):
            CaptionWord(text="", start_ms=0, end_ms=500)

    def test_caption_word_rejects_negative_start(self) -> None:
        """Test that negative start_ms is rejected."""
        with pytest.raises(ValidationError):
            CaptionWord(text="test", start_ms=-1, end_ms=500)

    def test_caption_word_rejects_zero_end(self) -> None:
        """Test that zero end_ms is rejected."""
        with pytest.raises(ValidationError):
            CaptionWord(text="test", start_ms=0, end_ms=0)


class TestSourceArtifact:
    """Tests for SourceArtifact schema."""

    def test_valid_source_artifact(self) -> None:
        """Test creating a valid SourceArtifact."""
        artifact = SourceArtifact(
            agent_id="content",
            title="Test Title",
            summary="Test summary",
            materials=["point1", "point2"],
        )
        assert artifact.agent_id == "content"
        assert artifact.title == "Test Title"
        assert len(artifact.materials) == 2

    def test_source_artifact_defaults_empty_materials(self) -> None:
        """Test that materials defaults to empty list."""
        artifact = SourceArtifact(
            agent_id="quiz",
            title="Quiz",
            summary="Quiz summary",
        )
        assert artifact.materials == []

    def test_source_artifact_rejects_empty_agent_id(self) -> None:
        """Test that empty agent_id is rejected."""
        with pytest.raises(ValidationError):
            SourceArtifact(agent_id="", title="Test", summary="Summary")

    def test_source_artifact_limits_materials_to_12(self) -> None:
        """Test that materials is limited to 12 items."""
        materials = [f"item_{i}" for i in range(15)]
        with pytest.raises(ValidationError):
            SourceArtifact(
                agent_id="content",
                title="Test",
                summary="Summary",
                materials=materials,
            )


class TestCartoonVideoRequest:
    """Tests for CartoonVideoRequest schema."""

    def test_valid_request(self, tmp_path: object) -> None:
        """Test creating a valid CartoonVideoRequest."""
        request = CartoonVideoRequest(
            learning_need="理解 TCP 三次握手",
            profile={"level": "beginner"},
            video_length_seconds=60,
            voice="zh-CN-XiaoxiaoNeural",
            output_dir=tmp_path,
        )
        assert request.learning_need == "理解 TCP 三次握手"
        assert request.video_length_seconds == 60

    def test_request_defaults(self, tmp_path: object) -> None:
        """Test default values for CartoonVideoRequest."""
        request = CartoonVideoRequest(
            learning_need="Test",
            profile={},
            output_dir=tmp_path,
        )
        assert request.video_length_seconds == 30
        assert request.voice == "zh-CN-XiaoxiaoNeural"
        assert request.artifacts == []

    def test_request_rejects_empty_learning_need(self, tmp_path: object) -> None:
        """Test that empty learning_need is rejected."""
        with pytest.raises(ValidationError):
            CartoonVideoRequest(
                learning_need="",
                profile={},
                output_dir=tmp_path,
            )

    def test_request_validates_video_length_bounds(self, tmp_path: object) -> None:
        """Test that video_length_seconds must be within bounds [10, 180]."""
        with pytest.raises(ValidationError):
            CartoonVideoRequest(
                learning_need="Test",
                profile={},
                video_length_seconds=5,  # Below minimum of 10
                output_dir=tmp_path,
            )

        with pytest.raises(ValidationError):
            CartoonVideoRequest(
                learning_need="Test",
                profile={},
                video_length_seconds=200,  # Above maximum of 180
                output_dir=tmp_path,
            )


class TestSceneBrief:
    """Tests for SceneBrief schema."""

    def test_valid_scene_brief(self) -> None:
        """Test creating a valid SceneBrief."""
        scene = SceneBrief(
            name="intro",
            narration="欢迎来到本节课",
            start_time=0.0,
            duration=5.0,
        )
        assert scene.name == "intro"
        assert scene.duration == 5.0

    def test_scene_brief_defaults(self) -> None:
        """Test default values for SceneBrief."""
        scene = SceneBrief(name="test", narration="Test narration")
        assert scene.start_time == 0.0
        assert scene.duration == 1.0
        assert scene.visuals == []
        assert scene.animation_steps == []

    def test_scene_brief_rejects_zero_duration(self) -> None:
        """Test that zero duration is rejected (must be gt=0)."""
        with pytest.raises(ValidationError):
            SceneBrief(name="test", narration="Test", duration=0.0)


class TestVideoBrief:
    """Tests for VideoBrief schema."""

    def test_valid_video_brief(self) -> None:
        """Test creating a valid VideoBrief."""
        scene = SceneBrief(name="intro", narration="Welcome")
        brief = VideoBrief(
            title="TCP 三次握手",
            subject="计算机网络",
            scenes=[scene],
            mood="educational",
        )
        assert brief.title == "TCP 三次握手"
        assert len(brief.scenes) == 1

    def test_video_brief_requires_at_least_one_scene(self) -> None:
        """Test that at least one scene is required (min_length=1)."""
        with pytest.raises(ValidationError):
            VideoBrief(
                title="Test",
                subject="Test",
                scenes=[],
                mood="test",
            )


class TestStyleCandidate:
    """Tests for StyleCandidate schema."""

    def test_valid_style_candidate(self) -> None:
        """Test creating a valid StyleCandidate."""
        candidate = StyleCandidate(
            name="Chalkboard",
            source="preset",
            rationale="Educational style",
            design_recipe="Use Comic Neue font",
        )
        assert candidate.name == "Chalkboard"
        assert candidate.source == "preset"


class TestStyleDecision:
    """Tests for StyleDecision schema."""

    def test_valid_style_decision(self) -> None:
        """Test creating a valid StyleDecision."""
        candidate1 = StyleCandidate(
            name="Style A",
            source="preset",
            rationale="Good for education",
            design_recipe="Font: Arial",
        )
        candidate2 = StyleCandidate(
            name="Style B",
            source="preset",
            rationale="Good for tech",
            design_recipe="Font: Roboto",
        )
        decision = StyleDecision(
            candidates=[candidate1, candidate2],
            selected_index=0,
        )
        assert decision.selected.name == "Style A"

    def test_style_decision_selected_property(self) -> None:
        """Test the selected property returns the correct candidate."""
        candidates = [
            StyleCandidate(
                name=f"Style {i}",
                source="preset",
                rationale=f"Rationale {i}",
                design_recipe=f"Recipe {i}",
            )
            for i in range(3)
        ]
        decision = StyleDecision(candidates=candidates, selected_index=1)
        assert decision.selected.name == "Style 1"

    def test_style_decision_rejects_invalid_selected_index(self) -> None:
        """Test that selected_index must reference an existing candidate."""
        candidate = StyleCandidate(
            name="Style",
            source="preset",
            rationale="Test",
            design_recipe="Test",
        )
        with pytest.raises(ValidationError):
            StyleDecision(candidates=[candidate], selected_index=5)


class TestStaticAudit:
    """Tests for StaticAudit schema."""

    def test_passed_audit(self) -> None:
        """Test creating a passed audit."""
        audit = StaticAudit(passed=True, scene_count=3)
        assert audit.passed is True
        assert audit.problems == []

    def test_failed_audit_with_problems(self) -> None:
        """Test creating a failed audit with problems."""
        audit = StaticAudit(
            passed=False,
            problems=["Missing data-start", "Invalid duration"],
            scene_count=2,
        )
        assert audit.passed is False
        assert len(audit.problems) == 2