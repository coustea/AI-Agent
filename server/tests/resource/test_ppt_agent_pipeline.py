"""Tests for PPTGenerator orchestration and PPTAgent."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.resource.agents.ppt import PPTAgent, build_resource_ppt_request, build_path_ppt_request
from app.shared.ppt import (
    PPTArtifact,
    PPTGenerationError,
    PPTGenerator,
    ResourcePPTRequest,
    PathPPTRequest,
)
from app.shared.ppt.models import PPTPlan, PPTSlide, KeyPoint
from app.resource.schemas import (
    AgentResult,
    DownstreamContext,
    NodeInput,
    ResourceInput,
)


def _deck_plan() -> PPTPlan:
    return PPTPlan(
        title="Intro to Python",
        subtitle="Beginners",
        purpose="Intro to Python",
        audience="Beginners",
        density="speaker_led",
        narrative="Start simple, build up",
        language="zh-CN",
        slides=[
            PPTSlide(
                role="cover",
                shape="statement",
                title="Python Basics",
                statement="Welcome to Python",
            ),
            PPTSlide(
                role="explain",
                shape="concept",
                title="What is a Variable",
                points=[KeyPoint(label="Variable", detail="A container for value")],
            ),
            PPTSlide(
                role="summary",
                shape="statement",
                title="Summary",
                statement="Python is easy",
            ),
        ],
    )


def _source_pack() -> ResourcePPTRequest:
    return ResourcePPTRequest(
        learning_need="Learn Python basics",
        learning_scenario="self_study",
        profile={},
        teaching_plan=None,
        artifacts=[],
    )


def _resource_input(**overrides: object) -> ResourceInput:
    defaults = dict(
        resource_id=42,
        learning_need="Learn Python",
        learning_scenario="self_study",
        profile={},
    )
    return ResourceInput(**{**defaults, **overrides})


def _node_input(**overrides: object) -> NodeInput:
    defaults = dict(
        path_id=1,
        node_id=7,
        node_key="n7",
        path_title="Python Path",
        path_goal="Master Python",
        node_title="Variables",
        difficulty="easy",
        tutorial_title="Variables Tutorial",
        tutorial_markdown="# Variables\n...",
        profile={},
    )
    return NodeInput(**{**defaults, **overrides})


# ---------------------------------------------------------------------------
# 1. Pipeline execution passes
# ---------------------------------------------------------------------------


def test_pipeline_execution_passes():
    async def _run():
        # Mock LLM: ainvoke returns a response with .content (Markdown text)
        mock_response = MagicMock()
        mock_response.content = """# Test Deck

---

## [cover|statement|reveal] Test

**核心论点：** Welcome

---

## [explain|concept|reveal] Topic

**核心论点：** A topic
- **Point：** Detail here
**总结金句：** Summary

---

## [summary|statement|reveal] End

