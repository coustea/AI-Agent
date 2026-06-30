# -*- coding: utf-8 -*-
"""Tests for the OpenAI-compatible LLM gateway."""

from __future__ import annotations

from typing import Any

import pytest
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

import app.infra.llm as llm_module
from app.infra.llm import Llm
from app.infra.utils import ServiceError


class _Payload(BaseModel):
    name: str
    score: int


class _TextResponse:
    def __init__(self, content: str) -> None:
        self.content = content
        self.tool_calls: list[dict[str, Any]] = []


class _FakeModel:
    def __init__(
        self,
        *,
        text: str = "ok",
        fail_json_mode: bool = False,
    ) -> None:
        self.text_response = _TextResponse(text)
        self.fail_json_mode = fail_json_mode
        self.bind_calls: list[dict[str, Any]] = []
        self.invocations: list[Any] = []

    def bind(self, **kwargs: Any):
        self.bind_calls.append(kwargs)
        if kwargs.get("response_format") and self.fail_json_mode:
            raise RuntimeError("response_format unsupported")
        return self

    def bind_tools(self, tools: list[Any], *, tool_choice: Any | None = None):
        return _FakeRunnable(_TextResponse(""))

    async def ainvoke(self, input_data: Any, **_kwargs: Any) -> _TextResponse:
        self.invocations.append(input_data)
        return self.text_response

    async def astream(self, input_data: Any, **_kwargs: Any):
        self.invocations.append(input_data)
        yield "chunk-1"
        yield "chunk-2"


class _FakeRunnable:
    def __init__(self, response: Any) -> None:
        self.response = response

    async def ainvoke(self, input_data: Any, **_kwargs: Any) -> Any:
        return self.response


class _CapturedChatModel:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.model_name = kwargs.get("model")
        self.base_url = str(kwargs.get("base_url"))


@pytest.fixture
def llm_with_fake() -> tuple[Llm, _FakeModel]:
    llm = Llm()
    fake = _FakeModel()
    llm._text_model = fake
    llm.text_config = llm_module.ChatModelConfig(
        base_url="https://example.com/v1",
        api_key="test-key",
        model_name="test-model",
        temperature=0.3,
        max_tokens=4096,
        timeout=300,
        max_retries=2,
    )
    return llm, fake


def test_loads_text_model_from_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm_module, "ChatModel", _CapturedChatModel)

    config = {
        "models": {
            "base_url": "https://api.deepseek.com/v1",
            "api_key": "test-key",
            "model_name": "deepseek-chat",
            "temperature": 0.2,
            "max_tokens": 2048,
            "timeout": 120,
            "max_retries": 1,
            "model_kwargs": {"top_p": 0.8},
            "extra_body": {"custom": "value"},
            "default_headers": {"X-Test": "1"},
        }
    }

    def fake_get(path: str, default: Any = None) -> Any:
        if path == "models":
            return config["models"]
        if path == "models.vision":
            return {}
        return default

    monkeypatch.setattr(llm_module, "get", fake_get)
    llm = Llm()

    assert llm._text_model.model_name == "deepseek-chat"
    assert llm._text_model.base_url == "https://api.deepseek.com/v1"
    assert llm._text_model.kwargs["temperature"] == 0.2
    assert llm._text_model.kwargs["max_tokens"] == 2048
    assert llm._text_model.kwargs["model_kwargs"] == {"top_p": 0.8}
    assert llm._text_model.kwargs["extra_body"] == {"custom": "value"}
    assert llm._text_model.kwargs["default_headers"] == {"X-Test": "1"}


def test_normalizes_chat_completions_base_url() -> None:
    assert llm_module._normalize_base_url("https://spark-api-open.xf-yun.com/v1/chat/completions") == "https://spark-api-open.xf-yun.com/v1"
    assert llm_module._normalize_base_url("https://open.bigmodel.cn/api/paas/v4/") == "https://open.bigmodel.cn/api/paas/v4"


