"""Cartoon (HyperFrames 教学视频) 数据契约。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class CartoonModel(BaseModel):
    """Cartoon 模块基础模型，严格校验字段且剥离首尾空格。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CartoonGenerationConfig(CartoonModel):
    """前端与调用方传入的教学视频偏好配置。"""

    lesson_depth: Literal["focused", "standard", "deep"] = "standard"
    visual_density: Literal["moderate", "rich", "intensive"] = "rich"
    pace: Literal["fast", "balanced", "calm"] = "balanced"
    voice: Literal["teacher", "coach"] = "teacher"
    target_duration_seconds: int = 120


class CartoonBrief(CartoonModel):
    """交付给 CartoonAgent 的结构化创作任务需求。"""

    title: str = Field(default="", description="视频标题")
    learning_need: str = Field(min_length=1, description="核心教学需求或主题说明")
    source_materials: list[str] = Field(default_factory=list, description="上游参考材料或讲义要点")
    configuration: CartoonGenerationConfig = Field(default_factory=CartoonGenerationConfig)
    instruction_context: dict[str, Any] = Field(default_factory=dict, description="教学上下文元数据")


class CartoonArtifact(CartoonModel):
    """视频生成完成后的物理文件产物引用与媒体规格。"""

    title: str
    duration_seconds: float = Field(default=0.0, ge=0, description="视频实际播放时长（秒）")
    scene_count: int = Field(ge=1, description="语义场景分镜数")
    width: int = Field(default=1920, gt=0, description="视频画面宽度")
    height: int = Field(default=1080, gt=0, description="视频画面高度")
    html_path: Path
    video_path: Path
    caption_path: Path

    def metadata(self) -> dict[str, Any]:
        """将视频产物信息转换为包含静态访问 URL 的元数据字典。"""
        from app.config import static_url

        return {
            "agent_id": "cartoon",
            "video_url": static_url(self.video_path),
            "preview_url": static_url(self.html_path),
            "captions_url": static_url(self.caption_path),
            "duration_seconds": self.duration_seconds,
            "scene_count": self.scene_count,
            "width": self.width,
            "height": self.height,
        }


class CartoonGenerationError(RuntimeError):
    """动画视频生成阶段结构化异常。"""

    def __init__(self, message: str, *, stage: str = "generate", problems: list[str] | None = None) -> None:
        """初始化动画生成异常、发生阶段及详细问题列表。"""
        super().__init__(message)
        self.stage = stage
        self.problems = list(problems or [])


__all__ = [
    "CartoonArtifact",
    "CartoonBrief",
    "CartoonGenerationConfig",
    "CartoonGenerationError",
]
