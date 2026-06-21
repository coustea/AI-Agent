# OpenAI-Compatible LLM Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild `server/app/infra/llm.py` as a provider-agnostic LangChain `ChatOpenAI` gateway that loads OpenAI-compatible models from `server/config.yaml`, supports async invoke, streaming, tool calling, structured JSON output, and vision.

**Architecture:** The gateway keeps only the public surface currently used by business code: `get_llm()`, `Llm.model`, `ainvoke()`, `astream()`, `ainvoke_tools()`, `ainvoke_json()`, and `vision()`. All internal implementation is rewritten around a typed `ChatModelConfig`, a generic `OpenAICompatibleChatModel` subclass, and strategy-based structured output. Spark is handled as one provider compatibility case, not as the architecture.

**Tech Stack:** Python 3.13, FastAPI config module, LangChain `langchain_openai.ChatOpenAI`, LangChain core messages, Pydantic v2, pytest, pytest-asyncio.

---

## File Structure

- Modify: `server/app/infra/llm.py`
  - Owns all model config loading, `ChatOpenAI` construction, runtime binding, invocation methods, and JSON parsing.
  - This task intentionally rewrites the file. Do not preserve old private helper names, old benchmark aliases, or `SparkCompatibleChatOpenAI`.
- Modify: `server/tests/infra/test_llm_gateway.py`
  - Replace old tests with focused gateway tests for the new public API and new internal design.
- Modify: `server/tests/test_spark_structured_output.py`
  - Optional small cleanup only if needed: import the new generic model class or `Llm`; do not require this test in default CI because it needs a real API key.
- No frontend files are touched.
- No backend business-domain files are touched unless a test exposes a real public API mismatch.

## Public API Contract

Keep these stable for existing callers:

```python
get_llm()
Llm.model
await Llm.ainvoke(input_data, *, model=None, temperature=None, max_tokens=None)
async for chunk in Llm.astream(input_data, *, model=None, temperature=None, max_tokens=None)
await Llm.ainvoke_tools(input_data, tools, *, tool_choice=None, temperature=None, max_tokens=None)
await Llm.ainvoke_json(schema, input_data, *, temperature=None, max_tokens=None, function_name=None, function_description=None)
await Llm.vision(input_data, *, temperature=None, max_tokens=None)
```

Remove all compatibility for old private names:

```python
SparkCompatibleChatOpenAI
_collect_schema_root_candidates
_iter_json_objects
```

---

### Task 1: Rewrite Gateway Tests Around the New Contract

**Files:**
- Modify: `server/tests/infra/test_llm_gateway.py`

- [ ] **Step 1: Replace the test file with focused fake-model tests**

Replace the entire contents of `server/tests/infra/test_llm_gateway.py` with:

