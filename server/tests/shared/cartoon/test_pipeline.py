"""Unit tests for cartoon pipeline.

Tests cover CartoonPipeline orchestration, CartoonArtifact result,
and CartoonGenerationError exception handling.

User instruction: "@app/shared/cartoon/ 按照google的python代码规范来完善代码，补充测试和修复类型注解"
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.shared.cartoon.pipeline import (
    CartoonArtifact,
    CartoonGenerationError,
    CartoonPipeline,
)
from app.shared.cartoon.schemas import (
    CartoonVideoRequest,
    SceneBrief,
    StaticAudit,
    StyleCandidate,
    StyleDecision,
    VideoBrief,
)


@pytest.fixture
def mock_planner() -> MagicMock:
    """Create a mock VideoPlanner that returns a valid VideoBrief."""
    planner = MagicMock()
    planner.plan = AsyncMock(
        return_value=VideoBrief(
            title="Test Video",
            subject="Test Subject",
            scenes=[
                SceneBrief(name="intro", narration="Welcome"),
                SceneBrief(name="main", narration="Main content"),
            ],
            mood="educational",
        )
    )
    return planner


@pytest.fixture
def mock_director() -> MagicMock:
    """Create a mock VisualDirector that returns a valid StyleDecision."""
    director = MagicMock()
    director.direct = AsyncMock(
        return_value=StyleDecision(
            candidates=[
                StyleCandidate(
                    name="Style A",
                    source="preset",
                    rationale="Test",
                    design_recipe="Test",
                ),
                StyleCandidate(
                    name="Style B",
                    source="preset",
                    rationale="Test B",
                    design_recipe="Test B",
                ),
            ],
            selected_index=0,
        )
    )
    return director


@pytest.fixture
def mock_author() -> MagicMock:
    """Create a mock HTMLAuthor that returns valid HyperFrames HTML."""
    author = MagicMock()
    author.author = AsyncMock(
        return_value="""<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
<div data-composition-id="test" data-start="0" data-duration="10"
     data-width="1920" data-height="1080">
<div class="scene clip" id="scene-0" data-start="0" data-duration="5"
     data-track-index="0"></div>
<div class="scene clip" id="scene-1" data-start="5" data-duration="5"
     data-track-index="0"></div>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
