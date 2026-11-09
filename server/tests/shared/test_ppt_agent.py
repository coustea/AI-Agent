"""教学课件 (PPT) 智能体与物理构建核验测试。"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from zipfile import ZipFile

import pytest

from app.shared.ppt.agent import PPTAgent
from app.shared.ppt.schemas import PPTArtifact, PPTBrief, PPTGenerationError
from app.shared.tools.skills import SkillLoader


def test_skill_files_and_escape(tmp_path: Path) -> None:
    """测试技能说明与子目录参考文件的解析与路径穿越拦截。"""
    root = tmp_path / "demo"
    root.mkdir()
    (root / "SKILL.md").write_text("---\nname: demo\ndescription: >\n  multi line\n  description\n---\nInstructions", encoding="utf-8")
    (root / "guide.md").write_text("Guide", encoding="utf-8")
    loader = SkillLoader(tmp_path)
    assert "multi line description" in loader.get_descriptions()
    assert "Guide" in loader.get_content("demo", "guide.md")
    assert loader.get_content("demo", "../secret").startswith("Error:")


@pytest.mark.asyncio
async def test_build_and_verify_rejects_command_failure(tmp_path: Path) -> None:
    """测试课件物理校验在底层 CLI 执行失败时抛出异常。"""
    deck = tmp_path / "deck.pptx"
    with ZipFile(deck, "w") as z:
        z.writestr("ppt/slides/slide1.xml", "<slide/>")
    registry = SimpleNamespace(execute=AsyncMock(return_value={"exit_code": 1, "stderr": "bad chart"}))

    agent = PPTAgent()
    with pytest.raises(ValueError, match="bad chart"):
        await agent._build_and_verify("test", tmp_path, registry)
    assert registry.execute.await_count == 1


@pytest.mark.asyncio
async def test_ppt_loop_reinjects_error_on_verify_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """测试课件生成核验失败时将错误原因回灌给模型，超出重试次数抛出 PPTGenerationError。"""
    async def fake_create(**kwargs: any) -> SimpleNamespace:
        msg = SimpleNamespace(tool_calls=None, content="done", model_dump=lambda **kw: {"role": "assistant", "content": "done"})
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create)))
    monkeypatch.setattr("app.shared.ppt.agent.get_llm_client", lambda _: (client, SimpleNamespace(model_name="test")))

    agent = PPTAgent()

    async def fail_verify(*args: any, **kwargs: any) -> None:
        raise ValueError("deck.pptx 损坏")

    monkeypatch.setattr(agent, "_build_and_verify", fail_verify)

    brief = PPTBrief(title="测试", context="测试大纲")
    with pytest.raises(PPTGenerationError, match="已达最大修复次数"):
        await agent.generate(brief, tmp_path)


@pytest.mark.asyncio
async def test_ppt_loop_success_returns_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """测试课件模型循环与物理核验成功时返回完整 PPTArtifact。"""
    async def fake_create(**kwargs: any) -> SimpleNamespace:
        msg = SimpleNamespace(tool_calls=None, content="done", model_dump=lambda **kw: {"role": "assistant", "content": "done"})
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create)))
    monkeypatch.setattr("app.shared.ppt.agent.get_llm_client", lambda _: (client, SimpleNamespace(model_name="test")))

    agent = PPTAgent()

    async def success_verify(title: str, workdir: Path, registry: any) -> PPTArtifact:
        return PPTArtifact(
            title=title,
            pptx_path=workdir / "deck.pptx",
            pdf_path=workdir / "deck.pdf",
            preview_paths=[workdir / "previews/slide-1.png"],
            slide_count=1,
        )

    monkeypatch.setattr(agent, "_build_and_verify", success_verify)

    brief = PPTBrief(title="测试标题", context="测试大纲")
    artifact = await agent.generate(brief, tmp_path)
    assert artifact.title == "测试标题"
    assert artifact.slide_count == 1
    assert "pptx_url" in artifact.metadata()