```python
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


class _ToolResponse:
    def __init__(self, tool_calls: list[dict[str, Any]], content: str = "") -> None:
        self.tool_calls = tool_calls
        self.content = content


class _FakeRunnable:
    def __init__(self, response: Any, chunks: list[Any] | None = None) -> None:
        self.response = response
        self.chunks = chunks or []
        self.invocations: list[Any] = []

    async def ainvoke(self, input_data: Any, **_kwargs: Any) -> Any:
        self.invocations.append(input_data)
        return self.response

    async def astream(self, input_data: Any, **_kwargs: Any):
        self.invocations.append(input_data)
        for chunk in self.chunks:
            yield chunk


class _FakeModel:
    def __init__(
        self,
        *,
        text: str = "ok",
        tool_calls: list[dict[str, Any]] | None = None,
        chunks: list[Any] | None = None,
        fail_bind_tools: bool = False,
        fail_json_mode: bool = False,
    ) -> None:
        self.text_response = _TextResponse(text)
        self.tool_response = _ToolResponse(tool_calls or [])
        self.chunks = chunks or ["chunk-1", "chunk-2"]
        self.fail_bind_tools = fail_bind_tools
        self.fail_json_mode = fail_json_mode
        self.bind_calls: list[dict[str, Any]] = []
        self.bound_tools: list[Any] | None = None
        self.tool_choice: Any | None = None
        self.invocations: list[Any] = []

    def bind(self, **kwargs: Any):
        self.bind_calls.append(kwargs)
        if kwargs.get("response_format") and self.fail_json_mode:
            raise RuntimeError("response_format unsupported")
        return self

    def bind_tools(self, tools: list[Any], *, tool_choice: Any | None = None):
        if self.fail_bind_tools:
            raise RuntimeError("tool calling unsupported")
        self.bound_tools = tools
        self.tool_choice = tool_choice
        return _FakeRunnable(self.tool_response, chunks=["tool-chunk"])

    async def ainvoke(self, input_data: Any, **_kwargs: Any) -> _TextResponse:
        self.invocations.append(input_data)
        return self.text_response

    async def astream(self, input_data: Any, **_kwargs: Any):
        self.invocations.append(input_data)
        for chunk in self.chunks:
            yield chunk


class _CapturedChatModel:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.model_name = kwargs.get("model")
        self.base_url = str(kwargs.get("base_url"))


@pytest.fixture
def llm_with_fake_model() -> tuple[Llm, _FakeModel]:
    llm = Llm()
    fake = _FakeModel()
    llm._text_model = fake
    llm.text_config = llm_module.ChatModelConfig(
        provider="custom",
        base_url="https://example.com/v1",
        api_key="test-key",
        model_name="test-model",
        temperature=0.3,
        max_tokens=4096,
        timeout=300,
        max_retries=2,
        structured_output_strategy="auto",
        model_kwargs={},
        extra_body={},
        default_headers={},
    )
    return llm, fake


def test_loads_text_model_from_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm_module, "OpenAICompatibleChatModel", _CapturedChatModel)

    config = {
        "models": {
            "provider": "deepseek",
            "base_url": "https://api.deepseek.com/v1",
            "api_key": "test-key",
            "model_name": "deepseek-chat",
            "temperature": 0.2,
            "max_tokens": 2048,
            "timeout": 120,
            "max_retries": 1,
            "structured_output_strategy": "json_mode_first",
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

    assert llm.text_config.provider == "deepseek"
    assert llm._text_model.model_name == "deepseek-chat"
    assert llm._text_model.base_url == "https://api.deepseek.com/v1"
    assert llm._text_model.kwargs["temperature"] == 0.2
    assert llm._text_model.kwargs["max_tokens"] == 2048
    assert llm._text_model.kwargs["timeout"] == 120
    assert llm._text_model.kwargs["max_retries"] == 1
    assert llm._text_model.kwargs["model_kwargs"] == {"top_p": 0.8}
    assert llm._text_model.kwargs["extra_body"] == {"custom": "value"}
    assert llm._text_model.kwargs["default_headers"] == {"X-Test": "1"}


def test_normalizes_chat_completions_base_url() -> None:
    assert (
        llm_module._normalize_base_url("https://spark-api-open.xf-yun.com/v1/chat/completions")
        == "https://spark-api-open.xf-yun.com/v1"
    )
    assert (
        llm_module._normalize_base_url("https://open.bigmodel.cn/api/paas/v4/")
        == "https://open.bigmodel.cn/api/paas/v4"
    )


@pytest.mark.asyncio
async def test_ainvoke_binds_runtime_temperature_and_max_tokens(llm_with_fake_model) -> None:
    llm, fake = llm_with_fake_model

    response = await llm.ainvoke("hello", temperature=0.7, max_tokens=100)

    assert response.content == "ok"
    assert fake.bind_calls == [{"temperature": 0.7, "max_tokens": 100}]
    assert fake.invocations == ["hello"]


@pytest.mark.asyncio
async def test_astream_yields_chunks(llm_with_fake_model) -> None:
    llm, fake = llm_with_fake_model

    chunks = [chunk async for chunk in llm.astream("hello", temperature=0.2)]

    assert chunks == ["chunk-1", "chunk-2"]
    assert fake.bind_calls == [{"temperature": 0.2}]
    assert fake.invocations == ["hello"]


@pytest.mark.asyncio
async def test_ainvoke_tools_uses_langchain_bind_tools(llm_with_fake_model) -> None:
    llm, fake = llm_with_fake_model

    response = await llm.ainvoke_tools(
        [HumanMessage(content="search")],
        tools=["search_tool"],
        tool_choice="auto",
        max_tokens=1000,
    )

    assert response.tool_calls == []
    assert fake.bound_tools == ["search_tool"]
    assert fake.tool_choice == "auto"
    assert fake.bind_calls == [{"max_tokens": 1000}]


def test_openai_compatible_model_normalizes_nonstandard_tool_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import MagicMock
    from langchain_openai import ChatOpenAI

    model = llm_module.OpenAICompatibleChatModel(api_key="mock", model="generalv3")

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
async def test_ainvoke_json_prompt_first_parses_schema(llm_with_fake_model) -> None:
    llm, fake = llm_with_fake_model
    fake.text_response = _TextResponse('说明文字 {"name": "Alice", "score": 92}')
    llm.text_config = llm.text_config.model_copy(update={"structured_output_strategy": "prompt_first"})

    result = await llm.ainvoke_json(_Payload, "input")

    assert result == _Payload(name="Alice", score=92)
    assert fake.invocations


@pytest.mark.asyncio
async def test_ainvoke_json_json_mode_falls_back_to_prompt(llm_with_fake_model) -> None:
    llm, fake = llm_with_fake_model
    fake.fail_json_mode = True
    fake.text_response = _TextResponse('{"name": "Bob", "score": 88}')
    llm.text_config = llm.text_config.model_copy(update={"structured_output_strategy": "json_mode_first"})

    result = await llm.ainvoke_json(_Payload, "input")

    assert result == _Payload(name="Bob", score=88)
    assert fake.bind_calls[0] == {"response_format": {"type": "json_object"}}


@pytest.mark.asyncio
async def test_ainvoke_json_tool_first_parses_tool_args(llm_with_fake_model) -> None:
    llm, fake = llm_with_fake_model
    fake.tool_response = _ToolResponse([
        {"name": "submit_score", "args": '{"name": "Cara", "score": 95}'}
    ])
    llm.text_config = llm.text_config.model_copy(update={"structured_output_strategy": "tool_first"})

    result = await llm.ainvoke_json(_Payload, "input", function_name="submit_score")

    assert result == _Payload(name="Cara", score=95)
    assert fake.bound_tools is not None
    assert fake.tool_choice == {"type": "function", "function": {"name": "submit_score"}}


@pytest.mark.asyncio
async def test_ainvoke_json_raises_service_error_when_all_strategies_fail(llm_with_fake_model) -> None:
    llm, fake = llm_with_fake_model
    fake.fail_json_mode = True
    fake.fail_bind_tools = True
    fake.text_response = _TextResponse("not json")
    llm.text_config = llm.text_config.model_copy(update={"structured_output_strategy": "json_mode_first"})

    with pytest.raises(ServiceError) as exc_info:
        await llm.ainvoke_json(_Payload, "input")

    assert "[_Payload]" in str(exc_info.value)


@pytest.mark.asyncio
async def test_vision_uses_vision_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm_module, "OpenAICompatibleChatModel", _CapturedChatModel)

    config = {
        "models": {
            "provider": "spark",
            "base_url": "https://spark-api-open.xf-yun.com/v1",
            "api_key": "text-key",
            "model_name": "generalv3",
            "vision": {
                "provider": "glm",
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
    assert llm.vision_config.provider == "glm"
    assert vision_fake.bind_calls == [{"temperature": 0.4}]
```

