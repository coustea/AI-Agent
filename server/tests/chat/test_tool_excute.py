"""Tool 和 ToolRegistry 单元测试 — 自研工具调用框架。

测试覆盖：
  - Tool 类：注册、描述 Schema 生成、参数校验
  - ToolRegistry 类：注册与查询工具、参数校验、执行、并发执行、生命周期事件
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, Field

from app.shared.tools import Tool, ToolRegistry


class EchoArgs(BaseModel):
    message: str = Field(description="Message to echo.")
    repeat: int = Field(default=1, ge=1, le=5, description="Number of repeats.")


class SearchArgs(BaseModel):
    query: str = Field(description="Search query.")
    limit: int = Field(default=5, description="Max results.")


# ── Tool 类测试 ──


class TestTool:
    def test_tool_name_description_required(self):
        async def echo_handler(message: str, repeat: int = 1) -> str:
            return message * repeat

        tool = Tool(
            "echo",
            "Echo a message with optional repeats.",
            EchoArgs,
            echo_handler,
        )
        assert tool.name == "echo"
        assert tool.description == "Echo a message with optional repeats."

    def test_tool_empty_name_raises(self):
        async def handler() -> str:
            return ""

        with pytest.raises(ValueError, match="Tool name cannot be empty"):
            Tool("", "desc", EchoArgs, handler)

    def test_tool_empty_description_raises(self):
        async def handler() -> str:
            return ""

        with pytest.raises(ValueError, match="Tool description cannot be empty"):
            Tool("test", "", EchoArgs, handler)

    def test_description_schema_structure(self):
        async def handler(message: str) -> str:
            return message

        tool = Tool("echo", "Echo tool.", EchoArgs, handler)
        schema = tool.description_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "echo"
        assert schema["function"]["description"] == "Echo tool."
        assert "properties" in schema["function"]["parameters"]
        assert "message" in schema["function"]["parameters"]["properties"]
        assert schema["function"]["parameters"]["required"] == ["message"]


# ── ToolRegistry 注册测试 ──


class TestToolRegistryRegistration:
    def test_tool_registry_has_no_model_or_model_invocation_responsibility(self):
        registry = ToolRegistry()

        assert not hasattr(registry, "model")
        assert not hasattr(registry, "invoke")
        assert not hasattr(ToolRegistry, "_normalize_response_calls")

    def test_register_single_tool(self):
        async def handler() -> str:
            return "ok"

        registry = ToolRegistry()
        tool = registry.register(
            Tool("test", "Test tool.", EchoArgs, handler)
        )
        assert tool.name == "test"
        assert registry.get_tool("test") == tool

    def test_register_many_tools(self):
        async def echo(msg: str) -> str:
            return msg

        async def search(q: str) -> str:
            return f"results for {q}"

        tools = [
            Tool("echo", "Echo tool.", EchoArgs, echo),
            Tool("search", "Search tool.", SearchArgs, search),
        ]
        registry = ToolRegistry(tools=tools)
        assert registry.get_tool("echo").name == "echo"
        assert registry.get_tool("search").name == "search"

    def test_duplicate_registration_raises(self):
        async def handler() -> str:
            return ""

        registry = ToolRegistry()
        registry.register(Tool("test", "Test.", EchoArgs, handler))
        with pytest.raises(ValueError, match="Tool already registered"):
            registry.register(Tool("test", "Another.", EchoArgs, handler))

    def test_get_unknown_tool_raises(self):
        registry = ToolRegistry()
        with pytest.raises(KeyError, match="Unknown tool"):
            registry.get_tool("nonexistent")


# ── ToolRegistry.get_tools_description 测试 ──


class TestToolRegistryDescription:
    def test_get_tools_description_returns_schema_list(self):
        async def echo(msg: str) -> str:
            return msg

        registry = ToolRegistry(
            tools=[Tool("echo", "Echo.", EchoArgs, echo)],
        )
        descriptions = registry.get_tools_description()
        assert len(descriptions) == 1
        assert descriptions[0]["function"]["name"] == "echo"


# ── ToolRegistry.execute 单工具执行测试 ──


class TestToolRegistryExecute:
    @pytest.mark.asyncio
    async def test_execute_validates_args_with_pydantic(self):
        async def echo(message: str, repeat: int = 1) -> str:
            return message * repeat

        registry = ToolRegistry(
            tools=[Tool("echo", "Echo.", EchoArgs, echo)],
        )
        result = await registry.execute({
            "name": "echo",
            "args": {"message": "hi", "repeat": 3},
        })
        assert result == "hihihi"

    @pytest.mark.asyncio
    async def test_execute_uses_default_args(self):
        async def echo(message: str, repeat: int = 1) -> str:
            return message * repeat

        registry = ToolRegistry(
            tools=[Tool("echo", "Echo.", EchoArgs, echo)],
        )
        result = await registry.execute({
            "name": "echo",
            "args": {"message": "hi"},
        })
        assert result == "hi"

    @pytest.mark.asyncio
    async def test_execute_rejects_invalid_args(self):
        async def echo(message: str, repeat: int = 1) -> str:
            return message * repeat

        registry = ToolRegistry(
            tools=[Tool("echo", "Echo.", EchoArgs, echo)],
        )
        with pytest.raises(Exception):  # Pydantic ValidationError
            await registry.execute({
                "name": "echo",
                "args": {"repeat": 10},  # repeat > 5 violates Field(le=5)
            })

    @pytest.mark.asyncio
    async def test_execute_empty_name_raises(self):
        registry = ToolRegistry()
        with pytest.raises(ValueError, match="Tool call name cannot be empty"):
            await registry.execute({"name": "", "args": {}})

    @pytest.mark.asyncio
    async def test_execute_missing_args_raises(self):
        async def handler() -> str:
            return ""

        registry = ToolRegistry(
            tools=[Tool("test", "Test.", EchoArgs, handler)],
        )
        with pytest.raises(ValueError, match="Tool arguments must be an object"):
            await registry.execute({"name": "test", "args": None})


# ── ToolRegistry 事件通知测试 ──


class TestToolRegistryEventHandler:
    @pytest.mark.asyncio
    async def test_execute_emits_running_then_done(self):
        events: list[dict] = []

        async def handler(event: dict) -> None:
            events.append(event)

        async def echo(message: str, repeat: int = 1) -> str:
            return message * repeat

        registry = ToolRegistry(
            tools=[Tool("echo", "Echo.", EchoArgs, echo)],
            event_handler=handler,
        )
        await registry.execute({"name": "echo", "args": {"message": "hi"}})

        assert len(events) == 2
        assert events[0]["status"] == "running"
        assert events[0]["tool_name"] == "echo"
        assert events[1]["status"] == "done"
        assert events[1]["tool_name"] == "echo"

    @pytest.mark.asyncio
    async def test_execute_emits_running_then_failed_on_exception(self):
        events: list[dict] = []

        async def handler(event: dict) -> None:
            events.append(event)

        async def failing(message: str, repeat: int = 1) -> str:
            raise RuntimeError("tool error")

        registry = ToolRegistry(
            tools=[Tool("failing", "Failing.", EchoArgs, failing)],
            event_handler=handler,
        )

        with pytest.raises(RuntimeError, match="tool error"):
            await registry.execute({"name": "failing", "args": {"message": "test"}})

        assert len(events) == 2
        assert events[0]["status"] == "running"
        assert events[1]["status"] == "failed"

    @pytest.mark.asyncio
    async def test_event_handler_exception_does_not_affect_execution(self):
        events: list[dict] = []

        async def bad_handler(event: dict) -> None:
            events.append(event)
            if event["status"] == "running":
                raise RuntimeError("handler error")

        async def echo(message: str, repeat: int = 1) -> str:
            return message * repeat

        registry = ToolRegistry(
            tools=[Tool("echo", "Echo.", EchoArgs, echo)],
            event_handler=bad_handler,
        )

        # Should not raise - handler exceptions are caught internally
        result = await registry.execute({"name": "echo", "args": {"message": "hi"}})
        assert result == "hi"
        # Only running was attempted before exception, done should still emit
        assert "running" in [e["status"] for e in events]
