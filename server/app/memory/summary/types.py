"""概要领域类型定义。

模块职责：
- 定义概要相关常量
- 定义概要默认结构
- 定义概要 LLM 输出模型
"""

from __future__ import annotations

from typing import Any, Final

from pydantic import BaseModel, Field


# Token 阈值（触发概要生成）
SUMMARY_TOKEN_THRESHOLD: Final[int] = 150


class SummaryLLMOutput(BaseModel):
    """概要 LLM 输出模型。"""
    current_learning_task: str = Field(default="", description="当前学习任务")
    original_user_questions: list[str] = Field(default_factory=list, description="用户原始问题")
    explained_content: list[str] = Field(default_factory=list, description="已解释内容")
    current_understanding: list[str] = Field(default_factory=list, description="当前理解状态")
    current_confusions: list[str] = Field(default_factory=list, description="当前困惑点")
    teaching_methods_used: list[str] = Field(default_factory=list, description="已使用教学方法")
    conversation_position: str = Field(default="", description="对话进度")
    next_action: str = Field(default="", description="下一步行动")
    references: list[str] = Field(default_factory=list, description="参考资料")


def make_default_summary_json() -> dict[str, Any]:
    """创建默认概要 JSON 结构。"""
    return {
        "current_learning_task": "",
        "original_user_questions": [],
        "explained_content": [],
        "current_understanding": [],
        "current_confusions": [],
        "teaching_methods_used": [],
        "conversation_position": "",
        "next_action": "",
        "references": [],
    }


def render_summary_markdown(summary_json: dict[str, Any]) -> str:
    """从 JSON 渲染 Markdown。"""
    if not summary_json:
        return "# 会话概要\n\n暂无概要信息。"

    lines = ["# 会话概要"]

    task = summary_json.get("current_learning_task", "")
    if task:
        lines.append(f"\n## 当前学习任务\n\n{task}")

    questions = summary_json.get("original_user_questions", [])
    if questions:
        lines.append("\n## 用户原始问题")
        for q in questions:
            lines.append(f"- {q}")

    explained = summary_json.get("explained_content", [])
    if explained:
        lines.append("\n## 已解释内容")
        for content in explained:
            lines.append(f"- {content}")

    understanding = summary_json.get("current_understanding", [])
    if understanding:
        lines.append("\n## 当前理解状态")
        for u in understanding:
            lines.append(f"- {u}")

    confusions = summary_json.get("current_confusions", [])
    if confusions:
        lines.append("\n## 当前困惑点")
        for c in confusions:
            lines.append(f"- {c}")

    methods = summary_json.get("teaching_methods_used", [])
    if methods:
        lines.append("\n## 已使用教学方法")
        for m in methods:
            lines.append(f"- {m}")

    position = summary_json.get("conversation_position", "")
    if position:
        lines.append(f"\n## 对话进度\n\n{position}")

    next_action = summary_json.get("next_action", "")
    if next_action:
        lines.append(f"\n## 下一步行动\n\n{next_action}")

    return "\n".join(lines)