- [ ] **Step 2: Run the rewritten tests to verify they fail before implementation**

Run:

```bash
cd /Users/apple/Code/software/server
rtk uv run pytest tests/infra/test_llm_gateway.py -q
```

Expected: FAIL with import/attribute errors such as `ChatModelConfig` or `OpenAICompatibleChatModel` not existing yet.

- [ ] **Step 3: Commit the red tests**

```bash
cd /Users/apple/Code/software
git add server/tests/infra/test_llm_gateway.py
git commit -m "test: define openai-compatible llm gateway contract"
```

---

### Task 2: Replace `llm.py` With Config Loading and Model Construction

**Files:**
- Modify: `server/app/infra/llm.py`
- Test: `server/tests/infra/test_llm_gateway.py`

- [ ] **Step 1: Replace `llm.py` with the new module foundation**

Replace the entire contents of `server/app/infra/llm.py` with:

```python
"""OpenAI-compatible LLM gateway.

The gateway is provider-agnostic: Spark, DeepSeek, GLM, OpenAI, and local
OpenAI-compatible servers are all loaded through LangChain's ChatOpenAI.
Provider-specific quirks are isolated to the generic compatibility subclass.
"""

from __future__ import annotations

import copy
import json
import time
import uuid
from functools import lru_cache
from typing import Any, AsyncIterator

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.config import INFERENCE_TEMPERATURE, VISION_TEMPERATURE, get
from app.infra.logging import get_logger
from app.infra.utils import ServiceError, parse_first_json_object, parse_first_json_value, strip_markdown_code_fences

logger = get_logger(__name__)


class ChatModelConfig(BaseModel):
    """Runtime config for any OpenAI-compatible chat model."""

    provider: str = "custom"
    base_url: str
    api_key: str
    model_name: str
    temperature: float = INFERENCE_TEMPERATURE
    max_tokens: int | None = None
    timeout: float = 300
    max_retries: int = 2
    structured_output_strategy: str = "auto"
    model_kwargs: dict[str, Any] = Field(default_factory=dict)
    extra_body: dict[str, Any] = Field(default_factory=dict)
    default_headers: dict[str, str] = Field(default_factory=dict)


class OpenAICompatibleChatModel(ChatOpenAI):
    """ChatOpenAI with defensive normalization for OpenAI-compatible providers."""

    def _create_chat_result(self, response: Any, generation_info: Any | None = None) -> Any:
        try:
            _normalize_response_tool_calls(response)
        except Exception as exc:
            logger.warning("[LLM] tool_calls normalization failed: %s", exc)
        return super()._create_chat_result(response, generation_info)


def _normalize_response_tool_calls(response: Any) -> None:
    choices = getattr(response, "choices", None) or []
    for choice in choices:
        message = getattr(choice, "message", None)
        if message is None or not hasattr(message, "tool_calls"):
            continue
        tool_calls = getattr(message, "tool_calls")
        if tool_calls is None:
            continue
        normalized = [_normalize_raw_tool_call(tool_calls)] if isinstance(tool_calls, dict) else [
            _normalize_raw_tool_call(tool_call) for tool_call in tool_calls
        ]
        object.__setattr__(message, "tool_calls", normalized)


def _normalize_raw_tool_call(tool_call: Any) -> Any:
    if not isinstance(tool_call, dict):
        return tool_call
    normalized = copy.deepcopy(tool_call)
    if not normalized.get("id"):
        normalized["id"] = f"call_{uuid.uuid4().hex[:12]}"
    function = normalized.get("function")
    if isinstance(function, dict) and isinstance(function.get("arguments"), (dict, list)):
        function["arguments"] = json.dumps(function["arguments"], ensure_ascii=False)
    return normalized


def _normalize_base_url(base_url: str) -> str:
    normalized = (base_url or "").strip().rstrip("/")
    suffix = "/chat/completions"
    if normalized.endswith(suffix):
        normalized = normalized[: -len(suffix)]
    return normalized.rstrip("/")


def _load_chat_config(path: str) -> ChatModelConfig | None:
    raw = get(path, {}) or {}
    if not isinstance(raw, dict) or not raw.get("model_name"):
        return None
    data = {key: value for key, value in raw.items() if key != "vision"}
    if not data.get("base_url") or not data.get("api_key"):
        raise ServiceError(f"{path} 模型配置缺少 base_url 或 api_key")
    return ChatModelConfig(
        provider=str(data.get("provider") or "custom").lower(),
        base_url=_normalize_base_url(str(data["base_url"])),
        api_key=str(data["api_key"]),
        model_name=str(data["model_name"]),
        temperature=float(data.get("temperature", INFERENCE_TEMPERATURE)),
        max_tokens=data.get("max_tokens"),
        timeout=float(data.get("timeout", 300)),
        max_retries=int(data.get("max_retries", 2)),
        structured_output_strategy=str(data.get("structured_output_strategy", "auto")),
        model_kwargs=dict(data.get("model_kwargs") or {}),
        extra_body=dict(data.get("extra_body") or {}),
        default_headers=dict(data.get("default_headers") or {}),
    )


def _create_chat_model(config: ChatModelConfig, *, streaming: bool = False) -> OpenAICompatibleChatModel:
    kwargs: dict[str, Any] = {
        "model": config.model_name,
        "api_key": config.api_key,
        "base_url": config.base_url,
        "temperature": config.temperature,
        "streaming": streaming,
        "timeout": config.timeout,
        "max_retries": config.max_retries,
        "model_kwargs": config.model_kwargs,
    }
    if config.max_tokens is not None:
        kwargs["max_tokens"] = config.max_tokens
    if config.extra_body:
        kwargs["extra_body"] = config.extra_body
    if config.default_headers:
        kwargs["default_headers"] = config.default_headers
    return OpenAICompatibleChatModel(**kwargs)
```

