"""Cartoon (HyperFrames 教学视频) 数据模型 — CLI 工具循环。"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Model(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class LessonDepth(StrEnum):
    FOCUSED = "focused"
    STANDARD = "standard"
    DEEP = "deep"


class CartoonGenerationConfig(_Model):
    """前端/调用方传入的动画视频偏好配置。"""

    lesson_depth: LessonDepth = LessonDepth.STANDARD
    visual_density: Literal["moderate", "rich", "intensive"] = "rich"
    pace: Literal["fast", "balanced", "calm"] = "balanced"
    voice: Literal["teacher", "coach"] = "teacher"
    target_duration_seconds: int = Field(default=120, ge=30)


class CartoonBrief(_Model):
    """交给动画视频 agent 的统一请求契约。"""

    learning_need: str = Field(min_length=1)
    instruction_context: dict[str, Any] = Field(default_factory=dict)
    source_materials: list[str] = Field(default_factory=list)
    knowledge_points: list[str] = Field(default_factory=list)
    weak_knowledge_points: list[str] = Field(default_factory=list)
    configuration: CartoonGenerationConfig = Field(default_factory=CartoonGenerationConfig)


class CartoonInput(_Model):
    """一次动画视频生成的完整输入。"""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True, arbitrary_types_allowed=True)

    output_dir: Path
    brief: CartoonBrief


class CartoonArtifact(_Model):
    """Cartoon 生成完成后的产物引用。"""

    schema_version: Literal["cartoon/artifact-v8"] = "cartoon/artifact-v8"
    title: str
    duration_ms: int = Field(gt=0)
    scene_count: int = Field(ge=1)
    has_audio: Literal[True] = True
    output_dir: Path
    html_path: Path
    video_path: Path
    caption_path: Path


class CartoonResourceMetadata(_Model):
    """发布到 AgentResult.metadata 的前端契约。"""

    agent_id: Literal["cartoon"] = "cartoon"
    schema_version: Literal["cartoon/v8"] = "cartoon/v8"
    engine: Literal["hyperframes"] = "hyperframes"
    has_audio: Literal[True] = True
    quality_passed: Literal[True] = True
    video_url: str = Field(min_length=1)
    preview_url: str = Field(min_length=1)
    captions_url: str = Field(min_length=1)
    duration_seconds: float = Field(gt=0)
    scene_count: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_urls(self) -> "CartoonResourceMetadata":
        """校验各产物 URL 扩展名契约（.mp4/.html/.vtt）。"""
        expected = {
            "video_url": ".mp4",
            "preview_url": ".html",
            "captions_url": ".vtt",
        }
        for field_name, suffix in expected.items():
            if not str(getattr(self, field_name)).strip().endswith(suffix):
                raise ValueError(f"{field_name} must reference a {suffix} file")
        return self


class CartoonGenerationError(RuntimeError):
    """动画视频生成阶段结构化异常。"""

    def __init__(self, message: str, *, stage: str, problems: list[str] | None = None) -> None:
        """初始化动画生成异常、发生阶段及详细问题列表。"""
        super().__init__(message)
        self.stage = stage
        self.problems = list(problems or [])
