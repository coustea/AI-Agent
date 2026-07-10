"""题库 API 请求/响应模型 — 题目查询、AI 答案审查。"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


# 题目读取响应模型：包含题干、选项、答案、解析与元数据
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


# 题目列表分页响应模型：含筛选选项数据源
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


# AI 答案审查请求模型
class QuizReviewRequest(BaseModel):
    """AI 答案审查请求 — 用于分析题/简答题的自动评分。"""
    question_id: str = Field(description="题目唯一标识")
    question_type: str = Field(description="题目类型：分析题或简答题")
    question_content: str = Field(description="题目内容")
    standard_answer: str = Field(description="标准答案")
    user_answer: str = Field(description="用户作答")
    knowledge_points: list[str] = Field(default_factory=list, description="相关知识点")


# AI 答案审查响应模型：得分、正确性、反馈与建议
class QuizReviewResponse(BaseModel):
    """AI 答案审查响应 — 包含得分、是否正确、反馈和改进建议。"""
    score: int = Field(ge=0, le=100, description="得分 0-100")
    is_correct: bool = Field(description="是否正确 (score >= 60)")
    feedback: str = Field(description="一句话点评")
    improvement_hints: list[str] = Field(default_factory=list, description="改进建议")


# 单道客观题判卷结果模型
class ObjectiveQuestionResult(BaseModel):
    """单道客观题的前端判卷结果。"""
    question_id: str = Field(description="题目唯一标识")
    user_answer: str = Field(description="用户作答（如A、B、C或正确、错误，或填空题字面答案）")
    is_correct: bool = Field(description="前端判定的对错结果")
    # 动态题目快照字段（当该题不是题库中的固定题目时，前端需将这些快照信息传回以存错题本）
    subject: str | None = Field(default=None, description="所属科目")
    question_type: str | None = Field(default=None, description="题目类型（选择题、判断题、填空题等）")
    content: str | None = Field(default=None, description="题目内容")
    options: dict[str, str] | None = Field(default=None, description="题目选项")
    answer: str | None = Field(default=None, description="标准答案")
    analysis: str | None = Field(default=None, description="题目解析")


# 客观题批量提交请求模型
class ObjectiveSubmitRequest(BaseModel):
    """客观题判卷结果提交请求。"""
    results: list[ObjectiveQuestionResult] = Field(description="客观题作答结果列表")


# 客观题提交响应模型
class ObjectiveSubmitResponse(BaseModel):
    """客观题提交响应。"""
    processed_count: int = Field(description="处理的题目总数")
    wrong_saved_count: int = Field(description="自动收录进错题本的数量")


# 错题记录响应模型
class WrongQuestionRead(BaseModel):
    """错题记录响应 — 包含题目内容、用户答案和错误次数。"""
    id: int
    question_id: str
    subject: str
    question_type: str
    content: str
    options: dict[str, str] | None = None
    standard_answer: str | None = None
    analysis: str | None = None
    user_answer: str | None = None
    wrong_count: int
    note: str | None = None
    is_archived: bool
    created_at: datetime
    updated_at: datetime


# 错题列表分页响应模型
class WrongQuestionListResponse(BaseModel):
    """错题列表响应 — 分页结果，含可用的科目和类型筛选选项。"""
    items: list[WrongQuestionRead]
    total: int
    page: int = 1
    page_size: int = 20
    subjects: list[str] = Field(default_factory=list)
    types: list[str] = Field(default_factory=list)