- [ ] **Step 2: Run config/model tests**

Run:

```bash
cd /Users/apple/Code/software/server
rtk uv run pytest \
  tests/infra/test_llm_gateway.py::test_loads_text_model_from_config \
  tests/infra/test_llm_gateway.py::test_normalizes_chat_completions_base_url \
  tests/infra/test_llm_gateway.py::test_openai_compatible_model_normalizes_nonstandard_tool_calls \
  -q
```

Expected: PASS for the three selected tests, while later tests still fail because `Llm` is not implemented yet.

- [ ] **Step 3: Commit config/model foundation**

```bash
cd /Users/apple/Code/software
git add server/app/infra/llm.py server/tests/infra/test_llm_gateway.py
git commit -m "refactor: add openai-compatible llm model foundation"
```

---

### Task 3: Add `Llm` Core Invocation Methods

**Files:**
- Modify: `server/app/infra/llm.py`
- Test: `server/tests/infra/test_llm_gateway.py`

- [ ] **Step 1: Append runtime binding and the `Llm` class**

Append this code to `server/app/infra/llm.py`:

```python
def _bind_runtime_options(
    model: Any,
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> Any:
    bind_kwargs: dict[str, Any] = {}
    if temperature is not None:
        bind_kwargs["temperature"] = temperature
    if max_tokens is not None:
        bind_kwargs["max_tokens"] = max_tokens
    return model.bind(**bind_kwargs) if bind_kwargs else model


class Llm:
    """Unified async gateway around a configured OpenAI-compatible chat model."""

    def __init__(self) -> None:
        self.text_config = _load_chat_config("models")
        self.vision_config = _load_chat_config("models.vision")
        self._text_model = _create_chat_model(self.text_config) if self.text_config else None
        self._vision_model = _create_chat_model(self.vision_config) if self.vision_config else None

    @property
    def model(self) -> Any:
        if self._text_model is None:
            raise ServiceError("文本模型配置缺失")
        return self._text_model

    async def ainvoke(
        self,
        input_data: Any,
        *,
        model: Any | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Any:
        runnable = _bind_runtime_options(model or self.model, temperature=temperature, max_tokens=max_tokens)
        return await runnable.ainvoke(input_data)

    async def astream(
        self,
        input_data: Any,
        *,
        model: Any | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[Any]:
        runnable = _bind_runtime_options(model or self.model, temperature=temperature, max_tokens=max_tokens)
        async for chunk in runnable.astream(input_data):
            yield chunk

    async def ainvoke_tools(
        self,
        input_data: Any,
        tools: list[Any],
        *,
        tool_choice: Any | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Any:
        model = _bind_runtime_options(self.model, temperature=temperature, max_tokens=max_tokens)
        if tool_choice is None:
            runnable = model.bind_tools(tools)
        else:
            runnable = model.bind_tools(tools, tool_choice=tool_choice)
        return await runnable.ainvoke(input_data)

    async def vision(
        self,
        input_data: Any,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Any:
        if self._vision_model is None:
            raise ServiceError("图片理解模型配置缺失")
        runnable = _bind_runtime_options(self._vision_model, temperature=temperature, max_tokens=max_tokens)
        return await runnable.ainvoke(input_data)
```

