"""Tests for the refactored PPTAgent (PptxGenJS harness) and CartoonAgent (HyperFrames)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.resource.agents import CartoonAgent, PPTAgent
from app.resource.schemas import (
    DownstreamContext,
    ResourceInput,
    ResourcePlan,
    ResourcePlanTask,
)
from app.shared.cartoon import (
    CartoonArtifact,
    CartoonGenerationError,
    build_cartoon_tool,
    build_cartoon_subagent_tool,
)
from app.shared.tools.skills import get_skill_loader
from app.shared.ppt import (
    PPTArtifact,
    PPTGenerationError,
    build_ppt_tool,
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
    assert "pptxgenjs" in pptx_doc

    hf_format = loader.get_content("hyperframes", "references/format.md")
    assert "<template>" in hf_format


def test_ppt_agent_generate_resource_success(tmp_path: Path) -> None:
    async def _run() -> None:
        pdf_file = tmp_path / "deck.pdf"
        pptx_file = tmp_path / "deck.pptx"
        pdf_file.write_bytes(b"%PDF-test")
        pptx_file.write_bytes(b"PK\x03\x04dummy-pptx")

        artifact = PPTArtifact(
            title="Python 协程与事件循环",
            pdf_path=pdf_file,
            preview_paths=[pdf_file] * 7,
            pptx_path=pptx_file,
            slide_count=7,
        )

        agent = PPTAgent()
        with patch.object(agent._generator, "generate", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = artifact
            result = await agent.generate_resource(_sample_resource_input())

        assert result.success is True
        assert result.file_type == "pptx"
        assert result.metadata["slide_count"] == 7
        assert len(result.metadata["preview_urls"]) == 7
        assert result.metadata["pptx_url"].endswith("deck.pptx")

    asyncio.run(_run())


def test_ppt_agent_handles_generation_error() -> None:
    async def _run() -> None:
        agent = PPTAgent()
        with patch.object(
            agent._generator,
            "generate",
            new_callable=AsyncMock,
            side_effect=PPTGenerationError("OOXML geometry check failed", stage="ooxml-audit"),
        ):
            result = await agent.generate_resource(_sample_resource_input())

        assert result.success is False
        assert "OOXML" in (result.error or "")
        assert result.metadata["generation_stage"] == "ooxml-audit"

    asyncio.run(_run())


def test_cartoon_agent_generate_resource_success() -> None:
    """Cartoon 生成已迁移为标准工具调用机制，测试工具链可用性。"""
    tool = build_cartoon_tool(username="alice")
    assert tool.name == "generate_teaching_video"
    assert tool.args_model is not None


def test_subagent_tool_wrappers_exposed() -> None:
    ppt_tool = build_ppt_tool(username="alice")
    video_tool = build_cartoon_tool(username="alice")
    assert ppt_tool.name == "generate_ppt_deck"
    assert video_tool.name == "generate_teaching_video"
