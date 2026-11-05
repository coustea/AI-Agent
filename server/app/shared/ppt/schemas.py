"""PPT 领域数据模型 — Plan-and-Execute + python-pptx 架构。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PPTModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PPTSource(PPTModel):
    """上游交接给 PPT 的素材摘要。"""

    agent_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    materials: list[str] = Field(default_factory=list, max_length=12)


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


class ResourcePPT(PPTModel):
    """独立资源模块发起的 PPT 生成请求。"""

    username: str = ""
    learning_need: str = Field(min_length=1)
    learning_scenario: str = "self_study"
    profile: dict[str, Any] | str = Field(default_factory=dict)
    resource_plan: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[PPTSource] = Field(default_factory=list, max_length=16)
    preferences: PPTPreferences = Field(default_factory=PPTPreferences)


class PathPPT(PPTModel):
    """学习路径模块发起的 PPT 生成请求。"""

    username: str = ""
    profile: dict[str, Any] | str = Field(default_factory=dict)
    preferences: PPTPreferences = Field(default_factory=PPTPreferences)
    path_title: str = Field(min_length=1)
    path_goal: str = Field(min_length=1)
    node_title: str = Field(min_length=1)
    node_key: str = Field(min_length=1)
    difficulty: str = "beginner"
    knowledge_points: list[str] = Field(default_factory=list, max_length=24)
    weak_knowledge_points: list[str] = Field(default_factory=list, max_length=24)
    tutorial_title: str = Field(min_length=1)
    tutorial_summary: str = ""
    tutorial_knowledge_points: list[str] = Field(default_factory=list, max_length=24)
    tutorial_core_content: str = Field(min_length=1)


SlideLayoutType = Literal[
    "hero_cover",
    "roadmap_grid",
    "split_concept",
    "three_columns",
    "process_flow",
    "comparison_matrix",
    "bento_quad",
    "code_or_formula_spotlight",
    "summary_takeaways",
]


class ThemeTokens(PPTModel):
    """60-30-10 配色与字体主题 Token。"""

    palette_name: str = "ocean_editorial"
    bg_dark: str = "#0F172A"
    bg_light: str = "#F8FAFC"
    surface_card: str = "#FFFFFF"
    surface_dark_card: str = "#1E293B"
    accent_primary: str = "#2563EB"
    accent_secondary: str = "#0EA5E9"
    accent_soft: str = "#DBEAFE"
    text_primary: str = "#0F172A"
    text_muted: str = "#475569"
    text_on_dark: str = "#F8FAFC"
    border_subtle: str = "#CBD5E1"
    font_heading: str = "PingFang SC"
    font_body: str = "PingFang SC"
    font_mono: str = "Consolas"


PRESET_PALETTES: dict[str, ThemeTokens] = {
    "ocean_editorial": ThemeTokens(
        palette_name="ocean_editorial",
        bg_dark="#0F172A",
        bg_light="#F8FAFC",
        surface_card="#FFFFFF",
        surface_dark_card="#1E293B",
        accent_primary="#2563EB",
        accent_secondary="#0EA5E9",
        accent_soft="#DBEAFE",
        text_primary="#0F172A",
        text_muted="#475569",
        text_on_dark="#F8FAFC",
        border_subtle="#CBD5E1",
    ),
    "emerald_academy": ThemeTokens(
        palette_name="emerald_academy",
        bg_dark="#062C24",
        bg_light="#F4FBF8",
        surface_card="#FFFFFF",
        surface_dark_card="#0F3D33",
        accent_primary="#0D9488",
        accent_secondary="#10B981",
        accent_soft="#CCFBF1",
        text_primary="#0F2924",
        text_muted="#4B6B64",
        text_on_dark="#F0FDF4",
        border_subtle="#B8E1D6",
    ),
    "warm_terracotta": ThemeTokens(
        palette_name="warm_terracotta",
        bg_dark="#1C1917",
        bg_light="#FAF8F5",
        surface_card="#FFFFFF",
        surface_dark_card="#292524",
        accent_primary="#D97706",
        accent_secondary="#EA580C",
        accent_soft="#FEF3C7",
        text_primary="#1C1917",
        text_muted="#57534E",
        text_on_dark="#FAFAF9",
        border_subtle="#E7E5E4",
    ),
}


class SlideSpec(PPTModel):
    """DESIGN_PLAN.json 中单张幻灯片的规格定义。"""

    id: str = Field(pattern=r"^s[0-9]{2}$", description="幻灯片编号，如 s01, s02")
    layout: SlideLayoutType = Field(description="本页布局原型，相邻两页不得重复")
    chapter_badge: str = Field(default="MODULE · 核心教学", min_length=2)
    title: str = Field(min_length=2, description="本页主标题")
    subtitle: str = Field(default="", description="副标题或引导问题")
    core_claim: str = Field(min_length=2, description="本页核心论断或教学目标")
    key_points: list[str] = Field(
        default_factory=list,
        min_length=2,
        max_length=4,
        description="2~4 条结构化卡片要点，每条建议使用 '小标题：具体阐述' 格式",
    )
    takeaway: str = Field(default="", description="底部总结条一句话结论")
    speaker_notes: str = Field(default="", description="演讲者备注")
    code_or_formula: str = Field(default="", description="可选代码或核心公式片段")


class DeckDesignPlan(PPTModel):
    """PPT 主规划器产出的完整课件蓝图 (DESIGN_PLAN.json)。"""

    title: str = Field(min_length=2)
    subtitle: str = Field(default="")
    palette_name: str = Field(default="ocean_editorial")
    theme: ThemeTokens = Field(default_factory=ThemeTokens)
    slides: list[SlideSpec] = Field(min_length=5, max_length=14)

    @model_validator(mode="after")
    def validate_plan(self) -> "DeckDesignPlan":
        if self.palette_name in PRESET_PALETTES:
            self.theme = PRESET_PALETTES[self.palette_name]
        # 自动规范化 slide id 为 s01..sNN
        for idx, slide in enumerate(self.slides, start=1):
            slide.id = f"s{idx:02d}"
        # 校验相邻两页不能使用完全相同的 layout（若相同则自动轮换修补，避免死锁）
        fallback_layouts: list[SlideLayoutType] = [
            "split_concept",
            "three_columns",
            "process_flow",
            "comparison_matrix",
            "bento_quad",
        ]
        for idx in range(1, len(self.slides)):
            if self.slides[idx].layout == self.slides[idx - 1].layout:
                for candidate in fallback_layouts:
                    if candidate != self.slides[idx - 1].layout:
                        self.slides[idx].layout = candidate
                        break
        return self


class PPTArtifact(PPTModel):
    """PPT 生成完成后的产物引用。"""

    title: str = Field(min_length=1)
    path: Path
    pptx_path: Path | None = None
    generated_at: datetime
    slide_count: int
    html_url: str = ""
    pptx_url: str = ""


class PPTGenerationError(RuntimeError):
    """PPT 生成阶段结构化异常。"""

    def __init__(self, message: str, *, stage: str = "ppt-agent") -> None:
        super().__init__(message)
        self.stage = stage


__all__ = [
    "DeckDesignPlan",
    "PRESET_PALETTES",
    "PPTArtifact",
    "PPTGenerationError",
    "PPTModel",
    "PPTPreferences",
    "PPTSource",
    "PathPPT",
    "ResourcePPT",
    "SlideLayoutType",
    "SlideSpec",
    "ThemeTokens",
]