- [ ] **Step 2: Run core invocation tests**

Run:

```bash
cd /Users/apple/Code/software/server
rtk uv run pytest \
  tests/infra/test_llm_gateway.py::test_ainvoke_binds_runtime_temperature_and_max_tokens \
  tests/infra/test_llm_gateway.py::test_astream_yields_chunks \
  tests/infra/test_llm_gateway.py::test_ainvoke_tools_uses_langchain_bind_tools \
  tests/infra/test_llm_gateway.py::test_vision_uses_vision_config \
  -q
```

Expected: PASS for these tests. JSON tests still fail because structured output is not implemented yet.

- [ ] **Step 3: Commit core invocation methods**

```bash
cd /Users/apple/Code/software
git add server/app/infra/llm.py server/tests/infra/test_llm_gateway.py
git commit -m "refactor: add llm async invocation methods"
```

---

### Task 4: Add Structured JSON Output Strategies

**Files:**
- Modify: `server/app/infra/llm.py`
- Test: `server/tests/infra/test_llm_gateway.py`

- [ ] **Step 1: Insert JSON extraction helpers above `class Llm`**

Add this code above `class Llm` in `server/app/infra/llm.py`:

```python
def _schema_required_keys(schema: type[BaseModel]) -> set[str]:
    try:
        required = set(schema.model_json_schema().get("required", []) or [])
    except Exception:
        required = set()
    return required or set(getattr(schema, "model_fields", {}).keys())


def _score_json_candidate(candidate: dict[str, Any], schema: type[BaseModel]) -> int:
    required = _schema_required_keys(schema)
    fields = set(getattr(schema, "model_fields", {}).keys())
    keys = set(candidate.keys())
    return len(required & keys) * 10 + len(fields & keys)


def _deduplicate_json_objects(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        key = json.dumps(item, ensure_ascii=False, sort_keys=True, default=str)
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def _extract_json_objects(text: str) -> list[dict[str, Any]]:
    decoder = json.JSONDecoder()
    content = strip_markdown_code_fences(text or "").strip()
    candidates: list[dict[str, Any]] = []

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            candidates.append(value)
        elif isinstance(value, list):
            candidates.extend(item for item in value if isinstance(item, dict))

    for index, char in enumerate(content):
        if char not in "{[":
            continue
        try:
            value, _ = decoder.raw_decode(content[index:])
        except json.JSONDecodeError:
            continue
        collect(value)
    return _deduplicate_json_objects(candidates)


def _extract_root_candidates(text: str, schema: type[BaseModel]) -> list[dict[str, Any]]:
    required = _schema_required_keys(schema)
    if not required:
        return _extract_json_objects(text)
    return [candidate for candidate in _extract_json_objects(text) if required.issubset(candidate.keys())]


def _flatten_nested_config(data: dict[str, Any], schema: type[BaseModel]) -> dict[str, Any]:
    config = data.get("config")
    if not isinstance(config, dict):
        return data
    fields = set(getattr(schema, "model_fields", {}).keys())
    flattened = dict(data)
    changed = False
    for key, value in config.items():
        if key in fields and key not in flattened:
            flattened[key] = value
            changed = True
    if changed:
        flattened.pop("config", None)
    return flattened


def _clean_nested_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _clean_nested_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean_nested_json(item) for item in value]
    if isinstance(value, str):
        stripped = value.strip()
        if "{" in stripped or "[" in stripped:
            try:
                parsed = parse_first_json_value(stripped)
            except Exception:
                return value
            if isinstance(parsed, (dict, list)):
                return _clean_nested_json(parsed)
    return value


def _parse_json_response(text: str, schema: type[BaseModel]) -> BaseModel:
    candidates = _extract_root_candidates(text, schema) or _extract_json_objects(text)
    if not candidates:
        parsed = parse_first_json_object(text)
        return schema.model_validate(_flatten_nested_config(parsed, schema))

    last_error: Exception | None = None
    for candidate in sorted(candidates, key=lambda item: _score_json_candidate(item, schema), reverse=True):
        try:
            return schema.model_validate(_flatten_nested_config(candidate, schema))
        except Exception as exc:
            last_error = exc
    raise ValueError(f"未找到符合 {schema.__name__} 的 JSON 对象") from last_error


def _simplify_anyof_refs(schema: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(schema)

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            any_of = value.get("anyOf")
            if isinstance(any_of, list) and len(any_of) == 2:
                ref_item = next((item for item in any_of if isinstance(item, dict) and "$ref" in item), None)
                null_item = next((item for item in any_of if isinstance(item, dict) and item.get("type") == "null"), None)
                if ref_item and null_item:
                    keep = {key: item for key, item in value.items() if key != "anyOf"}
                    keep.update(ref_item)
                    value.clear()
                    value.update(keep)
            for child in list(value.values()):
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(result)
    return result


def _messages_with_json_instruction(input_data: Any, schema: type[BaseModel]) -> list[BaseMessage]:
    if isinstance(input_data, str):
        messages: list[BaseMessage] = [HumanMessage(content=input_data)]
    elif isinstance(input_data, BaseMessage):
        messages = [input_data]
    elif isinstance(input_data, list):
        messages = list(input_data)
    else:
        raise ValueError(f"Unsupported input_data type: {type(input_data)}")

    schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False, indent=2)
    required = schema.model_json_schema().get("required", []) or []
    instruction = (
        "\n\n[FORMAT INSTRUCTION]\n"
        "Return exactly one valid JSON object. Do not include markdown fences or explanatory text.\n"
        f"The root object must contain these required fields: {', '.join(required)}.\n"
        f"JSON Schema:\n{schema_json}\n"
    )

    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if isinstance(message, (HumanMessage, SystemMessage)):
            copied = copy.copy(message)
            copied.content = str(message.content or "") + instruction
            messages[index] = copied
            return messages

    messages.insert(0, SystemMessage(content=instruction.strip()))
    return messages


def _resolve_json_strategy(config: ChatModelConfig | None) -> str:
    configured = (config.structured_output_strategy if config else "auto").lower()
    if configured in {"prompt_first", "json_mode_first", "tool_first"}:
        return configured
    provider = (config.provider if config else "custom").lower()
    if provider == "spark":
        return "prompt_first"
    return "json_mode_first"
```

