"""PPT 课件生成数据契约。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class PPTModel(BaseModel):
    """PPT 模块基础模型，严格校验字段且剥离首尾空格。"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PPTBrief(PPTModel):
    """交付给 PPTAgent 的结构化创作任务需求。"""

    title: str = Field(min_length=1, description="课件标题")
    context: str = Field(min_length=1, description="课件教学上下文、大纲或上游素材")


class PPTArtifact(PPTModel):
    """PPT 生成完成后的物理文件产物引用。"""

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
            "file_size": self.pptx_path.stat().st_size if self.pptx_path.is_file() else 0,
        }


class PPTGenerationError(RuntimeError):
    """PPT 生成过程中的结构化异常。"""

    def __init__(self, message: str, *, stage: str = "generate") -> None:
        """初始化 PPT 生成异常及发生阶段。"""
        super().__init__(message)
        self.stage = stage


__all__ = [
    "PPTArtifact",
    "PPTBrief",
    "PPTGenerationError",
]
