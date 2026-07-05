"""Tool 和 ToolExcute 单元测试 — 自研工具调用框架。

测试覆盖：
  - Tool 类：注册、描述 Schema 生成、参数校验
  - ToolExcute 类：注册与查询工具、参数校验、执行、并发执行、生命周期事件
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, Field

from app.infra.tool_excute import Tool, ToolExcute


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


# ── ToolExcute 注册测试 ──


class TestToolExcuteRegistration:
    def test_tool_excute_has_no_model_or_model_invocation_responsibility(self):
        tool_excute = ToolExcute()

        assert not hasattr(tool_excute, "model")
        assert not hasattr(tool_excute, "invoke")
        assert not hasattr(ToolExcute, "_normalize_response_calls")

    def test_register_single_tool(self):
        async def handler() -> str:
            return "ok"

        tool_excute = ToolExcute()
        tool = tool_excute.register(
            Tool("test", "Test tool.", EchoArgs, handler)
        )
        assert tool.name == "test"
        assert tool_excute.get_tool("test") == tool

    def test_register_many_tools(self):
        async def echo(msg: str) -> str:
            return msg

        async def search(q: str) -> str:
            return f"results for {q}"

        tools = [
            Tool("echo", "Echo tool.", EchoArgs, echo),
            Tool("search", "Search tool.", SearchArgs, search),
        ]
        tool_excute = ToolExcute(tools=tools)
        assert len(tool_excute.get_tools()) == 2
        assert tool_excute.get_tool("echo").name == "echo"
        assert tool_excute.get_tool("search").name == "search"

    def test_duplicate_registration_raises(self):
        async def handler() -> str:
            return ""

        tool_excute = ToolExcute()
        tool_excute.register(Tool("test", "Test.", EchoArgs, handler))
        with pytest.raises(ValueError, match="Tool already registered"):
            tool_excute.register(Tool("test", "Another.", EchoArgs, handler))

    def test_get_unknown_tool_raises(self):
        tool_excute = ToolExcute()
        with pytest.raises(KeyError, match="Unknown tool"):
            tool_excute.get_tool("nonexistent")


# ── ToolExcute.get_tools_description 测试 ──


class TestToolExcuteDescription:
    def test_get_tools_description_returns_schema_list(self):
        async def echo(msg: str) -> str:
            return msg

        tool_excute = ToolExcute(
            tools=[Tool("echo", "Echo.", EchoArgs, echo)],
        )
        descriptions = tool_excute.get_tools_description()
        assert len(descriptions) == 1
        assert descriptions[0]["function"]["name"] == "echo"


# ── ToolExcute.execute 单工具执行测试 ──


class TestToolExcuteExecute:
    @pytest.mark.asyncio
    async def test_execute_validates_args_with_pydantic(self):
        async def echo(message: str, repeat: int = 1) -> str:
            return message * repeat

        tool_excute = ToolExcute(
            tools=[Tool("echo", "Echo.", EchoArgs, echo)],
        )
        result = await tool_excute.execute({
            "name": "echo",
            "args": {"message": "hi", "repeat": 3},
        })
        assert result == "hihihi"

    @pytest.mark.asyncio
    async def test_execute_uses_default_args(self):
        async def echo(message: str, repeat: int = 1) -> str:
            return message * repeat

        tool_excute = ToolExcute(
            tools=[Tool("echo", "Echo.", EchoArgs, echo)],
        )
        result = await tool_excute.execute({
            "name": "echo",
            "args": {"message": "hi"},
        })
        assert result == "hi"

    @pytest.mark.asyncio
    async def test_execute_rejects_invalid_args(self):
        async def echo(message: str, repeat: int = 1) -> str:
            return message * repeat

        tool_excute = ToolExcute(
            tools=[Tool("echo", "Echo.", EchoArgs, echo)],
        )
        with pytest.raises(Exception):  # Pydantic ValidationError
            await tool_excute.execute({
                "name": "echo",
                "args": {"repeat": 10},  # repeat > 5 violates Field(le=5)
            })

    @pytest.mark.asyncio
    async def test_execute_empty_name_raises(self):
        tool_excute = ToolExcute()
        with pytest.raises(ValueError, match="Tool call name cannot be empty"):
            await tool_excute.execute({"name": "", "args": {}})

    @pytest.mark.asyncio
    async def test_execute_missing_args_raises(self):
        async def handler() -> str:
            return ""

        tool_excute = ToolExcute(
            tools=[Tool("test", "Test.", EchoArgs, handler)],
        )
        with pytest.raises(ValueError, match="Tool arguments must be an object"):
            await tool_excute.execute({"name": "test", "args": None})


# ── ToolExcute.execute_all 并发执行测试 ──


class TestToolExcuteExecuteAll:
    @pytest.mark.asyncio
    async def test_execute_all_runs_tools_concurrently(self):
        import asyncio

        async def slow_handler(message: str, repeat: int = 1) -> str:
            await asyncio.sleep(0.01)
            return f"slow-{message}"

        async def fast_handler(query: str, limit: int = 5) -> str:
            return f"fast-{query}"

        tool_excute = ToolExcute(
            tools=[
                Tool("slow", "Slow.", EchoArgs, slow_handler),
                Tool("fast", "Fast.", SearchArgs, fast_handler),
            ],
        )
        calls = [
            {"name": "slow", "args": {"message": "a"}},
            {"name": "fast", "args": {"query": "b"}},
        ]
        results = await tool_excute.execute_all(calls)
        assert len(results) == 2
        assert "slow-a" in results[0]
        assert "fast-b" in results[1]

    @pytest.mark.asyncio
    async def test_execute_all_returns_exceptions_for_failed_calls(self):
        async def failing_handler(message: str, repeat: int = 1) -> str:
            raise RuntimeError("tool failed")

        async def working_handler(query: str, limit: int = 5) -> str:
            return f"result-{query}"

        tool_excute = ToolExcute(
            tools=[
                Tool("failing", "Failing.", EchoArgs, failing_handler),
                Tool("working", "Working.", SearchArgs, working_handler),
            ],
        )
        calls = [
            {"name": "failing", "args": {"message": "test"}},
            {"name": "working", "args": {"query": "search"}},
        ]
        results = await tool_excute.execute_all(calls)

        assert len(results) == 2
        assert isinstance(results[0], RuntimeError)
        assert results[1] == "result-search"

    @pytest.mark.asyncio
    async def test_execute_all_empty_list_returns_empty(self):
        tool_excute = ToolExcute()
        results = await tool_excute.execute_all([])
        assert results == []


# ── ToolExcute.subset 测试 ──


class TestToolExcuteSubset:
    def test_subset_retains_specified_tools(self):
        async def echo(msg: str) -> str:
            return msg

        async def search(q: str) -> str:
            return f"results for {q}"

        tool_excute = ToolExcute(
            tools=[
                Tool("echo", "Echo tool.", EchoArgs, echo),
                Tool("search", "Search tool.", SearchArgs, search),
            ],
        )
        subset = tool_excute.subset(["echo"])
        assert len(subset.get_tools()) == 1
        assert subset.get_tool("echo").name == "echo"
        with pytest.raises(KeyError):
            subset.get_tool("search")

    def test_subset_preserves_event_handler(self):
        events: list[dict] = []

        async def handler(event: dict) -> None:
            events.append(event)

        tool_excute = ToolExcute(tools=[], event_handler=handler)
        subset = tool_excute.subset([])
        assert subset._event_handler is handler


# ── ToolExcute 事件回调测试 ──


class TestToolExcuteEventHandler:
    @pytest.mark.asyncio
    async def test_execute_emits_running_then_done(self):
        events: list[dict] = []

        async def handler(event: dict) -> None:
            events.append(event)

        async def echo(message: str, repeat: int = 1) -> str:
            return message * repeat

        tool_excute = ToolExcute(
            tools=[Tool("echo", "Echo.", EchoArgs, echo)],
            event_handler=handler,
        )
        await tool_excute.execute({"name": "echo", "args": {"message": "hi"}})

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

        tool_excute = ToolExcute(
            tools=[Tool("failing", "Failing.", EchoArgs, failing)],
            event_handler=handler,
        )

        with pytest.raises(RuntimeError, match="tool error"):
            await tool_excute.execute({"name": "failing", "args": {"message": "test"}})

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

        tool_excute = ToolExcute(
            tools=[Tool("echo", "Echo.", EchoArgs, echo)],
            event_handler=bad_handler,
        )

        # Should not raise - handler exceptions are caught internally
        result = await tool_excute.execute({"name": "echo", "args": {"message": "hi"}})
        assert result == "hi"
        # Only running was attempted before exception, done should still emit
        assert "running" in [e["status"] for e in events]