- [ ] **Step 2: Insert JSON methods inside `class Llm` before `vision()`**

Add these methods inside `class Llm`, before `vision()`:

```python
    async def ainvoke_json(
        self,
        schema: type[BaseModel],
        input_data: Any,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        function_name: str | None = None,
        function_description: str | None = None,
    ) -> BaseModel:
        messages = _messages_with_json_instruction(input_data, schema)
        model = _bind_runtime_options(self.model, temperature=temperature, max_tokens=max_tokens)
        strategy = _resolve_json_strategy(self.text_config)
        ordered_tiers = _json_tiers_for_strategy(strategy)
        errors: list[str] = []

        for tier in ordered_tiers:
            started = time.perf_counter()
            try:
                if tier == "prompt":
                    result = await self._invoke_json_via_prompt(model, messages, schema)
                elif tier == "json_mode":
                    result = await self._invoke_json_via_json_mode(model, messages, schema)
                else:
                    result = await self._invoke_json_via_tool(
                        model,
                        messages,
                        schema,
                        function_name or schema.__name__,
                        function_description or f"Return {schema.__name__}",
                    )
                logger.info(
                    "[LLM] ainvoke_json success schema=%s strategy=%s tier=%s duration_ms=%d",
                    schema.__name__,
                    strategy,
                    tier,
                    round((time.perf_counter() - started) * 1000),
                )
                return result
            except Exception as exc:
                errors.append(f"{tier}={type(exc).__name__}: {exc}")
                logger.warning(
                    "[LLM] ainvoke_json tier failed schema=%s strategy=%s tier=%s error=%s",
                    schema.__name__,
                    strategy,
                    tier,
                    exc,
                )

        raise ServiceError(f"[{schema.__name__}] 结构化输出失败: {'; '.join(errors)}")

    async def _invoke_json_via_prompt(
        self,
        model: Any,
        messages: list[BaseMessage],
        schema: type[BaseModel],
    ) -> BaseModel:
        response = await model.ainvoke(messages)
        content = getattr(response, "content", "") or ""
        if not content.strip():
            raise ValueError("prompt mode returned empty content")
        return _parse_json_response(content, schema)

    async def _invoke_json_via_json_mode(
        self,
        model: Any,
        messages: list[BaseMessage],
        schema: type[BaseModel],
    ) -> BaseModel:
        response = await model.bind(response_format={"type": "json_object"}).ainvoke(messages)
        content = getattr(response, "content", "") or ""
        if not content.strip():
            raise ValueError("json mode returned empty content")
        return _parse_json_response(content, schema)

    async def _invoke_json_via_tool(
        self,
        model: Any,
        messages: list[BaseMessage],
        schema: type[BaseModel],
        function_name: str,
        function_description: str,
    ) -> BaseModel:
        tool = {
            "type": "function",
            "function": {
                "name": function_name,
                "description": function_description,
                "parameters": _simplify_anyof_refs(schema.model_json_schema()),
            },
        }
        runnable = model.bind_tools(
            [tool],
            tool_choice={"type": "function", "function": {"name": function_name}},
        )
        response = await runnable.ainvoke(messages)
        for tool_call in getattr(response, "tool_calls", []) or []:
            result = _parse_tool_json_response(tool_call, schema, function_name)
            if result is not None:
                return result
        content = getattr(response, "content", "") or ""
        if content.strip():
            return _parse_json_response(content, schema)
        raise ValueError("tool mode returned no usable tool_calls or content")
```

