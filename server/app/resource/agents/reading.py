"""阅读智能体 — 检索真实网页资源后生成可验证的阅读推荐。"""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, Field, field_validator

from app.infra.llm import get_llm
from app.infra.logging import get_logger
from app.infra.prompts import prompts
from app.resource.agents.base import BaseResourceAgent, register_agent
from app.resource.agents.common import build_path_context, build_resource_context
from app.resource.research import research_web
from app.resource.schemas import AgentResult, ResourceInput

if TYPE_CHECKING:
    from app.path.schemas import PathResourceRequest
    from app.shared.research.schemas import ResearchEvent, ResearchSourceItem

logger = get_logger(__name__)


class ReadingResource(BaseModel):
    """一个经过搜索结果 URL 校验的阅读资源。"""

    id: str = Field(description="资源编号，如 R1")
    type: str = Field(description="资源类型，如 book/paper/article/documentation/practice_project")
    title: str = Field(description="资源标题")
    authors: list[str] = Field(default_factory=list)
    url: str = Field(description="必须来自本次网页检索结果的 http/https URL")
    language: str = "中文"
    difficulty: str = "medium"
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
    """唯一保留网页检索的 Worker：它需要真实 URL，而非知识补全。"""

    agent_id = "reading"
    agent_name = "拓展阅读"

    def __init__(self, emitter=None):
        super().__init__(emitter=emitter)
        self.llm = get_llm()

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
        result = await self._generate_reading(
            input_text="\n\n".join(build_path_context(request)),
            title_prefix=request.node_title[:80],
            config={},
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
        """一次检索、一次生成；输出的每个 URL 必须可追溯到检索结果。"""
        started = time.perf_counter()
        coverage = config.get("coverage") or "extended"
        max_items = max(1, int(config.get("max_items", 5)))
        language_preference = config.get("language_preference") or "chinese"
        query = self._build_search_query(title_prefix, language_preference)

        logger.info("Agent[%s] 开始检索: query=%s", self.agent_id, query)
        await self.emitter.send(self.agent_id, "running", "正在检索真实阅读链接...", 25)
        try:
            report = await research_web(
                query,
                objective="为阅读推荐获取真实、可访问的权威学习资源 URL",
                event_handler=self._handle_research_event,
            )
        except Exception as exc:
            logger.warning("Agent[%s] 阅读链接检索失败: %s", self.agent_id, exc)
            return self._search_failure(title_prefix, [exc])
        sources = self._usable_sources(report.sources)
        if not sources:
            return self._search_failure(title_prefix, report.errors)

        await self.emitter.send(self.agent_id, "running", "正在基于真实链接编排阅读路径...", 60)
        prompt = prompts.get("resource").get("reading")
        full_prompt = f"{prompt}\n\n{self._build_generation_input(input_text, sources, max_items, coverage)}"
        payload = await self.run_with_heartbeat(
            self.llm.ainvoke_json(ReadingPayload, full_prompt),
            messages=["正在筛选权威资料...", "正在补充阅读顺序与学习建议..."],
            interval_seconds=12.0,
            progress=70,
        )
        resources = self._verify_resources(payload.resources, sources, max_items)
        if not resources:
            return AgentResult(
                success=False,
                error="阅读推荐未引用本次检索到的真实 URL",
                title=f"{title_prefix} - 拓展阅读",
                summary="生成结果未通过真实链接校验",
                file_type="json",
                metadata={"agent_id": self.agent_id, "error_type": "unverified_url"},
            )

        content = json.dumps(
            [resource.model_dump(mode="json") for resource in resources],
            ensure_ascii=False,
            indent=2,
        )
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "Agent[%s] 生成完成: resources=%d sources=%d elapsed_ms=%d",
            self.agent_id,
            len(resources),
            len(sources),
            elapsed_ms,
        )
        return AgentResult(
            success=True,
            content=content,
            file_type="json",
            title=f"{title_prefix} - 拓展阅读",
            summary=f"生成 {len(resources)} 条真实链接的拓展阅读材料",
            metrics={
                "resource_count": len(resources),
                "verified_source_count": len(sources),
                "coverage": coverage,
                "language_preference": language_preference,
            },
            metadata={"agent_id": self.agent_id, "coverage": coverage},
        )

    async def _handle_research_event(self, event: "ResearchEvent") -> None:
        status = event.get("status", "running")
        action = event.get("action", "检索网页资料")
        tool_status = {"running": "running", "done": "completed", "failed": "failed"}.get(
            status,
            "running",
        )
        await self.emitter.send(
            self.agent_id,
            "running",
            f"正在{action}..." if status == "running" else f"{action}{'已完成' if status == 'done' else '未完成'}",
            data={
                "phase": "reading_research",
                "tool_name": event.get("tool_name"),
                "tool_status": tool_status,
            },
        )

    @staticmethod
    def _build_search_query(title_prefix: str, language_preference: str) -> str:
        language_hint = {
            "chinese": "中文",
            "english": "English",
            "both": "中文 English",
        }.get(language_preference, "")
        return f"{title_prefix} {language_hint} 官方文档 教程 学习资源".strip()

    @staticmethod
    def _usable_sources(sources: list["ResearchSourceItem"]) -> list["ResearchSourceItem"]:
        unique: list[ResearchSourceItem] = []
        seen_urls: set[str] = set()
        for source in sources:
            if not source.url or not source.url.startswith(("http://", "https://")):
                continue
            key = _normalized_url(source.url)
            if key and key not in seen_urls:
                seen_urls.add(key)
                unique.append(source)
        return unique[:12]

    @staticmethod
    def _build_generation_input(
        input_text: str,
        sources: list["ResearchSourceItem"],
        max_items: int,
        coverage: str,
    ) -> str:
        source_lines = []
        for index, source in enumerate(sources, 1):
            source_lines.extend([
                f"{index}. 标题：{source.title or '未命名资源'}",
                f"   URL：{source.url}",
                f"   摘要：{source.summary[:300]}",
            ])
        return "\n".join([
            input_text,
            "## 本次检索到的真实资源（唯一允许使用的 URL）",
            *source_lines,
            "## 生成硬性约束",
            f"- 最多输出 {max_items} 条资源，coverage={coverage}。",
            "- 每条 url 必须逐字复制自上面的 URL；不得编造、改写或补全 URL。",
            "- 只选择与学习目标相关、适合当前学习阶段的资源。",
            "- 若可选资源不足，少推荐也可以；不要以假链接凑数。",
        ])

    @staticmethod
    def _verify_resources(
        resources: list[ReadingResource],
        sources: list["ResearchSourceItem"],
        max_items: int,
    ) -> list[ReadingResource]:
        source_by_url = {_normalized_url(source.url): source for source in sources}
        verified: list[ReadingResource] = []
        seen_urls: set[str] = set()
        for resource in resources:
            key = _normalized_url(resource.url)
            source = source_by_url.get(key)
            if source is None or key in seen_urls:
                continue
            seen_urls.add(key)
            verified.append(resource.model_copy(update={"url": source.url, "title": source.title or resource.title}))
            if len(verified) >= max_items:
                break
        return verified

    def _search_failure(self, title_prefix: str, errors: list[Any]) -> AgentResult:
        logger.warning("Agent[%s] 未获取到真实阅读链接: errors=%d", self.agent_id, len(errors))
        return AgentResult(
            success=False,
            error="未检索到可验证的阅读资源链接",
            title=f"{title_prefix} - 拓展阅读",
            summary="真实链接检索失败",
            file_type="json",
            metadata={"agent_id": self.agent_id, "error_type": "empty_search_results"},
        )


def _normalized_url(url: str) -> str:
    """比较 URL 时忽略末尾斜杠和 fragment，保留真实输出中的原 URL。"""
    parsed = urlsplit(url.strip())
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, parsed.query, ""))
