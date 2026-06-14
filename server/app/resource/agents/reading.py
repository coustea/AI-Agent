"""阅读智能体 — 生成拓展阅读材料。"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field

from app.config import INFERENCE_TEMPERATURE
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.infra.prompts import prompts
from app.resource.schemas import WorkerResult, WorkerState

logger = get_logger(__name__)


class ReadingResource(BaseModel):
    id: str = Field(description="资源编号，如 R1")
    type: str = Field(description="资源类型，如 book/paper/article/documentation/practice_project")
    title: str = Field(description="资源标题")
    authors: list[str] = Field(default_factory=list)
    url: str = ""
    language: str = "中文"
    difficulty: str = "medium"
    suitable_for: str = ""
    related_knowledge_points: list[str] = Field(default_factory=list)
    description: str = ""
    recommend_reason: str = ""
    how_to_use: str = ""
    estimated_time: str = ""
    note: str = ""


class ReadingPathStep(BaseModel):
    step: int
    title: str
    description: str = ""
    resource_ids: list[str] = Field(default_factory=list)
    goal: str = ""


class ReadingPayload(BaseModel):
    title: str = "拓展阅读推荐"
    summary: str = ""
    resources: list[ReadingResource] = Field(default_factory=list)
    learning_path: list[ReadingPathStep] = Field(default_factory=list)
    follow_up_suggestions: list[str] = Field(default_factory=list)


@register_agent
class ReadingAgent(BaseResourceAgent):
    """基于教学蓝图生成拓展阅读材料。"""

    agent_id = "reading"
    agent_name = "阅读生成"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

    async def _execute(self, input_text: str, state: WorkerState) -> WorkerResult:
        config = state.agent_config
        reading_depth = config.get("reading_depth") or config.get("reading_type") or "course_extended"
        max_items = config.get("max_items") or 5
        language_preference = config.get("language_preference") or "chinese"
        if config:
            cfg = ["## 阅读配置"]
            cfg.append(f"- reading_depth: {reading_depth}")
            cfg.append(f"- max_items: {max_items}")
            cfg.append(f"- language_preference: {language_preference}")
            input_text += f"\n\n{chr(10).join(cfg)}"
        input_text += "\n\n请生成拓展阅读材料，只输出 JSON 对象。"

        if self.emitter:
            await self.emitter.emit_agent(
                self.agent_id, status="running",
                message="正在构建拓展阅读提示词",
                progress=25,
            )

        prompt = prompts.get("resource").get("reading")
        logger.info("Agent[reading] 步骤: 调用 LLM 生成拓展阅读, depth=%s max_items=%s", reading_depth, max_items)
        result = await self.llm.ainvoke_json(
            ReadingPayload,
            f"{prompt}\n\n{input_text}",
            temperature=INFERENCE_TEMPERATURE,
            function_name="generate_reading_resources",
            function_description="生成拓展阅读推荐资源",
        )

        if self.emitter:
            await self.emitter.emit_agent(
                self.agent_id, status="running",
                message="阅读列表已生成，正在解析资源结构",
                progress=85,
            )

        reading_data = result.model_dump(mode="json")
        content = json.dumps(reading_data, ensure_ascii=False, indent=2)
        logger.info(
            "Agent[reading] 步骤: 阅读资源解析完成, resources=%d path_steps=%d",
            len(reading_data.get("resources", [])),
            len(reading_data.get("learning_path", [])),
        )

        return WorkerResult(
            success=True,
            content=content,
            file_type="json",
            title=reading_data.get("title") or f"{state.learning_need[:32]} - 拓展阅读",
            summary=reading_data.get("summary") or "生成拓展阅读材料",
            summary_data={
                "resource_count": len(reading_data.get("resources", [])),
                "reading_depth": reading_depth,
                "language_preference": language_preference,
            },
            metadata={
                "agent_id": "reading",
                "reading_depth": reading_depth,
                "max_items": max_items,
                "language_preference": language_preference,
            },
        )
