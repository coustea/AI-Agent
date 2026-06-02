"""
资源生成 Agent 公共基础模块。
"""

import json
import re

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


def salvage_json_from_llm(raw: str, *, require_key: str | None = None) -> dict | None:
    """Try to extract a JSON dict from LLM output that may be wrapped in markdown fences.

    Args:
        raw: Raw LLM output string.
        require_key: If provided, the parsed dict must contain this key to be accepted.
    """
    # Try direct parse
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and (not require_key or require_key in data):
            return data
    except json.JSONDecodeError:
        pass

    # Try stripping ```json``` fence
    match = re.search(r"```(?:json)?\s*\n(.*?)```", raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            if isinstance(data, dict) and (not require_key or require_key in data):
                return data
        except json.JSONDecodeError:
            pass

    # Try finding outermost { }
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(raw[start:end + 1])
            if isinstance(data, dict) and (not require_key or require_key in data):
                return data
        except json.JSONDecodeError:
            pass

    return None
