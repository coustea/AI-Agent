"""Tool 与 ToolRegistry 单元测试。"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, Field

from app.shared.tools.registry import Tool, ToolRegistry, format_tool_output


class EchoArgs(BaseModel):
    """Echo 工具参数。"""

    message: str = Field(description="Message to echo.")
    repeat: int = Field(default=1, ge=1, le=5, description="Number of repeats.")


class TestTool:
    def test_holds_name_description_and_handler(self):
        """Tool 保存模型可见的名称、描述与执行入口。"""

        async def echo(message: str, repeat: int = 1) -> str:
            """回显消息。"""
            return message * repeat

        tool = Tool("echo", "Echo a message with optional repeats.", EchoArgs, echo)
        assert tool.name == "echo"
        assert tool.description == "Echo a message with optional repeats."
        assert tool.handler is echo

    def test_empty_name_raises(self):
        """名称为空直接报错。"""

        async def handler() -> str:
            """空实现。"""
            return ""

        with pytest.raises(ValueError, match="Tool name cannot be empty"):
            Tool("", "desc", EchoArgs, handler)

    def test_empty_description_raises(self):
        """描述为空直接报错。"""

        async def handler() -> str:
            """空实现。"""
            return ""

        with pytest.raises(ValueError, match="Tool description cannot be empty"):
            Tool("test", "", EchoArgs, handler)

    def test_openai_schema_structure(self):
        """schema 由 args_model 生成，含名称、描述与参数定义。"""

        async def handler(message: str) -> str:
            """回显消息。"""
            return message

        schema = Tool("echo", "Echo tool.", EchoArgs, handler).to_openai_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "echo"
        assert schema["function"]["description"] == "Echo tool."
        assert schema["function"]["parameters"]["required"] == ["message"]


class TestToolRegistry:
    def test_duplicate_registration_raises(self):
        """同名工具重复注册直接报错。"""

        async def handler() -> str:
            """空实现。"""
            return ""

        with pytest.raises(ValueError, match="Tool already registered"):
            ToolRegistry([
                Tool("test", "Test.", EchoArgs, handler),
                Tool("test", "Another.", EchoArgs, handler),
            ])

    def test_openai_schemas_lists_every_tool(self):
        """openai_schemas 返回全部工具的 schema。"""

        async def echo(msg: str) -> str:
            """回显消息。"""
            return msg

        registry = ToolRegistry([Tool("echo", "Echo.", EchoArgs, echo)])
        schemas = registry.openai_schemas()
        assert [item["function"]["name"] for item in schemas] == ["echo"]


class TestToolRegistryExecute:
    @pytest.mark.asyncio
    async def test_validates_args_with_pydantic(self):
        """参数经 args_model 校验后传给 handler。"""

        async def echo(message: str, repeat: int = 1) -> str:
            """回显消息。"""
            return message * repeat

        registry = ToolRegistry([Tool("echo", "Echo.", EchoArgs, echo)])
        assert await registry.execute("echo", {"message": "hi", "repeat": 3}) == "hihihi"

    @pytest.mark.asyncio
    async def test_accepts_json_string_args(self):
        """支持 OpenAI 直接给出的 JSON 字符串参数。"""

        async def echo(message: str, repeat: int = 1) -> str:
            """回显消息。"""
            return message * repeat

        registry = ToolRegistry([Tool("echo", "Echo.", EchoArgs, echo)])
        assert await registry.execute("echo", '{"message": "hi", "repeat": 2}') == "hihi"

    @pytest.mark.asyncio
    async def test_uses_default_args(self):
        """缺省字段由 pydantic 补齐。"""

        async def echo(message: str, repeat: int = 1) -> str:
            """回显消息。"""
            return message * repeat

        registry = ToolRegistry([Tool("echo", "Echo.", EchoArgs, echo)])
        assert await registry.execute("echo", {"message": "hi"}) == "hi"

    @pytest.mark.asyncio
    async def test_rejects_invalid_args(self):
        """参数越界时抛校验错误，不执行 handler。"""

        async def echo(message: str, repeat: int = 1) -> str:
            """回显消息。"""
            return message * repeat

        registry = ToolRegistry([Tool("echo", "Echo.", EchoArgs, echo)])
        with pytest.raises(Exception):
            await registry.execute("echo", {"message": "hi", "repeat": 10})

    @pytest.mark.asyncio
    async def test_unknown_tool_raises(self):
        """未注册的工具名抛 KeyError。"""

        with pytest.raises(KeyError, match="Unknown tool"):
            await ToolRegistry().execute("nonexistent", {})


class TestFormatToolOutput:
    def test_text_payload_returns_plain_text(self):
        """带 text 的短结构直接返回文本，失败加 [Error] 前缀。"""
        assert format_tool_output({"text": "done", "status": "ok"}) == "done"
        assert format_tool_output({"text": "boom", "status": "failed"}) == "[Error] boom"

    def test_other_structures_serialize_as_json(self):
        """其余结构序列化为 JSON 文本。"""
        assert '"exit_code": 0' in format_tool_output({"stdout": "x", "stderr": "", "exit_code": 0})
