"""Quiz review request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class QuizReviewRequest(BaseModel):
    question_type: str
    question_content: str
    standard_answer: str
    user_answer: str
    knowledge_points: list[str] | None = None


class QuizReviewResponse(BaseModel):
    score: int
    is_correct: bool
    feedback: str
    improvement_hints: list[str]