**核心论点：** Done
"""
        llm = MagicMock()
        llm.ainvoke = AsyncMock(return_value=mock_response)
        generator = PPTGenerator(llm=llm)

        resolved_deck = MagicMock()
        resolved_deck.template.manifest.id = "neon-cyber"
        resolved_deck.template.manifest.name = "Neon Cyber"
        resolved_deck.slides = [MagicMock() for _ in range(6)]

        with patch.object(generator._templates, "resolve", return_value=resolved_deck):
            with patch.object(generator._renderer, "render", return_value="<html>ok</html>"):
                with patch("app.shared.ppt.generator.PPTHTMLPublisher") as mock_pub_cls:
                    mock_pub = MagicMock()
                    mock_pub.publish.return_value = Path("/tmp/test.html")
                    mock_pub_cls.return_value = mock_pub

                    artifact = await generator.generate(_source_pack(), output_dir=Path("/tmp"))

                    assert artifact.slide_count == 6
                    assert artifact.template_id == "neon-cyber"
                    assert artifact.template_name == "Neon Cyber"
                    mock_pub.publish.assert_called_once_with("slides", "<html>ok</html>")

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# 2. PPTAgent standalone resource — file_id and html_url
# ---------------------------------------------------------------------------


def test_ppt_agent_standalone_resource():
    async def _run():
        with tempfile.NamedTemporaryFile(
            suffix=".html", delete=False, mode="w"
        ) as tmp:
            tmp.write("<html>slide</html>")
            tmp_path = Path(tmp.name)

        artifact = PPTArtifact(
            path=tmp_path,
            plan=_deck_plan(),
            template_id="neon-cyber",
            template_name="Neon Cyber",
            slide_count=6,
        )

        with patch("app.resource.agents.ppt.PPTGenerator.generate", new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = artifact
            agent = PPTAgent()

            result = await agent.generate_resource(_resource_input())

            assert result.success is True
            assert result.file_type == "html"
            mock_generate.assert_awaited_once()
            call_kwargs = mock_generate.call_args
            assert call_kwargs.kwargs["output_dir"] == Path("/Users/apple/Code/software/server/static/anonymous/resources/42/ppt")
        # html_url is derived from user_resource_ppt_dir
        assert "/static/" in result.metadata["html_url"]
        tmp_path.unlink(missing_ok=True)

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# 3. PPTAgent path node — node key and path ID used in URL
# ---------------------------------------------------------------------------


def test_ppt_agent_path_node():
    async def _run():
        with tempfile.NamedTemporaryFile(
            suffix=".html", delete=False, mode="w"
        ) as tmp:
            tmp.write("<html>slide</html>")
            tmp_path = Path(tmp.name)

        artifact = PPTArtifact(
            path=tmp_path,
            plan=_deck_plan(),
            template_id="neon-cyber",
            template_name="Neon Cyber",
            slide_count=6,
        )

        mock_source_pack = _source_pack()
        with patch("app.resource.agents.ppt.build_path_ppt_request", return_value=mock_source_pack):
            with patch("app.resource.agents.ppt.PPTGenerator.generate", new_callable=AsyncMock) as mock_generate:
                mock_generate.return_value = artifact
                agent = PPTAgent()
                result = await agent.generate_node(_node_input())

        assert result.success is True
        mock_generate.assert_awaited_once()
        call_kwargs = mock_generate.call_args
        assert call_kwargs.kwargs["output_dir"] == Path("/Users/apple/Code/software/server/static/anonymous/paths/1/nodes/7/ppt")
        assert "/static/" in result.metadata["html_url"]
        tmp_path.unlink(missing_ok=True)

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# 4. Result metadata shape — file_type, content, metadata fields
# ---------------------------------------------------------------------------


def test_ppt_agent_result_metadata():
    async def _run():
        with tempfile.NamedTemporaryFile(
            suffix=".html", delete=False, mode="w"
        ) as tmp:
            tmp.write("<html>slide</html>")
            tmp_path = Path(tmp.name)

        artifact = PPTArtifact(
            path=tmp_path,
            plan=_deck_plan(),
            template_id="neon-cyber",
            template_name="Neon Cyber",
            slide_count=8,
        )

        mock_source_pack = _source_pack()
        with patch("app.resource.agents.ppt.build_resource_ppt_request", return_value=mock_source_pack):
            with patch("app.resource.agents.ppt.PPTGenerator.generate", new_callable=AsyncMock) as mock_generate:
                mock_generate.return_value = artifact
                agent = PPTAgent()
                result = await agent.generate_resource(_resource_input())

        assert result.file_type == "html"
        assert result.content == ""
        # metadata must contain exactly the new fields from PPTAgent
        expected_keys = {
            "agent_id",
            "html_file_path",
            "html_url",
            "slide_count",
            "style_name",
            "template_id",
            "density",
            "file_size",
        }
        assert set(result.metadata.keys()) == expected_keys
        assert result.metadata["slide_count"] == 8
        assert result.metadata["density"] == "speaker_led"
        assert result.metadata["style_name"] == "Neon Cyber"
        assert result.metadata["template_id"] == "neon-cyber"
        assert result.metadata["file_size"] == tmp_path.stat().st_size
        tmp_path.unlink(missing_ok=True)

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# 5. PPTGenerationError — Agent returns success=False
# ---------------------------------------------------------------------------


def test_ppt_agent_generation_error():
    async def _run():
        mock_source_pack = _source_pack()
        with patch("app.resource.agents.ppt.build_resource_ppt_request", return_value=mock_source_pack):
            with patch("app.resource.agents.ppt.PPTGenerator.generate", new_callable=AsyncMock) as mock_generate:
                mock_generate.side_effect = PPTGenerationError(
                    "planning", "presentation failed"
                )
                agent = PPTAgent()
                result = await agent.generate_resource(_resource_input())

        assert result.success is False
        assert result.error != ""
        assert "failed" in result.error.lower()

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# 6. Standalone and path don't share source-pack builders
# ---------------------------------------------------------------------------


def test_ppt_agent_standalone_and_path_use_different_source_pack_builders():
    """Verify standalone uses build_resource_ppt_request and path uses
    build_path_ppt_request — they must not share records."""

    resource_input = _resource_input()
    resource_req = build_resource_ppt_request(resource_input)

    assert isinstance(resource_req, ResourcePPTRequest)
    assert not hasattr(resource_req, "node_title")

    node_input = _node_input()
    node_req = build_path_ppt_request(node_input)

    assert isinstance(node_req, PathPPTRequest)
    assert node_req.node_title == "Variables"
    assert node_req.path_title == "Python Path"
