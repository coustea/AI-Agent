from __future__ import annotations

from typing import Any

from app.infra.llm import get_llm
from app.path.prompt_manager import path_prompts


class NodeLearningAgent:
    """负责节点教程与节点测验题生成。"""

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
        weak_points_section = ""
        if weak_knowledge_points:
            weak_points_section = f"重点围绕这些薄弱知识点强化：{', '.join(weak_knowledge_points)}"
        profile_section = f"学习者画像:\n{profile_markdown[:2000]}" if profile_markdown else ""
        prompt = path_prompts.render_tutorial(
            path_goal=path_goal,
            node_title=node_title,
            mastery_target=mastery_target,
            tutorial_type=tutorial_type,
            weak_points_section=weak_points_section,
            profile_section=profile_section,
        )
        response = await self.llm.ainvoke(prompt, temperature=0.3)
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
        prompt = path_prompts.render_question_generation(
            path_goal=path_goal,
            node_title=node_title,
            mastery_target=mastery_target,
            tutorial_title=tutorial_title,
            tutorial_summary=tutorial_summary,
            round_no=round_no,
        )
        result = await self.llm.ainvoke_json(path_prompts.question_schema(), prompt)
        questions = result.questions if hasattr(result, "questions") else []
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
