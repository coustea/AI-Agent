"""Request-scoped tutor tools for the chat agent."""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.chat.memory.service import get_chat_memory_service
from app.chat.memory.types import LTM_CATEGORIES
from app.chat.schemas import TurnRequest
from app.chat.stages import AttachmentAnalyzer, WebSearchTool
from app.chat.tools.knowledge import aformat_knowledge_context
from app.evaluation.service import evaluation_service
from app.infra.database import session_scope
from app.infra.logging import get_logger
from app.profile.service import get_profile_service

logger = get_logger(__name__)

LongTermMemoryCategory = Literal[
    "learning_background",
    "long_term_goals",
    "learning_preferences",
    "stable_weaknesses",
    "interaction_rules",
    "effective_strategies",
    "corrections",
]


class GetLearnerProfileArgs(BaseModel):
    dimension: str | None = Field(default=None, description="Profile dimension to read, such as goals or preferences.")
    course_name: str | None = Field(default=None, description="Course-specific profile scope when available.")
    reason: str = Field(default="", description="Why the tutor needs the profile.")


class GetLongTermMemoryArgs(BaseModel):
    category: LongTermMemoryCategory | None = Field(default=None, description="Canonical long-term-memory category.")
    reason: str = Field(default="", description="Why the tutor needs durable memory.")


class SearchKnowledgeBaseArgs(BaseModel):
    query: str = Field(description="Search query for local course knowledge.")
    course_name: str | None = Field(default=None, description="Course name used as a retrieval hint.")
    top_k: int = Field(default=4, ge=1, le=8, description="Maximum number of snippets to return.")


class WebSearchArgs(BaseModel):
    query: str = Field(description="Fresh external-information query.")
    reason: str = Field(default="", description="Why current web information is needed.")


class GetRecentEvaluationArgs(BaseModel):
    limit: int = Field(default=5, ge=1, le=10, description="Number of recent evaluation events to summarize.")
    reason: str = Field(default="", description="Why recent evaluation data is needed.")


class AnalyzeAttachmentArgs(BaseModel):
    reason: str = Field(default="", description="What to inspect in the uploaded attachments.")


def _compact(text: str, *, limit: int = 3500) -> str:
    value = str(text or "").strip()
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


class TutorToolRegistry:
    """Build LangChain tools bound to one tutoring turn."""

    def __init__(
        self,
        *,
        request: TurnRequest,
        memory_service: Any | None = None,
        web_search: Any | None = None,
        attachment_analyzer: Any | None = None,
        profile_service: Any | None = None,
    ) -> None:
        self.request = request
        self.memory_service = memory_service or get_chat_memory_service()
        self.profile_service = profile_service or get_profile_service()
        self.web_search = web_search or WebSearchTool()
        self.attachment_analyzer = attachment_analyzer or AttachmentAnalyzer()
        self._tools: list[StructuredTool] | None = None

    def tools(self) -> list[StructuredTool]:
        if self._tools is None:
            self._tools = [
                StructuredTool.from_function(
                    coroutine=self._get_learner_profile,
                    name="get_learner_profile",
                    description="Read learner profile when personalization, goals, preferences, or background matter.",
                    args_schema=GetLearnerProfileArgs,
                ),
                StructuredTool.from_function(
                    coroutine=self._get_long_term_memory,
                    name="get_long_term_memory",
                    description="Read durable learning memory for previous goals, preferences, weaknesses, strategies, or corrections.",
                    args_schema=GetLongTermMemoryArgs,
                ),
                StructuredTool.from_function(
                    coroutine=self._search_knowledge_base,
                    name="search_knowledge_base",
                    description="Search local course knowledge base for definitions, concepts, textbook facts, and course material.",
                    args_schema=SearchKnowledgeBaseArgs,
                ),
                StructuredTool.from_function(
                    coroutine=self._web_search,
                    name="web_search",
                    description="Search the web only for current, recent, or explicitly requested external information.",
                    args_schema=WebSearchArgs,
                ),
                StructuredTool.from_function(
                    coroutine=self._get_recent_evaluation,
                    name="get_recent_evaluation",
                    description="Read recent quiz/evaluation summary for remediation and study planning.",
                    args_schema=GetRecentEvaluationArgs,
                ),
                StructuredTool.from_function(
                    coroutine=self._analyze_attachment,
                    name="analyze_attachment",
                    description="Analyze uploaded images or documents for this turn.",
                    args_schema=AnalyzeAttachmentArgs,
                ),
            ]
        return self._tools

    def by_name(self, name: str) -> StructuredTool:
        for tool in self.tools():
            if tool.name == name:
                return tool
        raise KeyError(f"Unknown tutor tool: {name}")

    async def _get_learner_profile(
        self,
        dimension: str | None = None,
        course_name: str | None = None,
        reason: str = "",
    ) -> str:
        markdown = await self.profile_service.get_profile_markdown(
            self.request.user_id,
            course_name=course_name,
            dimension=dimension,
        )
        return _compact(f"画像读取原因: {reason or '未提供'}\n{markdown}")

    async def _get_long_term_memory(
        self,
        category: LongTermMemoryCategory | None = None,
        reason: str = "",
    ) -> str:
        category_value = str(category or "").strip() or None
        if category_value and category_value not in LTM_CATEGORIES:
            return f"长期记忆分类无效: {category_value}"
        markdown = await self.memory_service.get_memory_markdown(self.request.user_id, category=category_value)
        return _compact(f"长期记忆读取原因: {reason or '未提供'}\n{markdown}")

    async def _search_knowledge_base(
        self,
        query: str,
        course_name: str | None = None,
        top_k: int = 4,
    ) -> str:
        search_query = f"{course_name} {query}".strip() if course_name else query
        context, _rows = await aformat_knowledge_context(search_query, top_k=top_k)
        return _compact(context or "本地知识库没有检索到相关内容，或知识库尚未正确加载。")

    async def _web_search(self, query: str, reason: str = "") -> str:
        result_text, tool_name = await self.web_search.search(query)
        if result_text:
            return _compact(f"搜索渠道: {tool_name or 'web_search'}\n搜索原因: {reason or '未提供'}\n{result_text}")
        return "联网搜索没有返回可用结果。"

    async def _get_recent_evaluation(self, limit: int = 5, reason: str = "") -> str:
        try:
            async with session_scope() as db:
                summary = await evaluation_service.get_summary(db, user_id=self.request.user_id, limit=limit)
        except Exception as exc:
            logger.warning("[TutorToolRegistry] get_recent_evaluation failed: %s", exc)
            return "暂无近期学习测验评估记录。"
        if summary.event_count <= 0:
            return "暂无近期学习测验评估记录。"
        lines = [f"评估读取原因: {reason or '未提供'}", f"测验记录数: {summary.event_count}"]
        if summary.average_score is not None:
            lines.append(f"平均测验分: {summary.average_score}")
        if summary.weak_topics:
            lines.append(f"薄弱点: {', '.join(summary.weak_topics)}")
        if summary.recommendations:
            lines.append(f"系统建议: {', '.join(summary.recommendations)}")
        return _compact("\n".join(lines))

    async def _analyze_attachment(self, reason: str = "") -> str:
        if not self.request.attachments:
            return "本轮没有上传附件。"
        output = await self.attachment_analyzer.analyze(self.request)
        summaries = [item.summary for item in output.evidence]
        if not summaries:
            return "附件分析没有得到可用内容。"
        return _compact(f"附件分析原因: {reason or '未提供'}\n" + "\n\n".join(summaries))
