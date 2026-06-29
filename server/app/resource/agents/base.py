"""资源生成 Agent 基类与注册表。

所有资源生成 Agent 继承 BaseResourceAgent，通过 @register_agent 装饰器
自动注册到全局 AGENT_REGISTRY 字典中，供路径模块和资源服务按 agent_id 查找调用。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.infra.logging import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from app.infra.tool_excute import Tool, ToolExcute
    from app.resource.event import ResourceEvents
    from app.resource.schemas import AgentResult, NodeInput, ResourceInput


AGENT_REGISTRY: dict[str, type[BaseResourceAgent]] = {}


def register_agent(cls: type[BaseResourceAgent]) -> type[BaseResourceAgent]:
    """装饰器：将 Agent 类注册到全局注册表，按 agent_id 索引。"""
    AGENT_REGISTRY[cls.agent_id] = cls
    return cls


class BaseResourceAgent:
    """资源 Agent 基类。子类必须显式实现 resource 和 node 两个入口。

    集成 ToolExcute，支持统一工具调用：
    - invoke_with_tools() 带工具调用的 LLM 调用
    - search() 统一网页搜索功能
    """

    agent_id: str
    agent_name: str

    def __init__(
        self,
        emitter: ResourceEvents | None = None,
        tools: list[Tool] | None = None,
    ) -> None:
        self.emitter = emitter
        if emitter is None:
            class NoopEvents:
                def __getattr__(self, name):
                    async def noop(*args, **kwargs):
                        pass
                    return noop

            self.emitter = NoopEvents()

        # 如果没有传入 tools，直接内置默认的搜索工具
        if tools is None:
            from app.chat.tools.search import SearchQueryArgs, duckduckgo_search, tavily_search, spark_search
            from app.infra.tool_excute import Tool

            async def wrap_ddg(query: str) -> str:
                res = await duckduckgo_search(query)
                return "" if res is None else str(res)

            async def wrap_tavily(query: str) -> str:
                res = await tavily_search(query)
                return "" if res is None else str(res)

            async def wrap_spark(query: str) -> str:
                res = await spark_search(query)
                return "" if res is None else str(res)

            self.tools = [
                Tool(
                    "duckduckgo_search",
                    "General web search for articles, tutorials, blogs, and web content.",
                    SearchQueryArgs,
                    wrap_ddg,
                ),
                Tool(
                    "tavily_search",
                    "AI-optimized search with structured, relevance-ranked results.",
                    SearchQueryArgs,
                    wrap_tavily,
                ),
                Tool(
                    "spark_search",
                    "Chinese semantic search with reranking support.",
                    SearchQueryArgs,
                    wrap_spark,
                ),
            ]
        else:
            self.tools = list(tools)

        from app.infra.llm import get_llm

        async def handle_tool_event(event: dict[str, Any]) -> None:
            status = event.get("status")
            tool_name = event.get("tool_name")
            agent_id = getattr(self, "agent_id", "base_resource")
            if status == "running":
                await self.emitter.send(
                    agent_id,
                    "running",
                    f"正在调用工具 {tool_name}...",
                    data={
                        "phase": "tool_call",
                        "tool_name": tool_name,
                        "tool_status": "running",
                    },
                )
            elif status == "done":
                duration = event.get("duration_ms", 0)
                await self.emitter.send(
                    agent_id,
                    "running",
                    f"工具 {tool_name} 执行成功 (耗时 {duration}ms)",
                    data={
                        "phase": "tool_call",
                        "tool_name": tool_name,
                        "tool_status": "completed",
                        "elapsed_ms": duration,
                    },
                )
            elif status == "failed":
                error = event.get("error", "未知错误")
                await self.emitter.send(
                    agent_id,
                    "running",
                    f"工具 {tool_name} 执行失败: {error}",
                    data={
                        "phase": "tool_call",
                        "tool_name": tool_name,
                        "tool_status": "failed",
                    },
                )

        self.tool_excute = get_llm().create_tool_excute(self.tools, event_handler=handle_tool_event)

    async def search(self, query: str) -> str:
        """内置搜索工具调用：优先使用讯飞星火搜索，其次使用 Tavily，最后回退到 DuckDuckGo。

        通过 ToolExcute 执行以保证生命周期事件被正常触发与监听。
        """
        # 1. 优先调用 spark_search (讯飞星火搜索)
        try:
            res = await self.tool_excute.execute({"name": "spark_search", "args": {"query": query}})
            if "讯飞搜索不可用" not in str(res) and "讯飞搜索失败" not in str(res):
                return str(res)
        except Exception as exc:
            logger.warning("[BaseResourceAgent] spark_search failed: %s", exc)

        # 2. 次选调用 tavily_search
        try:
            res = await self.tool_excute.execute({"name": "tavily_search", "args": {"query": query}})
            if "Tavily 搜索不可用" not in str(res) and "Tavily 搜索失败" not in str(res):
                return str(res)
        except Exception as exc:
            logger.warning("[BaseResourceAgent] tavily_search failed: %s", exc)

        # 3. 兜底调用 duckduckgo_search
        try:
            res = await self.tool_excute.execute({"name": "duckduckgo_search", "args": {"query": query}})
            return str(res)
        except Exception as exc:
            logger.error("[BaseResourceAgent] duckduckgo_search fallback failed: %s", exc)
            return f"搜索失败: {exc}"

    # -- ToolExcute 集成 -----------------------------------------------------

    async def invoke_with_tools(self, messages: Any, **kwargs: Any) -> tuple[Any, list[dict[str, Any]]]:
        """使用 ToolExcute 调用 LLM，返回 (response, tool_calls)。

        如果没有注册工具，退化为普通 LLM 调用。
        """
        if not self.tool_excute:
            from app.infra.llm import get_llm

            llm = get_llm()
            response = await llm.ainvoke(messages, **kwargs)
            return response, []

        return await self.tool_excute.invoke(messages, **kwargs)

    async def execute_tools(self, tool_calls: list[dict[str, Any]]) -> list[Any]:
        """执行工具调用列表。"""
        if not self.tool_excute or not tool_calls:
            return []
        return await self.tool_excute.execute_all(tool_calls)

    # -- 子类必须实现的入口 ----------------------------------------------------

    async def generate_resource(self, input_data: ResourceInput) -> AgentResult:
        """独立资源生成入口（standalone 模式）。子类必须实现。"""
        raise NotImplementedError(f"{self.__class__.__name__}.generate_resource is required")

    async def generate_node(self, input_data: NodeInput) -> AgentResult:
        """路径节点资源生成入口。子类必须实现。"""
        raise NotImplementedError(f"{self.__class__.__name__}.generate_node is required")
