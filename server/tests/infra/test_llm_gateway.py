# -*- coding: utf-8 -*-
"""测试单文本模型 LLM Gateway。"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel

import app.infra.llm as llm_module
from app.infra.utils import ServiceError
from app.infra.llm import Llm
from pydantic import Field


class _Payload(BaseModel):
    name: str
    score: int


class _TextResponse:
    def __init__(self, content: str) -> None:
        self.content = content


class _ToolResponse:
    def __init__(self, tool_calls: list[dict]) -> None:
        self.tool_calls = tool_calls


class _Runnable:
    def __init__(self, response: _ToolResponse) -> None:
        self.response = response
        self.invocations: list[Any] = []

    async def ainvoke(self, _input_data, **_kwargs):
        self.invocations.append(_input_data)
        return self.response

    async def astream(self, _input_data, **_kwargs):
        self.invocations.append(_input_data)
        yield "tool-chunk-1"
        yield "tool-chunk-2"


class _FakeModel:
    def __init__(
        self,
        *,
        text: str = "ok",
        tool_calls: list[dict] | None = None,
        fail_tools: bool = False,
    ) -> None:
        self.text_response = _TextResponse(text)
        self.tool_response = _ToolResponse(tool_calls or [])
        self.fail_tools = fail_tools
        self.bind_calls: list[dict[str, Any]] = []
        self.bound_tools: list[Any] | None = None
        self.tool_choice: str | None = None
        self.invocations: list[Any] = []

    def bind(self, **kwargs):
        self.bind_calls.append(kwargs)
        return self

    def bind_tools(self, tools, *, tool_choice=None):
        if self.fail_tools:
            raise RuntimeError("tool calling unavailable")
        self.bound_tools = tools
        self.tool_choice = tool_choice
        return _Runnable(self.tool_response)

    async def ainvoke(self, _input_data, **_kwargs):
        self.invocations.append(_input_data)
        return self.text_response

    async def astream(self, _input_data, **_kwargs):
        yield "chunk-1"
        yield "chunk-2"


class _CapturedChatOpenAI:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.model_name = kwargs.get("model")
        self.base_url = str(kwargs.get("base_url"))


@pytest.fixture
def llm_with_fake_model() -> tuple[Llm, _FakeModel]:
    llm = Llm()
    fake = _FakeModel()
    llm._text_model = fake
    return llm, fake


def test_initializes_single_text_model_from_config(monkeypatch) -> None:
    monkeypatch.setattr(llm_module, "ChatOpenAI", _CapturedChatOpenAI)

    config = {
        "models": {
            "model_name": "generalv3.5",
            "api_key": "test-key",
            "base_url": "https://spark-api-open.xf-yun.com/v1/chat/completions",
            "concurrency": 7,
            "timeout": 120,
            "max_retries": 1,
        }
    }

    def _fake_get(path: str, default=None):
        if path == "models":
            return config["models"]
        if path == "models.vision":
            return {}
        return default

    monkeypatch.setattr(llm_module, "get", _fake_get)

    llm = Llm()

    assert llm._text_model.model_name == "generalv3.5"
    assert llm._text_model.base_url == "https://spark-api-open.xf-yun.com/v1"
    assert not hasattr(llm, "_text_semaphore")


def test_model_exposes_default_text_model(llm_with_fake_model) -> None:
    llm, fake = llm_with_fake_model

    assert llm.model is fake


def test_bind_tools_is_not_part_of_gateway_interface(llm_with_fake_model) -> None:
    llm, _fake = llm_with_fake_model

    assert not hasattr(llm, "bind_tools")


@pytest.mark.asyncio
async def test_ainvoke_uses_async_text_model(llm_with_fake_model) -> None:
    llm, fake = llm_with_fake_model

    response = await llm.ainvoke("hello", temperature=0.7, max_tokens=100)

    assert response.content == "ok"
    assert fake.bind_calls == [{"temperature": 0.7, "max_tokens": 100}]


@pytest.mark.asyncio
async def test_ainvoke_accepts_prebound_langchain_model(llm_with_fake_model) -> None:
    llm, fake = llm_with_fake_model
    tool_model = fake.bind_tools(["search_tool"])

    response = await llm.ainvoke("hello", model=tool_model)

    assert response.tool_calls == []
    assert tool_model.invocations == ["hello"]
    assert fake.bound_tools == ["search_tool"]


@pytest.mark.asyncio
async def test_astream_uses_async_streaming_model(llm_with_fake_model) -> None:
    llm, fake = llm_with_fake_model

    chunks = []
    async for chunk in llm.astream("hello", temperature=0.2):
        chunks.append(chunk)

    assert chunks == ["chunk-1", "chunk-2"]
    assert fake.bind_calls == [{"temperature": 0.2}]


@pytest.mark.asyncio
async def test_astream_accepts_prebound_langchain_model(llm_with_fake_model) -> None:
    llm, fake = llm_with_fake_model
    tool_model = fake.bind_tools(["search_tool"])

    chunks = []
    async for chunk in llm.astream("hello", model=tool_model):
        chunks.append(chunk)

    assert chunks == ["tool-chunk-1", "tool-chunk-2"]
    assert tool_model.invocations == ["hello"]


@pytest.mark.asyncio
async def test_ainvoke_json_accepts_tool_args_json_string() -> None:
    llm = Llm()
    fake = _FakeModel(
        tool_calls=[{"name": "submit_score", "args": '{"name": "Alice", "score": 92}'}]
    )
    llm._text_model = fake


    result = await llm.ainvoke_json(
        _Payload,
        "input",
        function_name="submit_score",
    )

    assert result == _Payload(name="Alice", score=92)


@pytest.mark.asyncio
async def test_ainvoke_json_selects_matching_tool_call() -> None:
    llm = Llm()
    fake = _FakeModel(
        tool_calls=[
            {"name": "wrong_tool", "args": {"name": "Wrong", "score": 1}},
            {"name": "submit_score", "args": {"name": "Bob", "score": 88}},
        ]
    )
    llm._text_model = fake


    result = await llm.ainvoke_json(
        _Payload,
        "input",
        function_name="submit_score",
    )

    assert result == _Payload(name="Bob", score=88)


class _MockNestedInstruction(BaseModel):
    agent_id: str
    focus: str
    constraints: list[str] = Field(default_factory=list)

class _MockNestedBlueprint(BaseModel):
    topic: str
    learner_goal: str
    core_concepts: list[str] = Field(default_factory=list)

class _MockExecutionPlan(BaseModel):
    blueprint: _MockNestedBlueprint
    agent_instructions: list[_MockNestedInstruction]
    personalization_summary: str

@pytest.mark.asyncio
async def test_ainvoke_json_parses_nested_stringified_json_fields() -> None:
    llm = Llm()
    fake = _FakeModel(
        tool_calls=[
            {
                "name": "_MockExecutionPlan",
                "args": {
                    "blueprint": '蓝图如下:\n{"topic":"TCP三次握手","learner_goal":"理解连接建立过程","core_concepts":["SYN","ACK"]}',
                    "agent_instructions": [
                        {
                            "agent_id": "reading",
                            "focus": "重点解释为什么需要三次握手",
                            "constraints": ["先讲 SYN 和 ACK 的作用"],
                        }
                    ],
                    "personalization_summary": "优先补齐基础概念",
                },
            }
        ]
    )
    llm._text_model = fake


    result = await llm.ainvoke_json(_MockExecutionPlan, "input")

    assert result.blueprint.topic == "TCP三次握手"
    assert result.blueprint.learner_goal == "理解连接建立过程"
    assert result.blueprint.core_concepts == ["SYN", "ACK"]
    assert result.agent_instructions[0].agent_id == "reading"


@pytest.mark.asyncio
async def test_ainvoke_json_falls_back_to_json_text() -> None:
    llm = Llm()
    fake = _FakeModel(text='说明文字\n{"name": "Cara", "score": 95}\n结束')
    llm._text_model = fake


    result = await llm.ainvoke_json(
        _Payload,
        "input",
        function_name="submit_score",
    )

    assert result == _Payload(name="Cara", score=95)
    assert fake.bind_calls[-1] == {"response_format": {"type": "json_object"}}


@pytest.mark.asyncio
async def test_ainvoke_json_can_prefer_json_mode_first() -> None:
    llm = Llm()
    fake = _FakeModel(text='{"name": "Eve", "score": 99}')
    llm._text_model = fake

    llm._structured_output_strategy = "json_first"

    result = await llm.ainvoke_json(
        _Payload,
        "input",
        function_name="submit_score",
    )

    assert result == _Payload(name="Eve", score=99)
    assert fake.bind_calls[-1] == {"response_format": {"type": "json_object"}}
    assert fake.bound_tools is None
    assert len(fake.invocations) == 1


@pytest.mark.asyncio
async def test_ainvoke_json_falls_back_when_tool_binding_fails() -> None:
    llm = Llm()
    fake = _FakeModel(
        text='{"name": "Dana", "score": 90}',
        fail_tools=True,
    )
    llm._text_model = fake


    result = await llm.ainvoke_json(
        _Payload,
        "input",
        function_name="submit_score",
    )

    assert result == _Payload(name="Dana", score=90)


@pytest.mark.asyncio
async def test_ainvoke_json_raises_diagnostic_error_when_all_paths_fail() -> None:
    llm = Llm()
    fake = _FakeModel(text="not json")
    llm._text_model = fake


    with pytest.raises(ServiceError) as exc_info:
        await llm.ainvoke_json(
            _Payload,
            "input",
            function_name="submit_score",
        )

    assert "[_Payload]" in str(exc_info.value)


def test_llm_does_not_read_or_create_concurrency_limit(monkeypatch) -> None:
    monkeypatch.setattr(llm_module, "ChatOpenAI", _CapturedChatOpenAI)

    config = {
        "models": {
            "model_name": "generalv3.5",
            "api_key": "test-key",
            "base_url": "https://spark-api-open.xf-yun.com/v1/chat/completions",
            "concurrency": 7,
            "timeout": 120,
            "max_retries": 1,
        }
    }

    def _fake_get(path: str, default=None):
        if path == "models":
            return config["models"]
        if path == "models.vision":
            return {}
        return default

    monkeypatch.setattr(llm_module, "get", _fake_get)

    llm = Llm()

    assert not hasattr(llm, "_text_semaphore")


def test_spark_compatible_tool_call_normalization():
    from app.infra.llm import SparkCompatibleChatOpenAI
    from unittest.mock import MagicMock
    from langchain_openai import ChatOpenAI
    
    model = SparkCompatibleChatOpenAI(api_key="mock", model="generalv3")
    
    # Mock raw message with a dict in tool_calls
    mock_msg = MagicMock()
    mock_msg.tool_calls = {
        "type": "function",
        "function": {"name": "test_tool", "arguments": "{}"}
    }
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    
    # Mock the super()._create_chat_result to prevent actual OpenAI processing
    original_super = ChatOpenAI._create_chat_result
    ChatOpenAI._create_chat_result = lambda self, r, g=None: r
    
    try:
        result = model._create_chat_result(mock_response)
    finally:
        ChatOpenAI._create_chat_result = original_super
    
    # Should normalize tool_calls to list and add id
    normalized = result.choices[0].message.tool_calls
    assert isinstance(normalized, list)
    assert len(normalized) == 1
    assert normalized[0]["type"] == "function"
    assert "id" in normalized[0]