- [ ] **Step 3: Add helper functions used by JSON methods**

Add this code below `_resolve_json_strategy()`:

```python
def _json_tiers_for_strategy(strategy: str) -> list[str]:
    if strategy == "prompt_first":
        return ["prompt", "json_mode", "tool"]
    if strategy == "tool_first":
        return ["tool", "prompt", "json_mode"]
    return ["json_mode", "prompt", "tool"]


def _parse_tool_json_response(
    tool_call: Any,
    schema: type[BaseModel],
    function_name: str,
) -> BaseModel | None:
    call_name = tool_call.get("name") if isinstance(tool_call, dict) else getattr(tool_call, "name", None)
    if call_name and call_name != function_name:
        return None

    args = tool_call.get("args") if isinstance(tool_call, dict) else getattr(tool_call, "args", None)
    if args is None and isinstance(tool_call, dict):
        function = tool_call.get("function")
        if isinstance(function, dict):
            args = function.get("arguments")
    if not args:
        return None

    if isinstance(args, str):
        args = json.loads(args)
    cleaned = _clean_nested_json(args)
    if not isinstance(cleaned, dict):
        return None
    return schema.model_validate(_flatten_nested_config(cleaned, schema))
```

- [ ] **Step 4: Run structured JSON tests**

Run:

