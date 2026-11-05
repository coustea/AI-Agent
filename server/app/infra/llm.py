"""基础设施层 LLM 网关 —— OpenAI 兼容客户端封装。

提供直接、无冗余的 LLM 调用接口：
- `LLM`: 显式指定 provider/temperature/max_tokens 的模型客户端对象
- `chat_text`: 纯文本生成函数
- `chat_json`: 结构化 JSON 生成函数（带自动重试与修复）
- `chat_stream`: 流式生成生成器（返回 TextDelta / TurnDone）
- `chat_vision`: 多模态图片理解函数
- `get_llm_client`: 获取底层 (AsyncOpenAI, ProviderSpec) 元组
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Sequence
from dataclasses import dataclass
import json
from pathlib import Path
import time
from typing import Any, Literal, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import get
from app.infra.logging import get_logger
from app.infra.utils import ServiceError, parse_first_json_object

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

_JSON_REPAIR_ATTEMPTS = 2


# ===========================================================================
# 基础消息模型
# ===========================================================================


@dataclass(frozen=True, slots=True)
class ToolCall:
    """模型发起的一次工具调用。"""

    id: str
    name: str
    args: dict[str, Any]
    raw_arguments: str = ""

    def __getitem__(self, item: str) -> Any:
        if item == "type":
            return "tool_call"
        return getattr(self, item)


@dataclass(frozen=True, slots=True)
class Message:
    """一条对话消息。"""

    role: Literal["system", "user", "assistant", "tool"]
    content: Any
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None

    def to_openai(self) -> dict[str, Any]:
        """序列化为 OpenAI Chat Completions 的 message 结构。"""
        payload: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_calls:
            payload["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": call.raw_arguments or json.dumps(call.args, ensure_ascii=False),
                    },
                }
                for call in self.tool_calls
            ]
        if self.tool_call_id is not None:
            payload["tool_call_id"] = self.tool_call_id
        return payload

    @classmethod
    def from_openai(cls, message: Any) -> Message:
        """从 OpenAI SDK 的 message 对象反向构造。"""
        calls: list[ToolCall] = []
        for raw in getattr(message, "tool_calls", None) or []:
            function = getattr(raw, "function", None)
            raw_args = str(getattr(function, "arguments", "") or "")
            calls.append(
                ToolCall(
                    id=str(getattr(raw, "id", "") or ""),
                    name=str(getattr(function, "name", "") or ""),
                    args=_parse_arguments(raw_args),
                    raw_arguments=raw_args,
                )
            )
        return cls(
            role=str(getattr(message, "role", "assistant")),  # type: ignore[arg-type]
            content=getattr(message, "content", "") or "",
            tool_calls=tuple(calls),
        )


def SystemMessage(content: Any) -> Message:
    return Message(role="system", content=content)


def HumanMessage(content: Any) -> Message:
    return Message(role="user", content=content)


def AIMessage(content: Any = "", *, tool_calls: Sequence[ToolCall] = ()) -> Message:
    return Message(role="assistant", content=content, tool_calls=tuple(tool_calls))


def ToolMessage(content: Any, *, tool_call_id: str) -> Message:
    return Message(role="tool", content=content, tool_call_id=tool_call_id)


def normalize_messages(input_data: Any) -> list[Message]:
    """将字符串、Message 或消息字典列表归一化为 Message 列表。"""
    if isinstance(input_data, str):
        return [HumanMessage(input_data)]
    if isinstance(input_data, Message):
        return [input_data]
    if isinstance(input_data, list):
        result: list[Message] = []
        for item in input_data:
            if isinstance(item, Message):
                result.append(item)
            elif isinstance(item, str):
                result.append(HumanMessage(item))
            elif isinstance(item, dict):
                role = str(item.get("role", "user")).lower()
                content = item.get("content", "")
                if role == "system":
                    result.append(SystemMessage(content))
                elif role == "assistant":
                    result.append(AIMessage(content))
                elif role == "tool":
                    result.append(ToolMessage(content, tool_call_id=str(item.get("tool_call_id", ""))))
                else:
                    result.append(HumanMessage(content))
            else:
                result.append(HumanMessage(str(item)))
        return result
    raise ValueError(f"Unsupported input_data type: {type(input_data)}")


# ===========================================================================
# 流式事件
# ===========================================================================


@dataclass(frozen=True, slots=True)
class TextDelta:
    """流式文本增量。"""

    text: str


@dataclass(frozen=True, slots=True)
class TurnDone:
    """一轮生成结束。"""

    text: str
    tool_calls: tuple[ToolCall, ...] = ()
    finish_reason: str | None = None


# ===========================================================================
# 网关配置与客户端缓存
# ===========================================================================


@dataclass(frozen=True, slots=True)
class ModelSpec:
    """一个模型的连接配置。"""

    name: str
    base_url: str
    api_key: str
    model_name: str
    timeout: float = 300.0
    max_retries: int = 2


# 兼容别名
ProviderSpec = ModelSpec

_MODELS: dict[str, ModelSpec] = {}
_CLIENTS: dict[str, tuple[AsyncOpenAI, ModelSpec]] = {}


def _load_models() -> dict[str, ModelSpec]:
    global _MODELS
    if _MODELS:
        return _MODELS
    raw = get("models", {}) or {}
    models: dict[str, ModelSpec] = {}
    for name, cfg in raw.items():
        if isinstance(cfg, dict) and "base_url" in cfg and "api_key" in cfg:
            models[name] = ModelSpec(
                name=name,
                base_url=str(cfg["base_url"]).rstrip("/").removesuffix("/chat/completions"),
                api_key=str(cfg["api_key"]),
                model_name=str(cfg.get("model_name", "")),
                timeout=float(cfg.get("timeout", 300.0)),
                max_retries=int(cfg.get("max_retries", 2)),
            )
    if not models:
        raise ServiceError("models 配置为空")
    _MODELS = models
    return _MODELS


def get_llm_client(model: str = "text") -> tuple[AsyncOpenAI, ModelSpec]:
    """按模型名称 ('text' 或 'vision') 获取底层 AsyncOpenAI 客户端及 ModelSpec。"""
    normalized_name = "text" if model in {"text", "main"} else model
    cached = _CLIENTS.get(normalized_name)
    if cached is not None:
        return cached

    models = _load_models()
    spec = models.get(normalized_name)
    if spec is None:
        spec = next(iter(models.values()))

    client = AsyncOpenAI(
        api_key=spec.api_key,
        base_url=spec.base_url,
        timeout=spec.timeout,
        max_retries=spec.max_retries,
    )
    pair = (client, spec)
    _CLIENTS[normalized_name] = pair
    return pair


# ===========================================================================
# LLM 核心接口类
# ===========================================================================


class LLM:
    """通用 LLM 调用接口类。显式传入生成参数，无全局 profile 间接层。"""

    __slots__ = ("max_tokens", "provider", "temperature", "timeout")

    def __init__(
        self,
        *,
        provider: str = "text",
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> None:
        self.provider = provider
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    def _build_payload(
        self,
        messages: list[Message],
        *,
        stream: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> tuple[AsyncOpenAI, dict[str, Any]]:
        client, spec = get_llm_client(self.provider)
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens
        payload: dict[str, Any] = {
            "model": spec.model_name,
            "messages": [m.to_openai() for m in messages],
            "temperature": temp,
        }
        if tokens is not None:
            payload["max_tokens"] = tokens
        if self.timeout is not None:
            payload["timeout"] = self.timeout
        if stream:
            payload["stream"] = True
        return client, payload

    async def _complete(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> tuple[Message, Any]:
        client, payload = self._build_payload(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        payload.update(kwargs)
        response = await client.chat.completions.create(**payload)
        usage = getattr(response, "usage", None)
        return Message.from_openai(response.choices[0].message), usage

    async def text(
        self,
        messages: Any,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """生成纯文本。"""
        norm_msgs = normalize_messages(messages)
        message, _ = await self._complete(
            norm_msgs,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = _extract_message_text(message)
        if not content:
            raise ServiceError("LLM 返回空文本响应")
        return content

    async def vision(self, messages_or_prompt: Any, *, image_url: str | None = None) -> str:
        """多模态图片理解。"""
        if image_url is not None:
            prompt_text = str(messages_or_prompt)
            norm_msgs = [
                HumanMessage(
                    [
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ]
                )
            ]
        else:
            norm_msgs = normalize_messages(messages_or_prompt)
        message, _ = await self._complete(norm_msgs)
        return _extract_message_text(message)

    async def json(
        self,
        schema: type[T],
        messages: Any,
        *,
        validator: Callable[[T], Any] | None = None,
        include_schema_example: bool = True,
    ) -> T:
        """结构化 JSON 生成，包含格式校验与自动自我修复。"""
        base_messages = normalize_messages(messages)
        example = _schema_example(schema) if include_schema_example else ""
        raw = ""
        last_error = ""

        for attempt in range(_JSON_REPAIR_ATTEMPTS + 1):
            try:
                prompt_messages = (
                    _build_json_generation_messages(base_messages, example)
                    if attempt == 0
                    else _build_json_repair_messages(base_messages, raw, last_error, example)
                )
                message, _ = await self._complete(prompt_messages)
                raw = _extract_message_text(message)
                data = parse_first_json_object(raw)
                payload = schema.model_validate(data)
                if validator is not None:
                    validator(payload)
                if attempt:
                    logger.info("[LLM] JSON 结构第 %d 次修复成功: %s", attempt, schema.__name__)
                return payload
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "[LLM] JSON 解析失败 (尝试 %d/%d): schema=%s error=%s",
                    attempt + 1,
                    _JSON_REPAIR_ATTEMPTS + 1,
                    schema.__name__,
                    last_error[:200],
                )

        raise ServiceError(f"[{schema.__name__}] 结构化输出失败: {last_error}")

    async def stream(
        self,
        messages: Any,
        *,
        tools: Sequence[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
    ) -> AsyncIterator[TextDelta | TurnDone]:
        """流式生成文本增量与工具调用。"""
        norm_msgs = normalize_messages(messages)
        client, payload = self._build_payload(norm_msgs, stream=True)
        if tools:
            payload["tools"] = list(tools)
            payload["tool_choice"] = tool_choice or "auto"

        text_parts: list[str] = []
        calls: dict[int, dict[str, str]] = {}
        finish_reason: str | None = None

        stream_resp = await client.chat.completions.create(**payload)
        async for chunk in stream_resp:
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta
            if delta is None:
                continue

            piece = delta.content or ""
            if piece:
                text_parts.append(piece)
                yield TextDelta(piece)

            for call_delta in getattr(delta, "tool_calls", None) or []:
                index = int(getattr(call_delta, "index", 0) or 0)
                slot = calls.setdefault(index, {"id": "", "name": "", "arguments": ""})
                if getattr(call_delta, "id", None):
                    slot["id"] = str(call_delta.id)
                func = getattr(call_delta, "function", None)
                if func is not None:
                    if getattr(func, "name", None):
                        slot["name"] = str(func.name)
                    if getattr(func, "arguments", None):
                        slot["arguments"] += str(func.arguments)

            if choice.finish_reason:
                finish_reason = choice.finish_reason

        yield TurnDone(
            text="".join(text_parts),
            tool_calls=tuple(
                ToolCall(
                    id=slot["id"] or f"call_{index}",
                    name=slot["name"],
                    args=_parse_arguments(slot["arguments"]),
                    raw_arguments=slot["arguments"],
                )
                for index, slot in sorted(calls.items())
                if slot["name"]
            ),
            finish_reason=finish_reason,
        )


# ===========================================================================
# 独立便利函数
# ===========================================================================


async def chat_text(
    messages: Any,
    *,
    provider: str = "text",
    temperature: float = 0.7,
    max_tokens: int | None = None,
    timeout: float | None = None,
) -> str:
    """便捷调用：生成文本。"""
    return await LLM(
        provider=provider,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    ).text(messages)


async def chat_json(
    schema: type[T],
    messages: Any,
    *,
    provider: str = "text",
    temperature: float = 0.1,
    max_tokens: int | None = None,
    timeout: float | None = None,
    validator: Callable[[T], Any] | None = None,
) -> T:
    """便捷调用：生成结构化 JSON 对象。"""
    return await LLM(
        provider=provider,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    ).json(schema, messages, validator=validator)


async def chat_stream(
    messages: Any,
    *,
    tools: Sequence[dict[str, Any]] | None = None,
    tool_choice: str | None = None,
    provider: str = "text",
    temperature: float = 0.7,
    max_tokens: int | None = None,
    timeout: float | None = None,
) -> AsyncIterator[TextDelta | TurnDone]:
    """便捷调用：流式生成。"""
    async for chunk in LLM(
        provider=provider,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    ).stream(messages, tools=tools, tool_choice=tool_choice):
        yield chunk


async def chat_vision(
    prompt: str,
    *,
    image_url: str,
    provider: str = "vision",
    temperature: float = 0.2,
    timeout: float | None = None,
) -> str:
    """便捷调用：视觉理解。"""
    return await LLM(
        provider=provider,
        temperature=temperature,
        timeout=timeout,
    ).vision(prompt, image_url=image_url)


# ===========================================================================
# 内部辅助函数
# ===========================================================================


def _extract_message_text(message: Message) -> str:
    content = message.content
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = [
            str(item.get("text") or item.get("content") or "")
            for item in content
            if isinstance(item, dict)
        ]
        return "\n".join(p.strip() for p in parts if p.strip())
    return str(content).strip()


def _parse_arguments(raw: str) -> dict[str, Any]:
    try:
        val = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}
    return val if isinstance(val, dict) else {}


def _schema_example(schema: type[BaseModel]) -> str:
    props = schema.model_json_schema().get("properties", {})
    payload: dict[str, Any] = {}
    for name, info in props.items():
        if info.get("default") is not None:
            payload[name] = info["default"]
        elif info.get("enum"):
            payload[name] = info["enum"][0]
        else:
            payload[name] = {
                "boolean": False,
                "integer": 0,
                "number": 0.0,
                "array": [],
                "object": {},
            }.get(info.get("type", "string"), "")
    return json.dumps(payload, ensure_ascii=False, indent=2)


_JSON_SYSTEM_PROMPT = (
    "你是结构化 JSON 生成器。请根据上下文直接输出单一合法的 JSON 根对象，"
    "严禁包含任何 Markdown 格式代码块围栏、前缀说明或注释。"
)


def _build_json_generation_messages(messages: list[Message], example: str) -> list[Message]:
    hint = f"\n\n请严格匹配此输出字段形状示例：\n{example}" if example else ""
    return [
        SystemMessage(_JSON_SYSTEM_PROMPT),
        *messages,
        HumanMessage(f"请输出纯 JSON。{hint}"),
    ]


def _build_json_repair_messages(
    messages: list[Message],
    raw: str,
    error: str,
    example: str,
) -> list[Message]:
    hint = f"\n\n参考正确字段结构：\n{example}" if example else ""
    return [
        SystemMessage(_JSON_SYSTEM_PROMPT + " 保持原有信息语义，只修复格式与缺失字段。"),
        *messages,
        HumanMessage(
            f"上一次输出无法解析为目标 JSON：\n```\n{raw}\n```\n\n校验错误：{error}{hint}\n\n请修正并仅返回修正后的合法 JSON。"
        ),
    ]


__all__ = [
    "AIMessage",
    "HumanMessage",
    "LLM",
    "Message",
    "ModelSpec",
    "ProviderSpec",
    "SystemMessage",
    "TextDelta",
    "ToolCall",
    "ToolMessage",
    "TurnDone",
    "chat_json",
    "chat_stream",
    "chat_text",
    "chat_vision",
    "get_llm_client",
    "normalize_messages",
]
