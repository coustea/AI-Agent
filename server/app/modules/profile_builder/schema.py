from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str


class ProfileResponse(BaseModel):
    """画像查询响应"""
    knowledge_level: Optional[str] = None
    knowledge_level_score: Optional[int] = None
    cognitive_style: Optional[str] = None
    cognitive_style_score: Optional[int] = None
    error_pattern: Optional[str] = None
    error_pattern_score: Optional[int] = None
    learning_goal: Optional[str] = None
    learning_goal_score: Optional[int] = None
    learning_history: Optional[str] = None
    learning_history_score: Optional[int] = None
    interest_preference: Optional[str] = None
    interest_preference_score: Optional[int] = None
    learning_pace: Optional[str] = None
    learning_pace_score: Optional[int] = None
    cognitive_level: Optional[str] = None
    cognitive_level_score: Optional[int] = None
    profile_summary: Optional[str] = None
    updated_at: Optional[datetime] = None


class ProfileHistoryItem(BaseModel):
    """单条画像变更记录"""
    version: int
    knowledge_level: Optional[str] = None
    knowledge_level_score: Optional[int] = None
    cognitive_style: Optional[str] = None
    cognitive_style_score: Optional[int] = None
    error_pattern: Optional[str] = None
    error_pattern_score: Optional[int] = None
    learning_goal: Optional[str] = None
    learning_goal_score: Optional[int] = None
    learning_history: Optional[str] = None
    learning_history_score: Optional[int] = None
    interest_preference: Optional[str] = None
    interest_preference_score: Optional[int] = None
    learning_pace: Optional[str] = None
    learning_pace_score: Optional[int] = None
    cognitive_level: Optional[str] = None
    cognitive_level_score: Optional[int] = None
    profile_summary: Optional[str] = None
    change_reason: Optional[str] = None
    created_at: Optional[datetime] = None


class ChatMessageItem(BaseModel):
    """单条聊天消息"""
    role: str
    content: str
    created_at: Optional[datetime] = None