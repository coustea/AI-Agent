"""
PPT 智能体 — 生成幻灯片内容 JSON 供前端渲染。
"""

from __future__ import annotations

import json
import time

from pydantic import BaseModel, Field, model_validator

from app.infra.llm import get_llm
from app.infra.logging import get_module_logger
from app.prompts import registry
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.agents.common import salvage_json_from_llm
from app.resource.events import AgentEventEmitter
from app.resource.schemas import WorkerResult, WorkerState

logger = get_module_logger("resource", sub="ppt")


class CoverData(BaseModel):
    main_title: str = Field(description="主标题")
    sub_title: str = Field(default="", description="副标题")
    lecturer: str = Field(default="", description="演讲者")


class AgendaData(BaseModel):
    model_config = {"populate_by_name": True}
    items: list[str] = Field(default_factory=list, alias="list", description="目录列表")


class BulletPointsData(BaseModel):
    title: str = Field(description="页面标题")
    points: list[str] = Field(default_factory=list, description="要点列表")


class GridCardItem(BaseModel):
    title: str = Field(description="卡片标题")
    desc: str = Field(description="卡片描述")


class GridCardsData(BaseModel):
    title: str = Field(description="页面标题")
    cards: list[GridCardItem] = Field(default_factory=list, description="卡片列表")


class ComparisonData(BaseModel):
    title: str = Field(description="页面标题")
    left_label: str = Field(default="", description="左侧标签")
    left_content: list[str] = Field(default_factory=list, description="左侧内容")
    right_label: str = Field(default="", description="右侧标签")
    right_content: list[str] = Field(default_factory=list, description="右侧内容")


class SlideMetadata(BaseModel):
    speaker_notes: str = Field(default="", description="演讲者备注")
    transition: str = Field(default="none", description="切换效果")
    background_override: str | None = Field(default=None, description="自定义背景色")


class SlideCover(BaseModel):
    layout: str = Field(default="cover", description="布局类型")
    data: CoverData = Field(description="封面数据")
    metadata: SlideMetadata = Field(default_factory=SlideMetadata)


class SlideAgenda(BaseModel):
    layout: str = Field(default="agenda", description="布局类型")
    data: AgendaData = Field(description="目录数据")
    metadata: SlideMetadata = Field(default_factory=SlideMetadata)


class SlideBulletPoints(BaseModel):
    layout: str = Field(default="bullet_points", description="布局类型")
    data: BulletPointsData = Field(description="要点数据")
    metadata: SlideMetadata = Field(default_factory=SlideMetadata)


class SlideGridCards(BaseModel):
    layout: str = Field(default="grid_cards", description="布局类型")
    data: GridCardsData = Field(description="卡片数据")
    metadata: SlideMetadata = Field(default_factory=SlideMetadata)


class SlideComparison(BaseModel):
    layout: str = Field(default="comparison", description="布局类型")
    data: ComparisonData = Field(description="对比数据")
    metadata: SlideMetadata = Field(default_factory=SlideMetadata)


PPTSlide = SlideCover | SlideAgenda | SlideBulletPoints | SlideGridCards | SlideComparison


class PPTConfig(BaseModel):
    template_id: str = Field(default="theme-logic-blue", description="主题ID")
    topic: str = Field(default="", description="PPT主题")


class PptPayload(BaseModel):
    config: PPTConfig = Field(default_factory=PPTConfig, description="PPT配置")
    slides: list[PPTSlide] = Field(default_factory=list, description="幻灯片列表")

    @model_validator(mode="after")
    def validate_playable_layout(self) -> PptPayload:
        if len(self.slides) < 3:
            raise ValueError("PPT 至少需要封面、目录和一页正文")
        if self.slides[0].layout != "cover" or self.slides[1].layout != "agenda":
            raise ValueError("PPT 必须以 cover、agenda 开始")
        return self


