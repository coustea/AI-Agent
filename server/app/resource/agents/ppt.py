"""
PPT文稿智能体 — 生成PPT文稿内容。
"""

from __future__ import annotations

import json
from typing import Literal, Union, List, Optional
from pydantic import BaseModel, Field, model_validator

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.prompts import registry
from app.resource.events import AgentEventEmitter
from app.resource.schemas import WorkerResult, WorkerState
from app.resource.utils import format_learner_profile_for_prompt

logger = get_logger(__name__)

# --- Pydantic Schemas for PPT ---

class PPTConfig(BaseModel):
    template_id: Literal["theme-logic-blue"] = Field(
        default="theme-logic-blue", description="PPT的主题风格"
    )
    topic: str = Field(description="PPT的主题或核心标题")
    author: Optional[str] = Field(default=None, description="作者或演讲者名称")
    date: Optional[str] = Field(default=None, description="日期，例如 '2023-10-01'")

class SlideMetadata(BaseModel):
    speaker_notes: Optional[str] = Field(default=None, description="演讲者备注或逐字稿")
    transition: Optional[Literal["fade", "slide", "zoom", "none"]] = Field(
        default=None, description="切换动画"
    )
    background_override: Optional[str] = Field(default=None, description="自定义背景色，如 '#FFFFFF'")

class CoverData(BaseModel):
    main_title: str = Field(description="主标题")
    sub_title: Optional[str] = Field(default=None, description="副标题")
    lecturer: Optional[str] = Field(default=None, description="演讲者名称")

class SlideCover(BaseModel):
    layout: Literal["cover"]
    metadata: Optional[SlideMetadata] = None
    data: CoverData

class AgendaData(BaseModel):
    list: List[str] = Field(description="目录列表项目")

class SlideAgenda(BaseModel):
    layout: Literal["agenda"]
    metadata: Optional[SlideMetadata] = None
    data: AgendaData

class BulletPointsData(BaseModel):
    title: str = Field(description="本页标题")
    points: List[str] = Field(description="要点列表，每句话应简短精炼")

class SlideBulletPoints(BaseModel):
    layout: Literal["bullet_points"]
    metadata: Optional[SlideMetadata] = None
    data: BulletPointsData

class GridCardItem(BaseModel):
    title: str = Field(description="卡片标题")
    desc: str = Field(description="卡片简短描述")

class GridCardsData(BaseModel):
    title: str = Field(description="本页标题")
    cards: List[GridCardItem] = Field(description="网格卡片内容")

class SlideGridCards(BaseModel):
    layout: Literal["grid_cards"]
    metadata: Optional[SlideMetadata] = None
    data: GridCardsData

class ComparisonData(BaseModel):
    title: str = Field(description="本页标题")
    left_label: str = Field(description="左侧对比项标签，例如 '旧方案'")
    left_content: List[str] = Field(description="左侧特性或要点")
    right_label: str = Field(description="右侧对比项标签，例如 '新方案'")
    right_content: List[str] = Field(description="右侧特性或要点")

class SlideComparison(BaseModel):
    layout: Literal["comparison"]
    metadata: Optional[SlideMetadata] = None
    data: ComparisonData

PPTSlide = Union[SlideCover, SlideAgenda, SlideBulletPoints, SlideGridCards, SlideComparison]

class PPTDocument(BaseModel):
    config: PPTConfig
    slides: List[PPTSlide] = Field(description="幻灯片页面列表。第一页必须是cover，第二页必须是agenda")

    @model_validator(mode="after")
    def validate_playable_layout(self) -> "PPTDocument":
        """Reject decks that the online player cannot present coherently."""
        if len(self.slides) < 3:
            raise ValueError("PPT 至少需要 cover、agenda 和一页正文")
        if not isinstance(self.slides[0], SlideCover) or not isinstance(self.slides[1], SlideAgenda):
            raise ValueError("PPT 页面顺序必须以 cover、agenda 开始")
        if any(isinstance(slide, (SlideCover, SlideAgenda)) for slide in self.slides[2:]):
            raise ValueError("PPT 正文中不能重复出现 cover 或 agenda")
        return self

# --- Agent Implementation ---

