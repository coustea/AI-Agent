from __future__ import annotations
from typing import Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, model_validator

ModuleType = Literal["chat", "resource", "path", "quiz", "visualizer"]

LearningEventType = Literal[
    "chat_dialogue",
    "resource_generated", "resource_viewed", "resource_completed", "resource_feedback",
    "path_node_started", "path_node_completed", "path_quiz_answered", "path_feedback",
    "quiz_submitted",
    "visualizer_run",
]

class LearningEventCreate(BaseModel):
    module: ModuleType
    entity_id: str | None = Field(default=None, max_length=255, description="模块内实体 ID")
    event_type: LearningEventType
    score: float | None = Field(default=None, ge=0, le=100)
    course: str | None = Field(default=None, max_length=200)
    topic: str | None = Field(default=None, max_length=200)
    path_id: int | None = Field(default=None, description="路径 ID 快捷字段")
    path_node_id: int | None = Field(default=None, description="路径节点 ID 快捷字段")
    node_id: str | None = Field(default=None, max_length=255, description="路径节点业务 ID 快捷字段")
    event_metadata: dict[str, Any] = Field(default_factory=dict)
    client_event_id: str | None = Field(default=None, max_length=64)
    occurred_at: datetime | None = Field(default=None)

    @model_validator(mode="after")
    def validate_metadata_constraints(self) -> LearningEventCreate:
        if self.event_type in ("quiz_submitted", "path_quiz_answered"):
            is_correct = self.event_metadata.get("is_correct")
            if not isinstance(is_correct, bool):
                raise ValueError("quiz_submitted and path_quiz_answered require boolean 'is_correct' in event_metadata")
        elif self.event_type == "resource_feedback":
            feedback = self.event_metadata.get("feedback")
            if feedback not in ("helpful", "not_helpful"):
                raise ValueError("resource_feedback requires 'feedback' to be 'helpful' or 'not_helpful' in event_metadata")
        
        # Ensure we don't have natural language feedback, questions, answers, or chat content in event_metadata
        for key in ["feedback_text", "question_text", "answer_text", "chat_content", "user_message", "bot_message"]:
            if key in self.event_metadata:
                self.event_metadata.pop(key)
        return self


class LearningSessionCreate(BaseModel):
    source_page: str = Field(max_length=50)
    started_at: datetime
    ended_at: datetime
    duration_seconds: int = Field(ge=1, le=14400) # Capped to 14400 (4 hours)
    course: str | None = Field(default=None, max_length=200)
    topic: str | None = Field(default=None, max_length=200)
    event_metadata: dict[str, Any] = Field(default_factory=dict)
    client_session_id: str | None = Field(default=None, max_length=64)
