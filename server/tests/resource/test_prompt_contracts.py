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


def test_video_material_prompt_uses_teaching_plan_and_handoffs_only():
    text = _read_prompt("video_material.md")

    assert "teaching_plan" in text
    assert "upstream_handoffs" in text
    assert "DownstreamContext" in text
    for term in OLD_CONTRACT_TERMS:
        assert term not in text



