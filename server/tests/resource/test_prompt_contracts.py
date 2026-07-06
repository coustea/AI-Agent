from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parents[2] / "app" / "resource" / "prompts"


def _read_prompt(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8")


def test_content_prompt_references_plan():
    text = _read_prompt("content.md")
    # Content prompt should reference the teaching plan / 协同计划
    assert "协同计划" in text or "教学" in text or "任务" in text