@pytest.mark.asyncio
async def test_ainvoke_binds_runtime_options(llm_with_fake) -> None:
    llm, fake = llm_with_fake
    response = await llm.ainvoke("hello", temperature=0.7, max_tokens=100)
    assert response.content == "ok"
    assert fake.bind_calls == [{"temperature": 0.7, "max_tokens": 100}]


@pytest.mark.asyncio
async def test_astream_yields_chunks(llm_with_fake) -> None:
    llm, fake = llm_with_fake
    chunks = [c async for c in llm.astream("hello", temperature=0.2)]
    assert chunks == ["chunk-1", "chunk-2"]


def test_openai_compatible_model_normalizes_tool_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import MagicMock
    from langchain_openai import ChatOpenAI

    model = llm_module.ChatModel(api_key="mock", model="generalv3")
    raw_tool_call = {
        "type": "function",
        "function": {"name": "submit_score", "arguments": {"name": "Alice", "score": 92}},
    }
    mock_msg = MagicMock()
    mock_msg.tool_calls = raw_tool_call
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    monkeypatch.setattr(ChatOpenAI, "_create_chat_result", lambda self, response, generation_info=None: response)
    result = model._create_chat_result(mock_response)

    normalized = result.choices[0].message.tool_calls
    assert isinstance(normalized, list)
    assert normalized[0]["id"].startswith("call_")
    assert normalized[0]["function"]["arguments"] == '{"name": "Alice", "score": 92}'


@pytest.mark.asyncio
async def test_ainvoke_json_uses_json_mode_first(llm_with_fake) -> None:
    llm, fake = llm_with_fake
    fake.text_response = _TextResponse('{"name": "Alice", "score": 92}')
    result = await llm.ainvoke_json(_Payload, "input")
    assert result == _Payload(name="Alice", score=92)
    assert fake.bind_calls[0] == {"response_format": {"type": "json_object"}}


@pytest.mark.asyncio
async def test_ainvoke_json_retries_json_mode_once(llm_with_fake) -> None:
    llm, fake = llm_with_fake
    fake.text_response = _TextResponse('not json')
    # json_mode will fail to parse, retry also fails, then prompt also fails
    with pytest.raises(ServiceError) as exc_info:
        await llm.ainvoke_json(_Payload, "input")
    # Should show 2 json_mode attempts + 1 prompt attempt
    assert "json_mode(attempt=1)" in str(exc_info.value)
    assert "json_mode(attempt=2)" in str(exc_info.value)
    assert "prompt" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ainvoke_json_falls_back_to_prompt(llm_with_fake) -> None:
    llm, fake = llm_with_fake
    fake.fail_json_mode = True
    # bind(response_format) raises, so json_mode fails, prompt fallback succeeds
    fake.text_response = _TextResponse('{"name": "Bob", "score": 88}')
    result = await llm.ainvoke_json(_Payload, "input")
    assert result == _Payload(name="Bob", score=88)


@pytest.mark.asyncio
async def test_vision_uses_vision_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm_module, "ChatModel", _CapturedChatModel)

    config = {
        "models": {
            "base_url": "https://spark-api-open.xf-yun.com/v1",
            "api_key": "text-key",
            "model_name": "generalv3",
            "vision": {
                "base_url": "https://open.bigmodel.cn/api/paas/v4/",
                "api_key": "vision-key",
                "model_name": "glm-4.6v-flash",
                "temperature": 0.7,
            },
        }
    }

    def fake_get(path: str, default: Any = None) -> Any:
        if path == "models":
            return config["models"]
        if path == "models.vision":
            return config["models"]["vision"]
        return default

    monkeypatch.setattr(llm_module, "get", fake_get)
    llm = Llm()
    vision_fake = _FakeModel(text="vision ok")
    llm._vision_model = vision_fake

    response = await llm.vision("image message", temperature=0.4)
    assert response.content == "vision ok"
    assert llm.vision_config is not None
