from __future__ import annotations

from pathlib import Path

from app.infra.llm import load_prompt, render_prompt


def test_render_prompt_safely_interpolates() -> None:
    template = 'name={name}\njson={{"value": 1}}\nmissing={missing}'
    rendered = render_prompt(template, name="Alice")
    assert rendered == 'name=Alice\njson={{"value": 1}}\nmissing={missing}'


def test_load_prompt_reads_and_renders_file(tmp_path: Path) -> None:
    file = tmp_path / "test_prompt.md"
    file.write_text("Hello {target}, your score is {score}.", encoding="utf-8")

    result = load_prompt(file, target="Bob", score=95)
    assert result == "Hello Bob, your score is 95."


def test_load_prompt_without_kwargs(tmp_path: Path) -> None:
    file = tmp_path / "static.md"
    file.write_text("# Static Content\nNo variables here.", encoding="utf-8")

    result = load_prompt(file)
    assert result == "# Static Content\nNo variables here."
