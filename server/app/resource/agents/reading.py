"""阅读智能体 — 基于教学蓝图生成拓展阅读材料（JSON 结构化输出）。"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field

from app.config import INFERENCE_TEMPERATURE
from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.agents.common import (
    build_basic_handoff,
    build_node_context,
    build_resource_context,
    assigned_outline_ids,
)
from app.infra.prompts import prompts
from app.resource.schemas import AgentResult, NodeInput, ResourceInput

logger = get_logger(__name__)


class ReadingResource(BaseModel):
    """单个阅读资源：书籍/论文/文章/文档/实践项目。"""
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
    """阅读路径中的一个步骤。"""
    step: int
    title: str
    description: str = ""
    resource_ids: list[str] = Field(default_factory=list)
    goal: str = ""


class ReadingPayload(BaseModel):
    """LLM 结构化输出模型：完整拓展阅读推荐。"""
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

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        parts = build_resource_context(input_data)
        input_text = "\n\n".join(parts)
        config = {
            **input_data.agent_config,
            "_teaching_plan": input_data.teaching_plan,
        }
        result = await self._generate_reading(
            input_text=input_text,
            title_prefix=input_data.learning_need[:32],
            config=config,
        )
        try:
            reading_data = json.loads(result.content)
            resource_titles = [
                item.get("title")
                for item in reading_data.get("resources", [])
                if isinstance(item, dict) and item.get("title")
            ]
        except Exception:
            resource_titles = []
        outline_ids = assigned_outline_ids(input_data.teaching_plan, "reading")
        handoff = build_basic_handoff(
            source_agent="reading",
            title=result.title,
            summary=result.summary,
            teaching_plan=input_data.teaching_plan,
            covered_outline_ids=outline_ids,
            examples=resource_titles[:6],
        )
        result.downstream_context = handoff
        await self.emit_finish(result)
        return result

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        parts = build_node_context(input_data)
        input_text = "\n\n".join(parts)
        result = await self._generate_reading(
            input_text=input_text,
            title_prefix=input_data.node_title,
            config=input_data.agent_config,
        )
        result.metadata["path_id"] = input_data.path_id
        result.metadata["node_id"] = input_data.node_id
        await self.emit_finish(result)
        return result

    async def _generate_reading(
        self,
        *,
        input_text: str,
        title_prefix: str,
        config: dict,
    ) -> AgentResult:
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

        await self.emit_start("正在构建拓展阅读提示词", progress=25)

        prompt = prompts.get("resource").get("reading")
        logger.info("Agent[reading] 步骤: 调用 LLM 生成拓展阅读, depth=%s max_items=%s", reading_depth, max_items)
        result = await self.llm.ainvoke_json(
            ReadingPayload,
            f"{prompt}\n\n{input_text}",
            temperature=INFERENCE_TEMPERATURE,
            function_name="generate_reading_resources",
            function_description="生成拓展阅读推荐资源",
        )

        reading_data = result.model_dump(mode="json")
        content = json.dumps(reading_data, ensure_ascii=False, indent=2)
        logger.info(
            "Agent[reading] 步骤: 阅读资源解析完成, resources=%d path_steps=%d",
            len(reading_data.get("resources", [])),
            len(reading_data.get("learning_path", [])),
        )

        return AgentResult(
            success=True,
            content=content,
            file_type="json",
            title=reading_data.get("title") or f"{title_prefix} - 拓展阅读",
            summary=reading_data.get("summary") or "生成拓展阅读材料",
            metrics={
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
