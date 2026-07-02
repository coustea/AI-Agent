"""资源生成 Agent 基类与注册表。

所有资源生成 Agent 继承 BaseResourceAgent，通过 @register_agent 装饰器
自动注册到全局 AGENT_REGISTRY 字典中，供路径模块和资源服务按 agent_id 查找调用。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.infra.logging import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from app.infra.tool_excute import Tool
    from app.resource.event import ResourceEvents
    from app.resource.schemas import AgentResult, NodeInput, ResourceInput


AGENT_REGISTRY: dict[str, type[BaseResourceAgent]] = {}


def register_agent(cls: type[BaseResourceAgent]) -> type[BaseResourceAgent]:
    """装饰器：将 Agent 类注册到全局注册表，按 agent_id 索引。"""
    AGENT_REGISTRY[cls.agent_id] = cls
    return cls


class BaseResourceAgent:
    """资源 Agent 基类。子类必须显式实现 resource 和 node 两个入口。

    集成 ToolExcute，统一把网页研究委托给 ResearchAgent。
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

        from app.infra.llm import get_llm
        from app.infra.tool_excute import ToolExcute
        from app.shared.research import build_research_tool

        llm = get_llm()

        async def handle_research_event(event: dict[str, Any]) -> None:
            status = str(event.get("status") or "running")
            action = str(event.get("action") or "核验网页资料")
            duration = event.get("duration_ms")
            if status == "done":
                message = f"ResearchAgent：{action}已完成"
                tool_status = "completed"
            elif status == "failed":
                message = f"ResearchAgent：{action}未完成"
                tool_status = "failed"
            else:
                message = f"ResearchAgent：正在{action}..."
                tool_status = "running"
            await self.emitter.send(
                getattr(self, "agent_id", "base_resource"),
                "running",
                message,
                data={
                    "phase": "research",
                    "sub_agent": "research",
                    "action": action,
                    "tool_name": event.get("tool_name"),
                    "tool_status": tool_status,
                    "elapsed_ms": duration,
                },
            )

        async def handle_tool_event(event: dict[str, Any]) -> None:
            status = event.get("status")
            tool_name = event.get("tool_name")
            agent_id = getattr(self, "agent_id", "base_resource")
            if status == "running":
                await self.emitter.send(
                    agent_id,
                    "running",
                    "正在委托 ResearchAgent 研究资料...",
                    data={
                        "phase": "research_delegate",
                        "sub_agent": "research",
                        "tool_name": tool_name,
                        "tool_status": "running",
                    },
                )
            elif status == "done":
                duration = event.get("duration_ms", 0)
                await self.emitter.send(
                    agent_id,
                    "running",
                    f"ResearchAgent 已完成资料研究（耗时 {duration}ms）",
                    data={
                        "phase": "research_delegate",
                        "sub_agent": "research",
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
                    f"ResearchAgent 研究失败: {error}",
                    data={
                        "phase": "research_delegate",
                        "sub_agent": "research",
                        "tool_name": tool_name,
                        "tool_status": "failed",
                    },
                )

        research_tool = build_research_tool(
            model=llm.model,
            event_handler=handle_research_event,
        )
        custom_tools = [tool for tool in (tools or []) if tool.name != "research"]
        self.tools = [research_tool, *custom_tools]
        self.tool_excute = ToolExcute(self.tools, event_handler=handle_tool_event)

    async def search(self, query: str) -> str:
        """通过共享 research 工具把网页研究委托给 ResearchAgent。"""
        try:
            result = await self.tool_excute.execute({
                "name": "research",
                "args": {
                    "query": query,
                    "objective": "为资源生成提供准确、可引用的网页资料",
                    "depth": "standard",
                },
            })
            if isinstance(result, dict):
                return str(result.get("text") or "")
            return str(result or "")
        except Exception as exc:
            logger.error("[BaseResourceAgent] ResearchAgent failed: %s", exc)
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