<script>
const tl = gsap.timeline({ paused: true });
window.__timelines = window.__timelines || {};
window.__timelines["test"] = tl;
</script>
</body>
</html>"""
    )
    return author


@pytest.fixture
def mock_validator() -> MagicMock:
    """Create a mock CartoonCliValidator that returns passed audit."""
    validator = MagicMock()
    validator.validate = AsyncMock(
        return_value=StaticAudit(passed=True, scene_count=2)
    )
    return validator


@pytest.fixture
def mock_tts() -> MagicMock:
    """Create a mock CartoonTtsService that returns duration and words."""
    tts = MagicMock()
    tts.synthesize = AsyncMock(return_value=(5000, []))
    return tts


@pytest.fixture
def mock_renderer() -> MagicMock:
    """Create a mock CartoonVideoRenderer that returns video path."""
    renderer = MagicMock()
    renderer.render = AsyncMock(return_value=Path("/tmp/video.mp4"))
    return renderer


class TestCartoonPipeline:
    """Tests for CartoonPipeline orchestration."""

    @pytest.mark.asyncio
    async def test_generate_success(
        self,
        mock_planner: MagicMock,
        mock_director: MagicMock,
        mock_author: MagicMock,
        mock_validator: MagicMock,
        mock_tts: MagicMock,
        mock_renderer: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test successful video generation through full pipeline."""
        pipeline = CartoonPipeline(
            planner=mock_planner,
            director=mock_director,
            author=mock_author,
            validator=mock_validator,
            tts=mock_tts,
            renderer=mock_renderer,
        )

        request = CartoonVideoRequest(
            learning_need="Test learning need",
            profile={},
            output_dir=tmp_path,
        )

        artifact = await pipeline.generate(request)

        assert artifact.html is not None
        assert artifact.scene_count == 2
        assert artifact.repaired is False
        assert artifact.video_path == Path("/tmp/video.mp4")

    @pytest.mark.asyncio
    async def test_generate_with_repair(
        self,
        mock_planner: MagicMock,
        mock_director: MagicMock,
        mock_author: MagicMock,
        mock_renderer: MagicMock,
        mock_tts: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test generation triggers repair after validation failure."""
        # First validation fails, second passes
        validator = MagicMock()
        validator.validate = AsyncMock(
            side_effect=[
                StaticAudit(passed=False, problems=["Missing attribute"], scene_count=2),
                StaticAudit(passed=True, scene_count=2),
            ]
        )

        repairer = MagicMock()
        repairer.repair = AsyncMock(return_value="<html>repaired</html>")

        pipeline = CartoonPipeline(
            planner=mock_planner,
            director=mock_director,
            author=mock_author,
            validator=validator,
            repairer=repairer,
            tts=mock_tts,
            renderer=mock_renderer,
        )

        request = CartoonVideoRequest(
            learning_need="Test",
            profile={},
            output_dir=tmp_path,
        )

        artifact = await pipeline.generate(request)

        assert artifact.repaired is True
        assert repairer.repair.call_count == 1

    @pytest.mark.asyncio
    async def test_generate_fails_after_repair(
        self,
        mock_planner: MagicMock,
        mock_director: MagicMock,
        mock_author: MagicMock,
        mock_renderer: MagicMock,
        mock_tts: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that generation raises error if repair doesn't fix problems."""
        validator = MagicMock()
        validator.validate = AsyncMock(
            return_value=StaticAudit(
                passed=False,
                problems=["Unfixable problem"],
                scene_count=0,
            )
        )

        repairer = MagicMock()
        repairer.repair = AsyncMock(return_value="<html>still broken</html>")

        pipeline = CartoonPipeline(
            planner=mock_planner,
            director=mock_director,
            author=mock_author,
            validator=validator,
            repairer=repairer,
            tts=mock_tts,
            renderer=mock_renderer,
        )

        request = CartoonVideoRequest(
            learning_need="Test",
            profile={},
            output_dir=tmp_path,
        )

        with pytest.raises(CartoonGenerationError) as exc_info:
            await pipeline.generate(request)

        assert "修复后仍未通过验证" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_progress_callback(
        self,
        mock_planner: MagicMock,
        mock_director: MagicMock,
        mock_author: MagicMock,
        mock_validator: MagicMock,
        mock_tts: MagicMock,
        mock_renderer: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that progress callback is invoked during generation."""
        progress_messages: list[tuple[str, int]] = []

        async def progress_callback(message: str, percent: int) -> None:
            progress_messages.append((message, percent))

        pipeline = CartoonPipeline(
            planner=mock_planner,
            director=mock_director,
            author=mock_author,
            validator=mock_validator,
            tts=mock_tts,
            renderer=mock_renderer,
        )

        request = CartoonVideoRequest(
            learning_need="Test",
            profile={},
            output_dir=tmp_path,
        )

        await pipeline.generate(request, progress=progress_callback)

        assert len(progress_messages) >= 4
        assert any("规划" in msg for msg, _ in progress_messages)
        assert any(percent == 100 for _, percent in progress_messages)


class TestCartoonArtifact:
    """Tests for CartoonArtifact result container."""

    def test_artifact_attributes(self, tmp_path: Path) -> None:
        """Test that artifact stores all expected attributes."""
        brief = VideoBrief(
            title="Test",
            subject="Test",
            scenes=[SceneBrief(name="intro", narration="Hi")],
            mood="test",
        )
        style = StyleDecision(
            candidates=[
                StyleCandidate(
                    name="Style A",
                    source="preset",
                    rationale="Test A",
                    design_recipe="Test A",
                ),
                StyleCandidate(
                    name="Style B",
                    source="preset",
                    rationale="Test B",
                    design_recipe="Test B",
                ),
            ],
            selected_index=0,
        )

        artifact = CartoonArtifact(
            html="<html></html>",
            brief=brief,
            style=style,
            scene_count=1,
            repaired=False,
            video_path=tmp_path / "video.mp4",
        )

        assert artifact.html == "<html></html>"
        assert artifact.brief.title == "Test"
        assert artifact.style.selected.name == "Style A"
        assert artifact.scene_count == 1
        assert artifact.repaired is False


class TestCartoonGenerationError:
    """Tests for CartoonGenerationError exception."""

    def test_error_stores_audit(self) -> None:
        """Test that error stores the audit result for debugging."""
        audit = StaticAudit(
            passed=False,
            problems=["Problem 1", "Problem 2"],
            scene_count=0,
        )

        error = CartoonGenerationError("Generation failed", audit=audit)

        assert str(error) == "Generation failed"
        assert error.audit == audit
        assert len(error.audit.problems) == 2