"""PPT 智能体 — 生成前端 PPT 播放器可直接渲染的结构化文档。"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.infra.llm import get_llm
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.agents.common import build_worker_base_context
from app.infra.prompts import prompts
from app.resource.schemas import WorkerResult, WorkerState


ThemeType = Literal["theme-logic-blue"]
LayoutType = Literal["cover", "agenda", "bullet_points", "grid_cards", "comparison"]


class PptConfig(BaseModel):
    template_id: ThemeType = "theme-logic-blue"
    topic: str
    author: str | None = None
    date: str | None = None


class PptSlide(BaseModel):
    layout: LayoutType
    data: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)


class PptPayload(BaseModel):
    config: PptConfig
    slides: list[PptSlide] = Field(default_factory=list)

    @field_validator("slides")
    @classmethod
    def validate_slide_layout_order(cls, slides: list[PptSlide]) -> list[PptSlide]:
        if len(slides) < 3:
            raise ValueError("PPT 至少需要 cover、agenda 和 1 页正文")
        if slides[0].layout != "cover" or slides[1].layout != "agenda":
            raise ValueError("PPT slides 必须以 cover 和 agenda 开头")
        for index, slide in enumerate(slides[2:], start=3):
            if slide.layout in {"cover", "agenda"}:
                raise ValueError(f"第 {index} 页不能再次使用 cover 或 agenda")
        return slides

    @model_validator(mode="after")
    def validate_template(self) -> "PptPayload":
        self.config.template_id = "theme-logic-blue"
        return self


@register_agent
class PptAgent(BaseResourceAgent):
    """基于教学蓝图生成在线预览 PPT 文档。"""

    agent_id = "ppt"
    agent_name = "PPT 生成"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    def agent_input_parts(self, state: WorkerState) -> list[str]:
        parts = build_worker_base_context(state)
        config = state.agent_config or {}
        page_count = int(config.get("page_count") or config.get("slide_count") or 6)
        difficulty = config.get("difficulty") or "intermediate"
        approved_sources = config.get("approved_sources") or []

        ppt_config = [
            "## PPT 生成配置",
            f"- page_count: {page_count}",
            f"- 总页数必须严格等于 {page_count} 页",
            "- template_id: theme-logic-blue",
            "- 仅允许使用 theme-logic-blue",
            "- delivery_mode: 在线预览",
            f"- difficulty: {difficulty}",
        ]
        parts.append("\n".join(ppt_config))
        if approved_sources:
            parts.append(f"## 已通过审核的事实来源\n{json.dumps(approved_sources, ensure_ascii=False, indent=2)}")
        return parts

    async def run(self, state: WorkerState) -> WorkerResult:
        if self.emitter:
            await self.emitter.emit_agent(self.agent_id, status="running", message="正在生成在线预览 PPT", progress=10)

        input_text = "\n\n".join(self.agent_input_parts(state))

        if self.emitter:
            await self.emitter.emit_agent(
                self.agent_id, status="running",
                message="正在构建 PPT 结构化提示词",
                progress=25,
            )

        try:
            result = await self._execute(input_text, state)
        except Exception as exc:
            if self.emitter:
                await self.emitter.emit_agent(self.agent_id, status="failed", message=f"PPT 生成异常: {exc}", progress=0)
            raise

        if self.emitter:
            await self.emitter.emit_agent(
                self.agent_id,
                status="finished" if result.success else "failed",
                message=result.summary if result.success else (result.error or "PPT 生成失败"),
                progress=100 if result.success else 0,
            )
        return result

    async def _execute(self, input_text: str, state: WorkerState) -> WorkerResult:
        config = state.agent_config or {}
        page_count = int(config.get("page_count") or config.get("slide_count") or 6)
        difficulty = config.get("difficulty") or "intermediate"

        prompt = prompts.get("resource").get("ppt")
        result = await self.llm.ainvoke_json(
            PptPayload,
            f"{prompt}\n\n{input_text}",
            temperature=0.3,
            function_name="generate_ppt",
            function_description="生成前端 PPT 播放器可渲染的结构化文档",
        )
        ppt_data = result.model_dump(mode="json")
        slides = ppt_data.get("slides", [])
        actual_count = len(slides)
        if actual_count != page_count:
            return WorkerResult(
                success=False,
                content="",
                file_type="json",
                title=f"{state.learning_need[:32]} - PPT",
                summary="PPT 页数校验失败",
                error=f"PPT 页数不匹配: 期望 {page_count} 页，实际 {actual_count} 页",
                metadata={
                    "agent_id": "ppt",
                    "delivery_mode": "preview",
                    "template_id": "theme-logic-blue",
                    "page_count": actual_count,
                    "expected_page_count": page_count,
                    "difficulty": difficulty,
                },
            )

        content = json.dumps(ppt_data, ensure_ascii=False, indent=2)
        return WorkerResult(
            success=True,
            content=content,
            file_type="json",
            title=f"{state.learning_need[:32]} - PPT",
            summary=f"生成 {actual_count} 页在线预览 PPT",
            summary_data={"page_count": actual_count},
            metadata={
                "engine": "ppt_json",
                "agent_id": "ppt",
                "delivery_mode": "preview",
                "template_id": "theme-logic-blue",
                "page_count": actual_count,
                "difficulty": difficulty,
            },
        )
