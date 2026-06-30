from __future__ import annotations

from typing import Any, Dict, List, Literal
from pydantic import BaseModel, Field


class DeckBrief(BaseModel):
    purpose: str = Field(description="演示的目的与核心意图")
    audience: str = Field(description="受众类型与背景知识水平")
    density: Literal["speaker_led", "reading_first"] = Field(description="内容密度，演讲者引导或阅读优先")
    target_slide_count: int = Field(gt=0, description="目标幻灯片页数")
    narrative: str = Field(description="叙事大纲逻辑脉络描述")
    required_points: List[str] = Field(default_factory=list, description="必须包含的关键知识点")
    language: str = Field(default="zh-CN", description="语言代码")
    mood: str = Field(description="整体视觉和情感基调描述")


class StyleDecision(BaseModel):
    name: str = Field(description="风格名称")
    source: Literal["preset", "bold_template", "custom"] = Field(description="风格来源")
    rationale: str = Field(description="风格选择的合理性分析")
    design_recipe: Dict[str, Any] = Field(description="包含 CSS 变量、字体选择、间距等的字典")
    font_urls: List[str] = Field(default_factory=list, description="所用 Google Fonts 或 Fontshare 的 URL 列表")
    density: Literal["speaker_led", "reading_first"] = Field(description="内容密度，演讲者引导或阅读优先")


class VisualQAProblem(BaseModel):
    slide_index: int = Field(ge=0, description="出错的 slide 索引（0-indexed）")
    problem_type: Literal["overflow", "overlap", "empty", "script_error", "other"] = Field(description="问题类别：overflow, overlap, empty, script_error 等")
    element_summary: str = Field(description="涉及的 HTML 元素选择器或摘要描述")
    severity: Literal["warning", "critical"] = Field(description="严重等级")


class VisualAudit(BaseModel):
    passed: bool = Field(description="是否通过视觉 QA")
    problems: List[VisualQAProblem] = Field(default_factory=list, description="问题列表")
