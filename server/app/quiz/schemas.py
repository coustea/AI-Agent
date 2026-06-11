from __future__ import annotations

from pydantic import BaseModel, Field


class QuizQuestionRead(BaseModel):
    id: str
    subject: str
    subject_en: str | None = None
    type: str
    difficulty: str | None = None
    content: str
    options: dict[str, str] | None = None
    answer: str
    analysis: str
    knowledge_points: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    language: str | None = None
    split: str | None = None


class QuizQuestionListResponse(BaseModel):
    items: list[QuizQuestionRead]
    total: int
    page: int = 1
    page_size: int = 50
    subjects: list[str] = Field(default_factory=list)
    difficulties: list[str] = Field(default_factory=list)
    types: list[str] = Field(default_factory=list)


class QuizReviewRequest(BaseModel):
    """AI 答案审查请求"""
    question_id: str = Field(description="题目唯一标识")
    question_type: str = Field(description="题目类型：填空题或简答题")
    question_content: str = Field(description="题目内容")
    standard_answer: str = Field(description="标准答案")
    user_answer: str = Field(description="用户作答")
    knowledge_points: list[str] = Field(default_factory=list, description="相关知识点")


class QuizReviewResponse(BaseModel):
    """AI 答案审查响应"""
    score: int = Field(ge=0, le=100, description="得分 0-100")
    is_correct: bool = Field(description="是否正确 (score >= 60)")
    feedback: str = Field(description="一句话点评")
    improvement_hints: list[str] = Field(default_factory=list, description="改进建议")