```bash
cd /Users/apple/Code/software/server
rtk uv run pytest \
  tests/infra/test_llm_gateway.py::test_ainvoke_json_prompt_first_parses_schema \
  tests/infra/test_llm_gateway.py::test_ainvoke_json_json_mode_falls_back_to_prompt \
  tests/infra/test_llm_gateway.py::test_ainvoke_json_tool_first_parses_tool_args \
  tests/infra/test_llm_gateway.py::test_ainvoke_json_raises_service_error_when_all_strategies_fail \
  -q
```

Expected: PASS for the four selected tests.

- [ ] **Step 5: Commit structured JSON strategies**

```bash
cd /Users/apple/Code/software
git add server/app/infra/llm.py server/tests/infra/test_llm_gateway.py
git commit -m "refactor: add structured json strategies to llm gateway"
```

---

### Task 5: Add Singleton and Full Verification

**Files:**
- Modify: `server/app/infra/llm.py`
- Test: `server/tests/infra/test_llm_gateway.py`

- [ ] **Step 1: Add `get_llm()` at the bottom of `llm.py`**

Append this code to `server/app/infra/llm.py`:

```python
@lru_cache(maxsize=1)
def get_llm() -> Llm:
    """Return the process-wide LLM gateway singleton."""
    return Llm()
```

- [ ] **Step 2: Run the full gateway test file**

Run:

```bash
cd /Users/apple/Code/software/server
rtk uv run pytest tests/infra/test_llm_gateway.py -q
```

Expected: PASS for all tests in `tests/infra/test_llm_gateway.py`.

- [ ] **Step 3: Run import-sensitive backend tests**

Run:

```bash
cd /Users/apple/Code/software/server
rtk uv run pytest \
  tests/path/test_path_planner_search_tools.py \
  tests/chat/test_teaching_diagram_agent.py \
  tests/resource/test_agent_integration.py \
  -q
```

Expected: PASS. If a failure references removed private names from `llm.py`, update that test to use public API or test-local helpers. Do not reintroduce old private compatibility aliases.

- [ ] **Step 4: Run benchmark utility tests**

Run:

```bash
cd /Users/apple/Code/software/server
rtk uv run pytest tests/infra/test_llm_json_benchmark.py -q
```

Expected: Either PASS after updating `server/scripts/benchmark_llm_json_output.py` to use its own local helper functions, or FAIL only because the script imports removed private helpers. If it fails for removed imports, copy the needed JSON extraction logic into `server/scripts/benchmark_llm_json_output.py` instead of restoring private aliases in `llm.py`.

- [ ] **Step 5: Run optional real Spark probe**

Run only when API access is available:

```bash
cd /Users/apple/Code/software/server
RUN_SPARK_INTEGRATION=1 rtk uv run pytest tests/test_spark_structured_output.py -q -s
```

Expected: The probe prints which structured-output methods Spark supports. Passing this probe is useful but not required for default automated verification.

- [ ] **Step 6: Commit final verification changes**

```bash
cd /Users/apple/Code/software
git add server/app/infra/llm.py server/tests/infra/test_llm_gateway.py server/scripts/benchmark_llm_json_output.py server/tests/test_spark_structured_output.py
git commit -m "refactor: complete openai-compatible llm gateway redesign"
```

Only include `server/scripts/benchmark_llm_json_output.py` and `server/tests/test_spark_structured_output.py` in the commit if they were actually modified.

---

## Self-Review

Spec coverage:

- Generic `ChatOpenAI` loading from `config.yaml`: covered by Tasks 1 and 2.
- Provider-agnostic architecture with stronger Spark compatibility: covered by `OpenAICompatibleChatModel` in Task 2.
- Async non-streaming output: covered by Task 3.
- Async streaming output: covered by Task 3.
- Tool calling: covered by Tasks 3 and 4.
- Structured JSON output: covered by Task 4.
- Vision model loading from `models.vision`: covered by Task 3.
- No old private compatibility: explicitly enforced in File Structure and Task 5.

Placeholder scan:

- No `TBD`, `TODO`, or empty "handle edge cases" instructions remain.
- Every code-changing step includes concrete code.
- Every test step includes exact commands and expected results.

Type consistency:

- `ChatModelConfig` is a Pydantic model because tests use `model_copy`.
- `Llm.text_config` and `Llm.vision_config` names are used consistently.
- JSON strategies are consistently named `prompt_first`, `json_mode_first`, and `tool_first`.
