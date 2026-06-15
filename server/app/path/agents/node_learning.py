from __future__ import annotations

from typing import Any

from app.config import INFERENCE_TEMPERATURE
from app.infra.llm import get_llm
from app.infra.prompts import prompts
from app.path.schemas import AgentQuestionSet


class NodeLearningAgent:
    """节点学习智能体 — 负责生成节点教程和节点测验题。"""

    def __init__(self) -> None:
        self.llm = get_llm()

    async def generate_tutorial(
        self,
        *,
        path_goal: str,
        node_title: str,
        mastery_target: str,
        tutorial_type: str,
        weak_knowledge_points: list[str],
        profile_markdown: str = "",
    ) -> dict[str, Any]:
        """生成节点教程内容。

        Args:
            path_goal: 学习路径总目标
            node_title: 当前节点标题
            mastery_target: 掌握目标描述
            tutorial_type: 教程类型（primary/remediation/reinforced）
            weak_knowledge_points: 需要强化的薄弱知识点
            profile_markdown: 学习者画像文本

        Returns:
            包含 title、summary、content_markdown、knowledge_points 的字典
        """
        # 构建薄弱知识点提示段落
        weak_points_section = ""
        if weak_knowledge_points:
            weak_points_section = f"重点围绕这些薄弱知识点强化：{', '.join(weak_knowledge_points)}"
        # 截断过长的画像文本，避免超出 prompt 限制
        profile_section = f"学习者画像:\n{profile_markdown[:2000]}" if profile_markdown else ""
        # 渲染教程生成提示词
        prompt = prompts.get("path").render(
            "tutorial",
            path_goal=path_goal,
            node_title=node_title,
            mastery_target=mastery_target,
            tutorial_type=tutorial_type,
            weak_points_section=weak_points_section,
            profile_section=profile_section,
        )
        # 调用 LLM 生成教程 Markdown 内容
        response = await self.llm.ainvoke(prompt, temperature=INFERENCE_TEMPERATURE)
        content = response.content if hasattr(response, "content") else str(response)
        return {
            "title": f"{node_title} - {tutorial_type}",
            "summary": tutorial_type,
            "content_markdown": content,
            "knowledge_points": [node_title],
        }

    async def generate_questions(
        self,
        *,
        path_goal: str,
        node_title: str,
        mastery_target: str,
        tutorial_title: str,
        tutorial_summary: str,
        round_no: int,
    ) -> list[dict[str, Any]]:
        """生成节点测验题。

        基于教程内容生成结构化的选择题/判断题，
        返回包含 question、choice、answer、analysis 的字典列表。
        """
        prompt = prompts.get("path").render(
            "question_generation",
            path_goal=path_goal,
            node_title=node_title,
            mastery_target=mastery_target,
            tutorial_title=tutorial_title,
            tutorial_summary=tutorial_summary,
            round_no=round_no,
        )
        # LLM 结构化输出 → AgentQuestionSet（含 questions 列表）
        result = await self.llm.ainvoke_json(AgentQuestionSet, prompt)
        questions = result.questions if hasattr(result, "questions") else []
        # 标准化输出格式，确保每个题目包含统一的字段
        normalized: list[dict[str, Any]] = []
        for item in questions:
            choice = dict(getattr(item, "choice", {}) or {})
            normalized.append(
                {
                    "question": getattr(item, "question", ""),
                    "choice": choice,
                    "answer": str(getattr(item, "answer", "")),
                    "analysis": getattr(item, "analysis", ""),
                    "knowledge_points": list(getattr(item, "knowledge_points", []) or [node_title]),
                    "type": getattr(item, "type", "single_choice"),
                }
            )
        return normalized
