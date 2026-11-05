"""Cartoon (HyperFrames 教学视频) 数据模型 — Plan-and-Execute + Subagent 架构。"""

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
    """交给 CartoonPipeline 的统一请求契约。"""

    learning_need: str = Field(min_length=1)
    instruction_context: dict[str, Any] = Field(default_factory=dict)
    source_materials: list[str] = Field(default_factory=list)
    knowledge_points: list[str] = Field(default_factory=list)
    weak_knowledge_points: list[str] = Field(default_factory=list)
    configuration: CartoonGenerationConfig = Field(default_factory=CartoonGenerationConfig)


SceneVisualStyle = Literal[
    "concept_hero",
    "architecture_flow",
    "code_walkthrough",
    "comparison_split",
    "summary_recap",
]


class SceneStoryboardSpec(_Model):
    """STORYBOARD.json 中单个 HyperFrames 子场景 (compositions/sXX.html) 的规格定义。"""

    id: str = Field(pattern=r"^s[0-9]{2}$", description="场景编号，如 s01, s02")
    visual_style: SceneVisualStyle = "concept_hero"
    badge: str = Field(default="SCENE 01 · 核心概念", min_length=2)
    title: str = Field(min_length=2, description="本场景标题")
    subtitle: str = Field(default="", description="副标题或核心问题")
    narration: str = Field(min_length=6, description="本场景完整口播旁白文案（用于 TTS 合成）")
    visual_cards: list[str] = Field(
        default_factory=list,
        min_length=2,
        max_length=4,
        description="2~4 个动画展示卡片，格式建议为 '卡片标题：关键说明'",
    )
    code_or_formula: str = Field(default="", description="可选代码或核心公式")
    takeaway: str = Field(default="", description="底部高亮结论条")

    # 以下字段由 synthesize_narration (TTS) 阶段精确测定后填充
    start_sec: float = 0.0
    duration_sec: float = 5.0
    audio_duration_ms: int = 4500
    audio_src: str = ""


class VideoDesignPlan(_Model):
    """Cartoon 主规划智能体产出的完整视频分镜蓝图 (STORYBOARD.json)。"""

    title: str = Field(min_length=2)
    theme: Literal["dark_tech", "editorial_light", "emerald_studio"] = "dark_tech"
    scenes: list[SceneStoryboardSpec] = Field(min_length=3, max_length=7)
    total_duration_sec: float = 0.0
    total_duration_ms: int = 0

    @model_validator(mode="after")
    def normalize_scenes(self) -> "VideoDesignPlan":
        styles: list[SceneVisualStyle] = [
            "concept_hero",
            "architecture_flow",
            "comparison_split",
            "code_walkthrough",
            "summary_recap",
        ]
        for idx, scene in enumerate(self.scenes, start=1):
            scene.id = f"s{idx:02d}"
            if idx > 1 and scene.visual_style == self.scenes[idx - 2].visual_style:
                for candidate in styles:
                    if candidate != self.scenes[idx - 2].visual_style:
                        scene.visual_style = candidate
                        break
        return self


class SpeechClip(_Model):
    """单个场景合成后的音频片段信息。"""

    scene_id: str
    path: Path
    duration_ms: int = Field(gt=0)
    provider: str = "edge"
    voice: str = "zh-CN-XiaoxiaoNeural"


class CaptionCue(_Model):
    """WebVTT 字幕条目。"""

    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    text: str = Field(min_length=1)


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
    lesson_path: Path
    timeline_path: Path
    audit_path: Path


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
        super().__init__(message)
        self.stage = stage
        self.problems = list(problems or [])


__all__ = [
    "CaptionCue",
    "CartoonArtifact",
    "CartoonBrief",
    "CartoonGenerationConfig",
    "CartoonGenerationError",
    "CartoonResourceMetadata",
    "LessonDepth",
    "SceneStoryboardSpec",
    "SceneVisualStyle",
    "SpeechClip",
    "VideoDesignPlan",
]
