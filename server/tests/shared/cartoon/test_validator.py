"""Unit tests for HyperFrames HTML validator.

Tests cover _CompositionParser HTML parser, audit_hyperframes_html
static validation function, and CartoonCliValidator async validator.

User instruction: "@app/shared/cartoon/ 按照google的python代码规范来完善代码，补充测试和修复类型注解"
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.shared.cartoon.validator import (
    _CompositionParser,
    audit_hyperframes_html,
    CartoonCliValidator,
)
from app.shared.cartoon.schemas import StaticAudit


class TestCompositionParser:
    """Tests for _CompositionParser HTML parser."""

    def test_parses_composition_id(self) -> None:
        """Test that data-composition-id is extracted from root element."""
        html = '<div data-composition-id="my-video" data-start="0"></div>'
        parser = _CompositionParser()
        parser.feed(html)
        assert len(parser.compositions) == 1
        assert parser.compositions[0]["data-composition-id"] == "my-video"

    def test_detects_clips(self) -> None:
        """Test that elements with class 'clip' are detected."""
        html = """
        <div class="clip" id="scene-0" data-start="0" data-duration="5"></div>
        <div class="clip" id="scene-1" data-start="5" data-duration="3"></div>
        """
        parser = _CompositionParser()
        parser.feed(html)
        assert len(parser.clips) == 2

    def test_detects_audio_clips(self) -> None:
        """Test that audio elements with data-start are treated as clips."""
        html = '<audio id="audio-0" data-start="0" data-duration="5" src="audio.mp3"></audio>'
        parser = _CompositionParser()
        parser.feed(html)
        assert len(parser.clips) == 1
        assert parser.clips[0][0] == "audio"

    def test_collects_ids(self) -> None:
        """Test that all id attributes are collected for duplicate detection."""
        html = """
        <div id="root">
            <div id="scene-0"></div>
            <div id="scene-1"></div>
        </div>
        """
        parser = _CompositionParser()
        parser.feed(html)
        assert set(parser.ids) == {"root", "scene-0", "scene-1"}

    def test_detects_audio_inside_clip(self) -> None:
        """Test that nested audio inside clip is flagged."""
        html = """
        <div class="clip" id="scene-0" data-start="0" data-duration="5">
            <audio data-start="0" data-duration="5" src="audio.mp3"></audio>
        </div>
        """
        parser = _CompositionParser()
        parser.feed(html)
        assert parser.audio_inside_clip is True


class TestAuditHyperframesHtml:
    """Tests for audit_hyperframes_html static validation."""

    def test_valid_minimal_html(self) -> None:
        """Test validation of minimal valid HyperFrames HTML."""
        html = """
        <!DOCTYPE html>
        <html>
        <body>
        <div data-composition-id="test" data-start="0" data-duration="10"
             data-width="1920" data-height="1080">
          <div class="scene clip" id="scene-0" data-start="0" data-duration="5"
               data-track-index="0"></div>
        </div>
        <script>
        const tl = gsap.timeline({ paused: true });
        window.__timelines = window.__timelines || {};
        window.__timelines["test"] = tl;
        </script>
        </body>
        </html>
        """
        problems = audit_hyperframes_html(html)
        assert problems == []

    def test_missing_composition_id(self) -> None:
        """Test that missing data-composition-id root is detected."""
        html = '<div data-start="0"></div>'
        problems = audit_hyperframes_html(html)
        assert any("data-composition-id" in p for p in problems)

    def test_missing_root_attributes(self) -> None:
        """Test that missing required root attributes are detected."""
        html = '<div data-composition-id="test"></div>'
        problems = audit_hyperframes_html(html)
        assert any("data-start" in p for p in problems)
        assert any("data-duration" in p for p in problems)

    def test_duplicate_ids(self) -> None:
        """Test that duplicate id attributes are detected."""
        html = """
        <div data-composition-id="test" data-start="0" data-duration="10"
             data-width="1920" data-height="1080">
          <div id="scene" class="clip" data-start="0" data-duration="5" data-track-index="0"></div>
          <div id="scene" class="clip" data-start="5" data-duration="3" data-track-index="0"></div>
        </div>
        """
        problems = audit_hyperframes_html(html)
        assert any("重复的 id" in p for p in problems)

    def test_invalid_data_start(self) -> None:
        """Test that non-numeric data-start values are detected."""
        html = """
        <div data-composition-id="test" data-start="0" data-duration="10"
             data-width="1920" data-height="1080">
          <div id="scene-0" class="clip" data-start="invalid" data-duration="5"
               data-track-index="0"></div>
        </div>
        """
        problems = audit_hyperframes_html(html)
        assert any("data-start 无效" in p for p in problems)

    def test_overlapping_clips(self) -> None:
        """Test that time overlaps on same track are detected."""
        html = """
        <div data-composition-id="test" data-start="0" data-duration="10"
             data-width="1920" data-height="1080">
          <div id="scene-0" class="clip" data-start="0" data-duration="5" data-track-index="0"></div>
          <div id="scene-1" class="clip" data-start="4" data-duration="3" data-track-index="0"></div>
        </div>
        """
        problems = audit_hyperframes_html(html)
        assert any("时间重叠" in p for p in problems)

    def test_audio_inside_clip_detected(self) -> None:
        """Test that audio nested inside clip element is detected."""
        html = """
        <div data-composition-id="test" data-start="0" data-duration="10"
             data-width="1920" data-height="1080">
          <div class="clip" id="scene-0" data-start="0" data-duration="5" data-track-index="0">
            <audio data-start="0" data-duration="5" src="audio.mp3"></audio>
          </div>
        </div>
        """
        problems = audit_hyperframes_html(html)
        assert any("audio 必须是 composition 的直接 clip" in p for p in problems)

    def test_missing_paused_timeline(self) -> None:
        """Test that missing paused: true in GSAP timeline is detected."""
        html = """
        <div data-composition-id="test" data-start="0" data-duration="10"
             data-width="1920" data-height="1080">
          <div class="clip" id="scene-0" data-start="0" data-duration="5" data-track-index="0"></div>
        </div>
        <script>
        const tl = gsap.timeline();
        window.__timelines = window.__timelines || {};
        window.__timelines["test"] = tl;
        </script>
        """
        problems = audit_hyperframes_html(html)
        assert any("paused: true" in p for p in problems)

    def test_banned_math_random(self) -> None:
        """Test that Math.random usage is banned for reproducibility."""
        html = """
        <div data-composition-id="test" data-start="0" data-duration="10"
             data-width="1920" data-height="1080">
          <div class="clip" id="scene-0" data-start="0" data-duration="5" data-track-index="0"></div>
        </div>
        <script>
        const tl = gsap.timeline({ paused: true });
        const x = Math.random();
        window.__timelines = window.__timelines || {};
        window.__timelines["test"] = tl;
        </script>
        """
        problems = audit_hyperframes_html(html)
        assert any("Math.random" in p for p in problems)

    def test_banned_date_now(self) -> None:
        """Test that Date.now usage is banned for reproducibility."""
        html = """
        <div data-composition-id="test" data-start="0" data-duration="10"
             data-width="1920" data-height="1080">
          <div class="clip" id="scene-0" data-start="0" data-duration="5" data-track-index="0"></div>
        </div>
        <script>
        const tl = gsap.timeline({ paused: true });
        const now = Date.now();
        window.__timelines = window.__timelines || {};
        window.__timelines["test"] = tl;
        </script>
        """
        problems = audit_hyperframes_html(html)
        assert any("Date.now" in p for p in problems)

    def test_timeline_not_registered(self) -> None:
        """Test that timeline not registered to window.__timelines is detected."""
        html = """
        <div data-composition-id="test" data-start="0" data-duration="10"
             data-width="1920" data-height="1080">
          <div class="clip" id="scene-0" data-start="0" data-duration="5" data-track-index="0"></div>
        </div>
        <script>
        const tl = gsap.timeline({ paused: true });
        </script>
        """
        problems = audit_hyperframes_html(html)
        assert any("时间线未注册" in p for p in problems)


class TestCartoonCliValidator:
    """Tests for CartoonCliValidator async validation."""

    @pytest.mark.asyncio
    async def test_validates_missing_html_file(self, tmp_path: Path) -> None:
        """Test that missing HTML file returns failed audit."""
        validator = CartoonCliValidator()
        result = await validator.validate(tmp_path)

        assert isinstance(result, StaticAudit)
        assert result.passed is False
        assert any("not found" in p for p in result.problems)

    @pytest.mark.asyncio
    async def test_validates_html_with_static_problems(self, tmp_path: Path) -> None:
        """Test that static problems are caught before CLI validation."""
        html_file = tmp_path / "index.html"
        html_file.write_text("<html><body>Invalid composition</body></html>")

        validator = CartoonCliValidator()
        result = await validator.validate(tmp_path)

        assert result.passed is False
        assert len(result.problems) > 0

    @pytest.mark.asyncio
    async def test_counts_scenes_from_html(self, tmp_path: Path) -> None:
        """Test that scene count is extracted from HTML."""
        html = """
        <div data-composition-id="test" data-start="0" data-duration="10"
             data-width="1920" data-height="1080">
          <div class="scene clip" id="scene-0" data-start="0" data-duration="3" data-track-index="0"></div>
          <div class="scene clip" id="scene-1" data-start="3" data-duration="4" data-track-index="0"></div>
          <div class="scene clip" id="scene-2" data-start="7" data-duration="3" data-track-index="0"></div>
        </div>
        """
        html_file = tmp_path / "index.html"
        html_file.write_text(html)

        validator = CartoonCliValidator()
        result = await validator.validate(tmp_path)

        assert result.scene_count == 3