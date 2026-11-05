"""Tests for the refactored PPTAgent (Plan-and-Execute + python-pptx + Skill Loading) and CartoonAgent (HyperFrames)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.resource.agents.cartoon import CartoonAgent
from app.resource.agents.ppt import PPTAgent
from app.resource.schemas import (
    DownstreamContext,
    ResourceInput,
    ResourcePlan,
    ResourcePlanTask,
)
from app.shared.cartoon import (
    CartoonArtifact,
    CartoonGenerationError,
    build_cartoon_subagent_tool,
)
from app.shared.tools import get_skill_loader
from app.shared.ppt import (
    PPTArtifact,
    PPTGenerationError,
    build_ppt_subagent_tool,
)


def _sample_teaching_plan() -> ResourcePlan:
    return ResourcePlan(
        learner_goal="深入理解 async/await 与事件循环调度机制",
        scope=["协程基础", "事件循环", "并发任务调度"],
        tasks=[
            ResourcePlanTask(
                agent_id="content",
                objective="讲解协程挂起与恢复的核心概念",
                focus=["协程基础"],
                required_elements=["定义", "代码示例"],
            ),
            ResourcePlanTask(
                agent_id="ppt",
                objective="制作事件循环可视化教学演示课件",
                focus=["事件循环"],
                required_elements=["核心流程", "对比卡片"],
            ),
            ResourcePlanTask(
                agent_id="cartoon",
                objective="通过动画直观呈现并发任务调度过程",
                focus=["并发任务调度"],
                required_elements=["状态流转", "关键结论"],
            ),
        ],
    )


def _sample_resource_input(**overrides: object) -> ResourceInput:
    defaults = dict(
        resource_id=42,
        username="alice",
        learning_need="深入理解 Python 协程与事件循环",
        learning_scenario="self_study",
        profile={},
        teaching_plan=_sample_teaching_plan(),
        upstream_handoffs={
            "content": DownstreamContext(
                source_agent="content",
                title="Python 协程核心讲义",
                one_sentence_summary="讲解协程挂起与恢复的底层原理",
                materials=["协程通过 await 让出控制权", "事件循环负责驱动就绪任务"],
            )
        },
    )
    return ResourceInput(**{**defaults, **overrides})


def test_local_skills_installed_and_loadable() -> None:
    loader = get_skill_loader()
    assert "pptx" in loader.skills
    assert "hyperframes" in loader.skills
    assert "hyperframes-cli" in loader.skills

    pptx_doc = loader.get_content("pptx")
    assert "<skill name=\"pptx\">" in pptx_doc
    assert "60-30-10" in pptx_doc

    hf_format = loader.get_content("hyperframes", "format.md")
    assert "<template>" in hf_format


def test_ppt_agent_generate_resource_success(tmp_path: Path) -> None:
    async def _run() -> None:
        html_file = tmp_path / "slides.html"
        pptx_file = tmp_path / "deck.pptx"
        html_file.write_text("<html>viewer</html>", encoding="utf-8")
        pptx_file.write_bytes(b"PK\x03\x04dummy-pptx")

        artifact = PPTArtifact(
            title="Python 协程与事件循环",
            path=html_file,
            pptx_path=pptx_file,
            generated_at=datetime.now(timezone.utc),
            slide_count=7,
        )

        agent = PPTAgent()
        with patch.object(agent._ppt_service, "generate", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = artifact
            result = await agent.generate_resource(_sample_resource_input())

        assert result.success is True
        assert result.file_type == "html"
        assert result.metadata["slide_count"] == 7
        assert result.metadata["html_url"].endswith("/ppt/slides.html")
        assert result.metadata["pptx_file_path"] == str(pptx_file)
        assert result.metadata["ppt_pipeline"]["engine"] == "python-pptx-harness-v2"

    asyncio.run(_run())


def test_ppt_agent_handles_generation_error() -> None:
    async def _run() -> None:
        agent = PPTAgent()
        with patch.object(
            agent._ppt_service,
            "generate",
            new_callable=AsyncMock,
            side_effect=PPTGenerationError("OOXML geometry check failed", stage="ooxml-audit"),
        ):
            result = await agent.generate_resource(_sample_resource_input())

        assert result.success is False
        assert "OOXML" in (result.error or "")
        assert result.metadata["generation_stage"] == "ooxml-audit"

    asyncio.run(_run())


def test_cartoon_agent_generate_resource_success(tmp_path: Path) -> None:
    async def _run() -> None:
        html_path = tmp_path / "index.html"
        video_path = tmp_path / "video.mp4"
        vtt_path = tmp_path / "captions.vtt"
        lesson_path = tmp_path / "lesson.json"
        timeline_path = tmp_path / "timeline.json"
        audit_path = tmp_path / "audit.json"
        for p in (html_path, video_path, vtt_path, lesson_path, timeline_path, audit_path):
            p.write_text("ok", encoding="utf-8")

        artifact = CartoonArtifact(
            title="Python 协程动画",
            duration_ms=18500,
            scene_count=3,
            output_dir=tmp_path,
            html_path=html_path,
            video_path=video_path,
            caption_path=vtt_path,
            lesson_path=lesson_path,
            timeline_path=timeline_path,
            audit_path=audit_path,
        )

        mock_pipeline = AsyncMock()
        mock_pipeline.generate = AsyncMock(return_value=artifact)
        agent = CartoonAgent(pipeline=mock_pipeline)
        result = await agent.generate_resource(_sample_resource_input())

        assert result.success is True
        assert result.file_type == "mp4"
        assert result.metadata["scene_count"] == 3
        assert result.metadata["video_url"].endswith(".mp4")
        assert result.metadata["preview_url"].endswith(".html")
        assert result.metadata["captions_url"].endswith(".vtt")

    asyncio.run(_run())


def test_subagent_tool_wrappers_exposed() -> None:
    ppt_tool = build_ppt_subagent_tool(username="alice")
    video_tool = build_cartoon_subagent_tool(username="alice")
    assert ppt_tool.name == "generate_ppt_deck"
    assert video_tool.name == "generate_teaching_video"
