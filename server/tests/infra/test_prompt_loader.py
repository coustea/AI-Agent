from __future__ import annotations

from pathlib import Path


def test_module_prompt_loader_reads_prompt_files(tmp_path: Path) -> None:
    from app.infra.prompts import ModulePromptLoader

    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()
    (prompt_dir / "system.md").write_text("hello", encoding="utf-8")
    nested = prompt_dir / "nested"
    nested.mkdir()
    (nested / "guide.md").write_text("world", encoding="utf-8")

    loader = ModulePromptLoader(prompt_dir, module_name="demo")

    assert loader.get("system") == "hello"
    assert loader.get("nested/guide") == "world"
    assert loader.list() == ["nested/guide", "system"]


def test_module_prompt_loader_renders_placeholders_safely(tmp_path: Path) -> None:
    from app.infra.prompts import ModulePromptLoader

    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()
    (prompt_dir / "template.md").write_text(
        'name={name}\njson={{"value": 1}}\nmissing={missing}',
        encoding="utf-8",
    )

    loader = ModulePromptLoader(prompt_dir, module_name="demo")

    rendered = loader.render("template", name="Alice")

    assert rendered == 'name=Alice\njson={{"value": 1}}\nmissing={missing}'


def test_module_prompt_loader_tracks_prompt_metadata(tmp_path: Path) -> None:
    from app.infra.prompts import ModulePromptLoader

    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()
    (prompt_dir / "x.md").write_text("content", encoding="utf-8")

    loader = ModulePromptLoader(prompt_dir, module_name="demo")
    loader.load_all()

    status = loader.status()

    assert status["x"]["path"] == "x.md"
    assert status["x"]["size"] == len("content")
    assert status["x"]["status"] == "ok"


def test_prompt_registry_registers_and_warms(tmp_path: Path) -> None:
    from app.infra.prompts import PromptRegistry

    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()
    (prompt_dir / "hello.md").write_text("world", encoding="utf-8")

    registry = PromptRegistry()
    loader = registry.register("test_module", prompt_dir)

    assert registry.get("test_module") is loader
    registry.warm_all()
    assert loader.get("hello") == "world"

    status = registry.status()
    assert "test_module" in status
    assert status["test_module"]["hello"]["status"] == "ok"


def test_prompt_registry_raises_on_unknown_module() -> None:
    from app.infra.prompts import PromptRegistry

    registry = PromptRegistry()
    try:
        registry.get("nonexistent")
    except KeyError as exc:
        assert "nonexistent" in str(exc)
    else:
        raise AssertionError("Expected KeyError")
