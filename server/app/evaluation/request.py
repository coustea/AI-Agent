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

    @model_validator(mode="before")
    @classmethod
    def infer_path_module_for_path_events(cls, data: Any) -> Any:
        if not isinstance(data, dict) or data.get("module"):
            has_module = bool(data.get("module"))
        else:
            has_module = False
        has_path_context = any(
            data.get(key) is not None
            for key in ("path_id", "path_node_id", "node_id")
        )
        metadata = data.get("event_metadata")
        if isinstance(metadata, dict):
            has_path_context = has_path_context or any(
                metadata.get(key) is not None
                for key in ("path_id", "path_node_id", "node_id")
            )
        if has_path_context:
            next_data = {**data}
            if not has_module:
                next_data["module"] = "path"
            if next_data.get("module") == "path" and next_data.get("event_type") == "quiz_submitted":
                next_data["event_type"] = "path_quiz_answered"
                next_metadata = dict(next_data.get("event_metadata") or {})
                if "is_correct" not in next_metadata and next_data.get("score") is not None:
                    next_metadata["is_correct"] = float(next_data["score"]) >= 60
                next_metadata.setdefault("attempt_index", 1)
                next_data["event_metadata"] = next_metadata
            return next_data
        return data

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