@register_agent
class PptAgent(BaseResourceAgent):
    """基于教学蓝图生成 PPT 幻灯片内容。"""

    agent_id = "ppt"
    agent_name = "PPT生成"

    def __init__(self, emitter: AgentEventEmitter | None = None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def _execute(self, input_text: str, state: WorkerState) -> WorkerResult:
        start = time.perf_counter()
        logger.info("Agent[ppt] 启动: learning_need=%s", state.learning_need[:50])

        await self.emitter.emit_agent("ppt", status="running", message="正在准备PPT", progress=0)
        await self.emitter.emit_agent_action(
            "ppt", "outline", detail="正在规划幻灯片大纲",
            current_step=1, total_steps=4, step_label="规划大纲", progress=10,
        )

        prompt = registry.get("resource/ppt")
        full_prompt = f"{prompt}\n\n{input_text}\n\n请生成 PPT 内容，以 JSON 格式输出。"

        await self.emitter.emit_agent_action(
            "ppt", "generate", detail="正在生成幻灯片内容",
            current_step=2, total_steps=4, step_label="生成内容", progress=35,
        )

        try:
            result = await self.llm.ainvoke_json(
                PptPayload,
                full_prompt,
                temperature=0.3,
                function_name="generate_ppt",
                function_description="生成 PPT 幻灯片内容",
            )
            ppt_data = result.model_dump(mode="json", by_alias=True)
            content = json.dumps(ppt_data, ensure_ascii=False, indent=2)

            elapsed = time.perf_counter() - start
            logger.debug("Agent[ppt] LLM 调用完成: %.2fs", elapsed)
        except Exception as exc:
            logger.warning("Agent[ppt] 结构化输出失败，尝试 fallback: %s", exc)

            await self.emitter.emit_agent_action(
                "ppt", "fallback", detail="正在重新整理PPT格式",
                current_step=3, total_steps=4, step_label="格式整理", progress=55,
            )

            response = await self.llm.ainvoke(full_prompt, temperature=0.3)

            elapsed = time.perf_counter() - start
            logger.debug("Agent[ppt] LLM fallback 调用完成: %.2fs", elapsed)

            raw = response.content if hasattr(response, "content") else str(response)
            ppt_data = self._salvage_ppt_payload(raw)
            if ppt_data is None:
                elapsed = time.perf_counter() - start
                logger.warning("Agent[ppt] 失败: %.2fs, error=PPT JSON 解析失败", elapsed)
                return WorkerResult(success=False, error=f"PPT JSON 解析失败: {exc}")
            content = json.dumps(ppt_data, ensure_ascii=False, indent=2)

        slide_count = len(ppt_data.get("slides", []))
        requested_page_count = (state.agent_config or {}).get("page_count") or (state.agent_config or {}).get("slide_count") or 10
        if slide_count != requested_page_count:
            logger.warning("Agent[ppt] 失败: slide_count (%d) != requested_page_count (%d)", slide_count, requested_page_count)
            return WorkerResult(
                success=False,
                error=f"PPT 页面数量不符合配置: 期望 {requested_page_count} 页，实际 {slide_count} 页",
            )

        await self.emitter.emit_agent_action(
            "ppt", "done", detail=f"已生成 {slide_count} 页幻灯片",
            current_step=4, total_steps=4, step_label="生成完成", progress=100,
        )
        await self.emitter.emit_agent("ppt", status="success", message=f"已生成 {slide_count} 页幻灯片", progress=100)

        elapsed = time.perf_counter() - start
        logger.info("Agent[ppt] 完成: %.2fs", elapsed)

        return WorkerResult(
            success=True,
            content=content,
            file_type="json",
            title=f"{state.learning_need[:32]} - PPT",
            summary=f"生成 {slide_count} 页幻灯片",
            summary_data={"slide_count": slide_count},
            metadata={
                "engine": "ppt_json",
                "slide_count": slide_count,
                "agent_id": "ppt",
                "delivery_mode": (state.agent_config or {}).get("output_format") or "preview",
                "template_id": "theme-logic-blue",
                "page_count": requested_page_count,
                "difficulty": (state.agent_config or {}).get("difficulty") or "intermediate",
            },
        )

    def agent_input_parts(self, state: WorkerState) -> list[str]:
        config = state.agent_config or {}
        page_count = config.get("page_count") or config.get("slide_count") or 10
        difficulty = config.get("difficulty") or "intermediate"

        cfg_lines = ["## PPT配置"]
        cfg_lines.append(f"- 总页数必须严格等于 {page_count} 页")
        cfg_lines.append(f"- 仅允许使用 theme-logic-blue 模板")
        cfg_lines.append(f"- 在线预览格式 (output_format=preview)")
        cfg_lines.append(f"- 教学难度: {difficulty}")
        parts = ["\n".join(cfg_lines)]
        approved_sources = config.get("approved_sources")
        if isinstance(approved_sources, list) and approved_sources:
            parts.append("## 已通过审核的内容来源")
            parts.append(json.dumps(approved_sources, ensure_ascii=False, indent=2))
            parts.append("PPT 的核心事实、概念解释和案例应基于以上已审核来源展开，不要引入无依据的新结论。")
        parts.append("请生成 PPT 幻灯片内容。")
        return parts

    def _salvage_ppt_payload(self, raw: str) -> dict | None:
        """Try to parse raw LLM output as PPT JSON; convert old format if needed."""
        data = salvage_json_from_llm(raw, require_key="slides")
        if data is None:
            return None

        # Already in PPTDocument format (has config + layout-based slides)
        if "config" in data and isinstance(data["config"], dict):
            return data

        # Convert old format {title, theme, slides: [{heading, bullets, notes}]}
        return self._convert_legacy_format(data)

    def _convert_legacy_format(self, data: dict) -> dict:
        """Convert old {title, theme, slides: [{heading, bullets, notes}]} to PPTDocument format."""
        title = data.get("title", "")
        slides = data.get("slides", [])
        converted_slides = []
        for i, slide in enumerate(slides):
            heading = slide.get("heading", "")
            bullets = slide.get("bullets", [])
            notes = slide.get("notes", "")

            if i == 0:
                converted_slides.append({
                    "layout": "cover",
                    "data": {"main_title": heading or title, "sub_title": "", "lecturer": ""},
                    "metadata": {"speaker_notes": notes, "transition": "none"},
                })
            elif i == 1:
                converted_slides.append({
                    "layout": "agenda",
                    "data": {"list": bullets or [heading]},
                    "metadata": {"speaker_notes": notes, "transition": "none"},
                })
            else:
                converted_slides.append({
                    "layout": "bullet_points",
                    "data": {"title": heading, "points": bullets},
                    "metadata": {"speaker_notes": notes, "transition": "none"},
                })

        return {
            "config": {"template_id": "theme-logic-blue", "topic": title},
            "slides": converted_slides,
        }
