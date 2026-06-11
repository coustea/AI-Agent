"""错题本 DTO。"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class WrongQuestionCreate(BaseModel):
    """添加错题请求"""
    question_id: str = Field(description="题目ID")
    user_answer: str | None = Field(default=None, description="用户答错的答案")


class WrongQuestionRead(BaseModel):
    """错题记录"""
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
    """错题列表响应"""
    items: list[WrongQuestionRead]
    total: int
    page: int = 1
    page_size: int = 20
    subjects: list[str] = Field(default_factory=list)
    types: list[str] = Field(default_factory=list)