class PptAgent:
    """PPT文稿生成 Agent"""

    def __init__(self, emitter: AgentEventEmitter):
        self.emitter = emitter
        self.llm = get_llm()

    async def run(self, state: WorkerState) -> WorkerResult:
        await self.emitter.emit_agent("ppt", status="running", message="正在准备演示文稿", progress=0)
        await self.emitter.emit_agent_action(
            "ppt", "outline", detail="正在构思演示大纲",
            current_step=1, total_steps=4, step_label="构思大纲", progress=10,
        )

        prompt = registry.get("resource/ppt")
        input_text = self._build_input(state)
        full_prompt = f"{prompt}\n\n{input_text}"
        config = state.agent_config or {}
        template_id = config.get("template_id", "theme-logic-blue")
        requested_page_count = int(config.get("page_count", 6))
        difficulty = config.get("difficulty", "intermediate")
        delivery_mode = config.get("output_format", "preview")

        await self.emitter.emit_agent_action(
            "ppt", "compose", detail="正在编排幻灯片内容",
            current_step=2, total_steps=4, step_label="编排内容", progress=35,
        )

        logger.info("[PptAgent] 开始调用大语言模型生成结构化 PPT")
        try:
            ppt_doc: PPTDocument = await self.llm.ainvoke_json(PPTDocument, full_prompt)

            if len(ppt_doc.slides) != requested_page_count:
                raise ValueError(
                    f"PPT 页面数量不符合配置: 期望 {requested_page_count} 页，实际 {len(ppt_doc.slides)} 页"
                )

            # 转成符合前端预期的纯字典
            content_dict = ppt_doc.model_dump(exclude_none=True)
            content_json = json.dumps(content_dict, ensure_ascii=False)

            slide_titles = []
            for slide in ppt_doc.slides:
                if hasattr(slide.data, "title"):
                    slide_titles.append(slide.data.title)
                elif hasattr(slide.data, "main_title"):
                    slide_titles.append(slide.data.main_title)

            await self.emitter.emit_agent_action(
                "ppt", "render", detail="正在渲染演示文稿",
                current_step=3, total_steps=4, step_label="渲染文稿", progress=65,
            )

        except Exception as exc:
            logger.warning("[PptAgent] LLM 生成 PPT 失败: %s", exc)
            return WorkerResult(
                success=False,
                error=f"PPT 结构化生成失败: {exc}",
            )

        await self.emitter.emit_agent_action(
            "ppt", "done", detail="演示文稿生成完成",
            current_step=4, total_steps=4, step_label="生成完成", progress=100,
        )
        await self.emitter.emit_agent("ppt", status="success", message="演示文稿生成完成", progress=100)
        return WorkerResult(
            success=True,
            content=content_json,
            file_type="json",
            title=f"{ppt_doc.config.topic} - PPT",
            summary="已生成可演示的幻灯片结构",
            metadata={
                "engine": "ppt_json",
                "agent_id": "ppt",
                "delivery_mode": delivery_mode,
                "template_id": template_id,
                "page_count": requested_page_count,
                "difficulty": difficulty,
                "slide_count": len(ppt_doc.slides),
                "slide_titles": slide_titles
            },
        )

    def _build_input(self, state: WorkerState) -> str:
        parts = [f"## 学习需求\n{state.learning_need}"]
        config = state.agent_config or {}
        template_id = config.get("template_id", "theme-logic-blue")
        page_count = config.get("page_count", 6)
        difficulty = config.get("difficulty", "intermediate")
        output_format = config.get("output_format", "preview")
        parts.append(
            "\n".join(
                [
                    "## PPT 生成配置",
                    f"- template_id: {template_id}",
                    f"- page_count: {page_count}",
                    f"- difficulty: {difficulty}",
                    f"- output_format: {output_format}",
                    f"- 总页数必须严格等于 {page_count} 页（包含封面与目录）",
                    f"- 仅允许使用 {template_id} 主题及其可渲染布局",
                    f"- 内容难度须匹配 {difficulty} 学习者",
                    "- 交付方式为在线预览 JSON，不生成 PPTX 文件",
                ]
            )
        )

        profile_text = format_learner_profile_for_prompt(state.profile)
        if profile_text:
            parts.append(f"## 学习者画像摘要\n{profile_text}")

        if state.blueprint:
            parts.append(f"## 教学蓝图\n{state.blueprint.model_dump_json(indent=2)}")

        if state.instruction:
            lines = [f"## 规划师指令\n- 重点: {state.instruction.focus}"]
            for c in state.instruction.constraints:
                lines.append(f"- 约束: {c}")
            parts.append("\n".join(lines))

        return "\n\n".join(parts)
