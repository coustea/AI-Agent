"""Request-scoped tutor tools for the chat agent."""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.chat.memory.service import get_chat_memory_service
from app.chat.memory.types import LTM_CATEGORIES
from app.chat.schemas import Evidence, ToolIntent, TurnRequest
from app.chat.stages import AttachmentAnalyzer, WebSearchTool
from app.chat.tools.knowledge import aformat_knowledge_context
from app.evaluation.service import evaluation_service
from app.infra.database import session_scope
from app.infra.logging import get_logger
from app.profile.service import get_profile_service

logger = get_logger(__name__)

# Keep this Literal explicit so LangChain/Pydantic expose a stable enum schema for tool callers.
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
        try:
            markdown = await self.profile_service.get_profile_markdown(
                self.request.user_id,
                course_name=course_name,
                dimension=dimension,
            )
        except Exception as exc:
            logger.warning("[TutorToolRegistry] get_learner_profile failed: %s", exc)
            return "暂时无法读取学习者画像。"
        return _compact(f"画像读取原因: {reason or '未提供'}\n{markdown}")

    async def _get_long_term_memory(
        self,
        category: LongTermMemoryCategory | None = None,
        reason: str = "",
    ) -> str:
        category_value = str(category or "").strip() or None
        if category_value and category_value not in LTM_CATEGORIES:
            return f"长期记忆分类无效: {category_value}"
        try:
            markdown = await self.memory_service.get_memory_markdown(self.request.user_id, category=category_value)
        except Exception as exc:
            logger.warning("[TutorToolRegistry] get_long_term_memory failed: %s", exc)
            return "暂时无法读取长期学习记忆。"
        return _compact(f"长期记忆读取原因: {reason or '未提供'}\n{markdown}")

    async def _search_knowledge_base(
        self,
        query: str,
        course_name: str | None = None,
        top_k: int = 4,
    ) -> str:
        search_query = f"{course_name} {query}".strip() if course_name else query
        try:
            context, _rows = await aformat_knowledge_context(search_query, top_k=top_k)
        except Exception as exc:
            logger.warning("[TutorToolRegistry] search_knowledge_base failed: %s", exc)
            return "本地知识库暂时不可用。"
        return _compact(context or "本地知识库没有检索到相关内容，或知识库尚未正确加载。")

    async def _web_search(self, query: str, reason: str = "") -> str:
        try:
            result_text, tool_name = await self.web_search.search(query)
        except Exception as exc:
            logger.warning("[TutorToolRegistry] web_search failed: %s", exc)
            return "联网搜索暂时不可用。"
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
        try:
            output = await self.attachment_analyzer.analyze(self.request)
        except Exception as exc:
            logger.warning("[TutorToolRegistry] analyze_attachment failed: %s", exc)
            return "附件分析暂时不可用。"
        summaries = [item.summary for item in output.evidence]
        if not summaries:
            return "附件分析没有得到可用内容。"
        return _compact(f"附件分析原因: {reason or '未提供'}\n" + "\n\n".join(summaries))


_TOOL_EVIDENCE_TYPES: dict[str, str] = {
    "get_learner_profile": "learner_profile",
    "get_long_term_memory": "long_term_memory",
    "search_knowledge_base": "knowledge_base",
    "web_search": "web_search",
    "get_recent_evaluation": "recent_evaluation",
    "analyze_attachment": "attachment",
}


_TOOL_NAME_ALIASES: dict[str, str] = {
    "learner_profile": "get_learner_profile",
    "long_term_memory": "get_long_term_memory",
    "web_search": "web_search",
}


_LONG_TERM_MEMORY_CATEGORY_ALIASES: dict[str, str] = {
    "goals_progress": "long_term_goals",
}


class TutorToolExecutor:
    """Execute model-requested tutor tools and convert outputs to orchestrator evidence."""

    def __init__(self, *, request: TurnRequest, registry: TutorToolRegistry | None = None) -> None:
        self.request = request
        self.registry = registry or TutorToolRegistry(request=request)

    def tools(self) -> list[StructuredTool]:
        return self.registry.tools()

    async def execute(self, intent: ToolIntent, request: TurnRequest | None = None) -> dict[str, Any]:
        raw_tool_name = str(intent.tool_name or "").strip()
        tool_name = _TOOL_NAME_ALIASES.get(raw_tool_name, raw_tool_name)
        payload = self._normalize_payload(tool_name, intent.payload if isinstance(intent.payload, dict) else {})
        try:
            tool = self.registry.by_name(tool_name)
            raw_result = await tool.ainvoke(payload)
            result_text = "" if raw_result is None else str(raw_result).strip()
        except Exception as exc:
            logger.warning("[TutorToolExecutor] tool failed: name=%s error=%s", tool_name, exc)
            return {
                "tool_name": tool_name,
                "status": "failed",
                "result_text": f"{tool_name} 调用失败: {exc}",
                "evidence": [],
            }

        evidence_type = _TOOL_EVIDENCE_TYPES.get(tool_name)
        evidence = []
        if evidence_type and result_text:
            evidence.append(
                Evidence(
                    evidence_type=evidence_type,  # type: ignore[arg-type]
                    summary=result_text,
                    details={"tool_name": tool_name, "args": payload},
                ).model_dump()
            )
        return {
            "tool_name": tool_name,
            "status": "success" if result_text else "ignored",
            "result_text": result_text,
            "evidence": evidence,
        }

    def _normalize_payload(self, tool_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(payload)
        if tool_name == "get_long_term_memory":
            category = str(normalized.get("category") or "").strip()
            if category:
                normalized["category"] = _LONG_TERM_MEMORY_CATEGORY_ALIASES.get(category, category)
        return normalized
