"""请求级别的工具注册表和执行器 — 为聊天代理构建并执行 LangChain 工具。

职责：
  - TutorToolRegistry: 根据当前辅导轮次构建可用工具列表（懒加载）
  - TutorToolExecutor: 执行模型请求的工具调用，将结果转换为编排器可用的证据格式

工具列表：
  - get_learner_profile: 获取学习者画像（个性化偏好、目标、背景）
  - get_long_term_memory: 获取长期记忆（历史目标、偏好、薄弱点、纠正记录）
  - search_knowledge_base: 搜索本地课程知识库（定义、概念、教材内容）
  - web_search: 联网搜索外部信息（仅用于当前、近期或用户明确要求的内容）
  - get_recent_evaluation: 获取最近的测验/评估摘要（用于补救和学习规划）
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import StructuredTool

from app.chat.schemas import Evidence, ToolIntent, TurnRequest
from app.chat.stages import WebSearchTool
from app.chat.tools.evaluation import GetRecentEvaluationArgs, make_get_recent_evaluation
from app.chat.tools.knowledge import SearchKnowledgeBaseArgs, make_search_knowledge_base
from app.chat.tools.memory import LONG_TERM_MEMORY_CATEGORY_ALIASES, GetLongTermMemoryArgs, make_get_long_term_memory
from app.chat.tools.profile import GetLearnerProfileArgs, make_get_learner_profile
from app.infra.logging import get_logger

logger = get_logger(__name__)

# 工具名 → 证据类型的映射表，用于将工具返回结果包装为编排器可识别的证据
TOOL_EVIDENCE_TYPES: dict[str, str] = {
    "get_learner_profile": "learner_profile",
    "get_long_term_memory": "long_term_memory",
    "search_knowledge_base": "knowledge_base",
    "web_search": "web_search",
    "get_recent_evaluation": "recent_evaluation",
}

# 工具名别名映射 — 模型可能返回简短别名，需要解析为完整的工具函数名
TOOL_NAME_ALIASES: dict[str, str] = {
    "learner_profile": "get_learner_profile",
    "long_term_memory": "get_long_term_memory",
    "web_search": "web_search",
}


class TutorToolRegistry:
    """辅导工具注册表 — 构建绑定到单次辅导轮次的 LangChain 工具集合。

    每个 TurnRequest 创建一个 Registry 实例，工具列表通过 tools() 懒加载。
    工具的 coroutine 工厂函数会捕获当前请求上下文（用户ID、会话ID等），
    确保工具在执行时能访问正确的请求数据。
    """

    def __init__(
        self,
        *,
        request: TurnRequest,
        memory_service: Any | None = None,
        web_search: Any | None = None,
        profile_service: Any | None = None,
    ) -> None:
        self.request = request
        self.memory_service = memory_service
        # web_search 默认使用 WebSearchTool，也可注入外部实例
        self.web_search = web_search or WebSearchTool()
        self.profile_service = profile_service
        # 懒加载缓存：首次调用 tools() 时构建，后续直接返回
        self._tools: list[StructuredTool] | None = None

    def tools(self) -> list[StructuredTool]:
        """懒加载构建工具列表 — 首次调用时创建所有 StructuredTool 实例。"""
        if self._tools is None:
            self._tools = [
                # 学习者画像工具 — 用于个性化辅导时获取用户的学习偏好、目标和背景信息
                StructuredTool.from_function(
                    coroutine=make_get_learner_profile(self.request, self.profile_service),
                    name="get_learner_profile",
                    description="Read learner profile when personalization, goals, preferences, or background matter.",
                    args_schema=GetLearnerProfileArgs,
                ),
                # 长期记忆工具 — 获取跨会话持久化的学习特征（目标、偏好、薄弱点、纠正记录等）
                StructuredTool.from_function(
                    coroutine=make_get_long_term_memory(self.request, self.memory_service),
                    name="get_long_term_memory",
                    description="Read durable learning memory for previous goals, preferences, weaknesses, strategies, or corrections.",
                    args_schema=GetLongTermMemoryArgs,
                ),
                # 本地知识库搜索工具 — 检索课程定义、概念、教材内容等结构化知识
                StructuredTool.from_function(
                    coroutine=make_search_knowledge_base(),
                    name="search_knowledge_base",
                    description="Search local course knowledge base for definitions, concepts, textbook facts, and course material.",
                    args_schema=SearchKnowledgeBaseArgs,
                ),
                # 联网搜索工具 — 仅用于需要当前、近期或用户明确要求的外部信息
                StructuredTool.from_function(
                    coroutine=self._web_search,
                    name="web_search",
                    description="Search the web only for current, recent, or explicitly requested external information.",
                ),
                # 最近评估工具 — 获取近期测验/评估摘要，用于补救教学和学习规划
                StructuredTool.from_function(
                    coroutine=make_get_recent_evaluation(self.request),
                    name="get_recent_evaluation",
                    description="Read recent quiz/evaluation summary for remediation and study planning.",
                    args_schema=GetRecentEvaluationArgs,
                ),
            ]
        return self._tools

    def by_name(self, name: str) -> StructuredTool:
        """按工具名查找 — 如果找不到则抛出 KeyError。"""
        for tool in self.tools():
            if tool.name == name:
                return tool
        raise KeyError(f"Unknown tutor tool: {name}")

    async def _web_search(self, query: str, reason: str = "") -> str:
        """联网搜索的内部实现 — 委托给 WebSearchTool，失败时返回友好提示。

        Args:
            query: 搜索关键词
            reason: 搜索原因（供日志和上下文记录）
        """
        from app.chat.tools.profile import _compact

        try:
            result_text, tool_name = await self.web_search.search(query)
        except Exception as exc:
            logger.warning("[TutorToolRegistry] web_search failed: %s", exc)
            return "联网搜索暂时不可用。"
        # 搜索成功：将搜索渠道、原因和结果拼接，用 _compact 压缩过长文本
        if result_text:
            return _compact(f"搜索渠道: {tool_name or 'web_search'}\n搜索原因: {reason or '未提供'}\n{result_text}")
        return "联网搜索没有返回可用结果。"


class TutorToolExecutor:
    """工具执行器 — 执行模型请求的工具调用，并将原始输出转换为编排器可用的证据格式。

    执行流程：
      1. 解析工具名（处理别名映射）
      2. 规范化参数（如长期记忆的 category 别名）
      3. 调用工具并捕获结果
      4. 将结果包装为 Evidence 对象供编排器使用
    """

    def __init__(self, *, request: TurnRequest, registry: TutorToolRegistry | None = None) -> None:
        self.request = request
        # 如果未提供注册表，自动创建一个绑定到当前请求的新注册表
        self.registry = registry or TutorToolRegistry(request=request)

    def tools(self) -> list[StructuredTool]:
        return self.registry.tools()

    async def execute(self, intent: ToolIntent, request: TurnRequest | None = None) -> dict[str, Any]:
        """执行单个工具调用 — 解析别名、规范化参数、调用工具、包装证据。

        Args:
            intent: 模型输出的工具调用意图（包含工具名和参数）
            request: 可选的请求覆盖（当前未使用）

        Returns:
            包含 tool_name、status、result_text 和 evidence 的字典
        """
        # 第一步：解析工具名（处理别名映射，如 "learner_profile" → "get_learner_profile"）
        raw_tool_name = str(intent.tool_name or "").strip()
        tool_name = TOOL_NAME_ALIASES.get(raw_tool_name, raw_tool_name)
        # 第二步：规范化参数（如长期记忆的 category 别名替换）
        payload = self._normalize_payload(tool_name, intent.payload if isinstance(intent.payload, dict) else {})
        try:
            # 第三步：查找工具并异步调用
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

        # 第四步：将工具结果包装为 Evidence 供编排器使用
        evidence_type = TOOL_EVIDENCE_TYPES.get(tool_name)
        evidence = []
        # 仅当有证据类型映射且结果非空时才创建 Evidence
        if evidence_type and result_text:
            evidence.append(
                Evidence(
                    evidence_type=evidence_type,
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
        """规范化工具参数 — 处理别名替换等预处理逻辑。

        当前仅对 get_long_term_memory 的 category 参数做别名替换，
        将简短别名（如 "weakness"）转换为完整分类名（如 "stable_weaknesses"）。
        """
        normalized = dict(payload)
        if tool_name == "get_long_term_memory":
            category = str(normalized.get("category") or "").strip()
            if category:
                normalized["category"] = LONG_TERM_MEMORY_CATEGORY_ALIASES.get(category, category)
        return normalized
