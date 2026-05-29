"""
资源生成 Agent 公共基础模块。
"""

from app.resource.schemas import WorkerState
from app.resource.utils import format_learner_profile_for_prompt


def build_worker_base_context(state: WorkerState) -> list[str]:
    """
    构建所有 Resource Agent 生成时所需的通用基础上下文部分。
    
    返回按顺序拼接的片段列表，包括：
    - 学习需求
    - 学习者画像摘要
    - 教学蓝图
    - 规划师指令
    """
    parts = [f"## 学习需求\n{state.learning_need}"]

    # 学习者画像（首要依据）
    profile_text = format_learner_profile_for_prompt(state.profile)
    if profile_text:
        parts.append(f"## 学习者画像摘要\n{profile_text}")

    if state.blueprint:
        parts.append(f"## 教学蓝图\n{state.blueprint.model_dump_json(indent=2)}")

    if state.instruction:
        lines = [f"## 规划师指令\n- 重点: {state.instruction.focus}"]
        if getattr(state.instruction, "difficulty", None):
            lines.append(f"- 难度: {state.instruction.difficulty}")
        if getattr(state.instruction, "personalization_notes", None):
            lines.append(f"- 个性化建议: {state.instruction.personalization_notes}")
        for c in state.instruction.constraints:
            lines.append(f"- 约束: {c}")
        parts.append("\n".join(lines))

    return parts
