"""AI quiz answer review service."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from app.infra.llm import get_llm
from app.infra.prompts import prompts
from app.quiz.schemas import QuizReviewResponse


class QuizReviewService:
    async def review(
        self,
        question_type: str,
        question_content: str,
        standard_answer: str,
        user_answer: str,
        knowledge_points: list[str] | None = None,
    ) -> dict:
        llm = get_llm()
        system_prompt = prompts.get("quiz").get("quiz_review")
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=(
                f"题目类型: {question_type}\n"
                f"题目内容: {question_content}\n"
                f"标准答案: {standard_answer}\n"
                f"用户答案: {user_answer}\n"
                f"知识点: {', '.join(knowledge_points or [])}"
            )),
        ]
        result = await llm.ainvoke_json(QuizReviewResponse, messages)
        return result.model_dump()


quiz_review_service = QuizReviewService()
