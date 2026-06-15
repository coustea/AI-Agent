"""题库 API 请求/响应模型 — 题目查询、AI 答案审查。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class QuizQuestionRead(BaseModel):
    """题目读取响应 — 包含题干、选项、答案、解析和元数据。"""
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
    """题目列表响应 — 分页查询结果，含筛选选项。"""
    items: list[QuizQuestionRead]
    total: int
    page: int = 1
    page_size: int = 50
    # 可用的筛选选项（前端下拉框数据源）
    subjects: list[str] = Field(default_factory=list)
    difficulties: list[str] = Field(default_factory=list)
    types: list[str] = Field(default_factory=list)


class QuizReviewRequest(BaseModel):
    """AI 答案审查请求 — 用于填空题/简答题的自动评分。"""
    question_id: str = Field(description="题目唯一标识")
    question_type: str = Field(description="题目类型：填空题或简答题")
    question_content: str = Field(description="题目内容")
    standard_answer: str = Field(description="标准答案")
    user_answer: str = Field(description="用户作答")
    knowledge_points: list[str] = Field(default_factory=list, description="相关知识点")


class QuizReviewResponse(BaseModel):
    """AI 答案审查响应 — 包含得分、是否正确、反馈和改进建议。"""
    score: int = Field(ge=0, le=100, description="得分 0-100")
    is_correct: bool = Field(description="是否正确 (score >= 60)")
    feedback: str = Field(description="一句话点评")
    improvement_hints: list[str] = Field(default_factory=list, description="改进建议")
