"""阅读智能体 — 生成结构化的拓展阅读推荐。"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.infra.llm import LLM
from app.infra.logging import get_logger
from app.infra.prompts import prompts
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.agents.common import build_path_context, build_resource_context
from app.resource.schemas import AgentResult, ResourceInput

if TYPE_CHECKING:
    from app.path.schemas import PathResourceRequest

logger = get_logger(__name__)


class ReadingResource(BaseModel):
    """单条拓展阅读推荐资源。"""

    id: str = Field(description="资源编号，如 R1")
    type: Literal["book", "paper", "article", "documentation", "practice_project"] = Field(
        description="资源类型"
    )
    title: str = Field(description="资源标题")
    authors: list[str] = Field(default_factory=list)
    url: str = Field(description="真实或权威官方文档 http/https URL")
    language: Literal["中文", "英文"] = "中文"
    difficulty: Literal["basic", "medium", "advanced"] = "medium"
    suitable_for: str = ""
    related_knowledge_points: list[str] = Field(default_factory=list)
    description: str = ""
    recommend_reason: str = ""
    how_to_use: str = ""
    estimated_time: str = ""
    note: str = ""

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.startswith(("http://", "https://")):
            raise ValueError("url must use the http or https scheme")
        return normalized


class ReadingPayload(BaseModel):
    """阅读 Agent 的结构化输出。"""

    resources: list[ReadingResource] = Field(min_length=1)


@register_agent
class ReadingAgent(BaseResourceAgent):
    """拓展阅读推荐智能体。"""

    agent_id = "reading"
    agent_name = "拓展阅读"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self.llm = LLM(temperature=0.1)

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        return await self._generate_reading(
            input_text="\n\n".join(build_resource_context(input_data)),
            title_prefix=input_data.learning_need[:80],
            config=input_data.agent_config,
        )

    async def generate_for_path(self, request: "PathResourceRequest") -> AgentResult:
        if request.tutorial is None:
            return AgentResult(
                success=False,
                title="拓展阅读生成失败",
                file_type="json",
                error="缺少教程内容",
            )
        config: dict[str, Any] = {}
        if request.language_preference:
            config["language_preference"] = request.language_preference
        result = await self._generate_reading(
            input_text="\n\n".join(build_path_context(request)),
            title_prefix=request.node_title[:80],
            config=config,
        )
        result.metadata["node_id"] = request.node_id
        return result

    async def _generate_reading(
        self,
        *,
        input_text: str,
        title_prefix: str,
        config: dict[str, Any],
    ) -> AgentResult:
        started = time.perf_counter()
        coverage = config.get("coverage") or "extended"
        max_items = max(1, int(config.get("max_items", 5)))
        language_preference = config.get("language_preference") or "chinese"

        await self.emitter.send(self.agent_id, "running", "正在编排拓展阅读推荐路径...", 50)
        prompt = prompts.get("resource").get("reading")
        full_prompt = (
            f"{prompt}\n\n{input_text}\n\n"
            f"## 生成约束\n- 最多输出 {max_items} 条经典权威资源，coverage={coverage}。\n"
            "- 每条资源必须提供有效的 http:// 或 https:// 官方网站/文档链接。"
        )
        payload = await self.run_with_heartbeat(
            self.llm.json(ReadingPayload, full_prompt),
            messages=["正在筛选权威资料...", "正在补充阅读顺序与学习建议..."],
            interval_seconds=12.0,
            progress=70,
        )
        resources = payload.resources[:max_items]
        content = json.dumps(
            [resource.model_dump(mode="json") for resource in resources],
            ensure_ascii=False,
            indent=2,
        )
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "Agent[%s] 生成完成: resources=%d elapsed_ms=%d",
            self.agent_id,
            len(resources),
            elapsed_ms,
        )
        return AgentResult(
            success=True,
            content=content,
            file_type="json",
            title=f"{title_prefix} - 拓展阅读",
            summary=f"生成 {len(resources)} 条拓展阅读材料",
            metrics={
                "resource_count": len(resources),
                "coverage": coverage,
                "language_preference": language_preference,
            },
            metadata={"agent_id": self.agent_id, "coverage": coverage},
        )
