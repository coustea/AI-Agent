"""PPT generation input and output contracts."""
from pathlib import Path
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

class PPTModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class PPTPreferences(PPTModel):
    """前端/调用方传入的课件偏好配置。"""

    template: str = "auto"
    explanation_style: Literal["concept", "case_driven", "problem_led", "review"] = "concept"
    narrative_style: Literal["concept", "case_driven", "problem_led", "review"] = "concept"
    density: Literal["concise", "standard", "detailed"] = "standard"
    focus: list[str] = Field(default_factory=lambda: ["core_concepts"])
    emphasis: list[Literal["core_concepts", "cases", "pitfalls", "derivation"]] = Field(
        default_factory=lambda: ["core_concepts"],
        min_length=1,
        max_length=4,
    )
    include_speaker_notes: bool = True


class PPTBrief(PPTModel):
    title: str = Field(min_length=1)
    context: str = Field(min_length=1)
    preferences: PPTPreferences = Field(default_factory=PPTPreferences)

class PPTArtifact(PPTModel):
    title: str
    pptx_path: Path
    pdf_path: Path
    preview_paths: list[Path]
    slide_count: int = Field(gt=0)

    def metadata(self) -> dict[str, Any]:
        """将 PPT 产物信息转换为包含静态访问 URL 的元数据字典。"""
        from app.config import static_url
        return {
            "agent_id": "ppt",
            "pptx_url": static_url(self.pptx_path),
            "pdf_url": static_url(self.pdf_path),
            "preview_urls": [static_url(p) for p in self.preview_paths],
            "slide_count": self.slide_count,
            "file_size": self.pptx_path.stat().st_size,
        }

class PPTGenerationError(RuntimeError):
    def __init__(self, message: str, *, stage: str = "generate") -> None:
        """初始化 PPT 生成异常及发生阶段。"""
        super().__init__(message)
        self.stage = stage
