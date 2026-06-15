"""
资源生成 Agent 公共基础模块。

提供：
  build_worker_base_context — 构建所有 Resource Agent 通用的 prompt 上下文
  salvage_json_from_llm     — 从 LLM 输出中健壮地提取 JSON（处理 markdown fence 包裹）
"""

import json
import re

from app.resource.schemas import WorkerState
from app.resource.utils import format_learner_profile_for_prompt


def build_worker_base_context(state: WorkerState) -> list[str]:
    """构建所有 Resource Agent 生成时所需的通用基础上下文片段列表。

    按优先级拼接：
      1. 学习需求（必填）
      2. 学习者画像摘要（如有）
      3. 教学蓝图（多智能体模式下由 PlanningAgent 生成）
      4. 规划师指令（包含 focus、difficulty、constraints 等个性化参数）
    """
    parts = [f"## 学习需求\n{state.learning_need}"]

    # 学习者画像 — 作为生成个性化内容的首要依据
    profile_text = format_learner_profile_for_prompt(state.profile)
    if profile_text:
        parts.append(f"## 学习者画像摘要\n{profile_text}")

    # 教学蓝图 — 多智能体模式下由 PlanningAgent 预生成
    if state.blueprint:
        parts.append(f"## 教学蓝图\n{state.blueprint.model_dump_json(indent=2)}")

    # 规划师指令 — 包含 focus、difficulty、constraints 等参数
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
    """从 LLM 输出中健壮地提取 JSON 字典。

    依次尝试三种策略：
      1. 直接 JSON 解析
      2. 去除 ```json``` markdown fence 后解析
      3. 提取最外层 { } 后解析

    Args:
        raw: LLM 原始输出字符串。
        require_key: 若指定，解析后的 dict 必须包含此 key 才返回。

    Returns:
        解析成功的 dict，或 None（所有策略均失败）。
    """
    # 策略1: 直接解析
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and (not require_key or require_key in data):
            return data
    except json.JSONDecodeError:
        pass

    # 策略2: 去除 markdown fence 后解析
    match = re.search(r"```(?:json)?\s*\n(.*?)```", raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            if isinstance(data, dict) and (not require_key or require_key in data):
                return data
        except json.JSONDecodeError:
            pass

    # 策略3: 提取最外层花括号后解析
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
