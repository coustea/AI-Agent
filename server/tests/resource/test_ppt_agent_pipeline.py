"""Tests for the refactored PPTAgent (PptxGenJS harness) and CartoonAgent (HyperFrames)."""

from __future__ import annotations

from app.shared.cartoon import build_cartoon_tool
from app.shared.ppt import build_ppt_tool
from app.shared.tools.skills import get_skill_loader


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
