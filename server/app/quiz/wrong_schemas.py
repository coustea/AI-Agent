"""错题本 DTO — 添加请求、读取响应、列表响应。"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class WrongQuestionCreate(BaseModel):
    """添加错题请求 — 通过题目 ID 关联题库快照。"""
    question_id: str = Field(description="题目ID")
    user_answer: str | None = Field(default=None, description="用户答错的答案")


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


class WrongQuestionListResponse(BaseModel):
    """错题列表响应 — 分页结果，含可用的科目和类型筛选选项。"""
    items: list[WrongQuestionRead]
    total: int
    page: int = 1
    page_size: int = 20
    subjects: list[str] = Field(default_factory=list)
    types: list[str] = Field(default_factory=list)