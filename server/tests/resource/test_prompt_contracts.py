from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parents[2] / "app" / "resource" / "prompts"
OLD_CONTRACT_TERMS = (
    "blueprint",
    "instruction",
    "previous_results",
    "LearningBlueprint",
    "AgentInstruction",
    "ExecutionPlan",
)


def _read_prompt(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8")


def test_content_prompt_uses_teaching_plan_and_worker_task():
    text = _read_prompt("content.md")

    assert "教学计划" in text or "teaching_plan" in text.lower()
    assert "worker task" in text.lower()
    for term in OLD_CONTRACT_TERMS:
        assert term not in text
