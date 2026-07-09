"""OpenAI 兼容的 LLM 网关模块。

提供统一的异步 LLM 调用接口，支持：
- 普通文本生成（ainvoke / astream）
- 自研工具调用执行器创建
- 结构化 JSON 输出（ainvoke_json）

关键设计：
- ainvoke_json 不再默认依赖 LangChain with_structured_output(function_calling)。
- 结构化输出统一走“纯文本 JSON → 本地提取 → Pydantic 校验 → 一次修复”。
- 这样可以兼容不稳定的 OpenAI-compatible 服务，避免模型把 JSON 放入 tool_calls 后
  LangChain 解析成 None，导致业务侧无原文可修复。
"""

from __future__ import annotations

import json
import re
import time
import uuid
from functools import lru_cache
from typing import TYPE_CHECKING, Any, AsyncIterator

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.config import (
    DEFAULT_TEMPERATURE,
    JSON_TEMPERATURE,
    STREAM_TEMPERATURE,
    VISION_TEMPERATURE,
    get,
)
from app.infra.logging import get_logger
from app.infra.utils import ServiceError, parse_first_json_object

if TYPE_CHECKING:
    from app.infra.tool_excute import Tool, ToolEventHandler, ToolExcute

logger = get_logger(__name__)


class ChatModelConfig(BaseModel):
    """LLM 模型配置项。"""

    base_url: str
    api_key: str
    model_name: str
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int | None = None
    timeout: float = 300
    max_retries: int = 2
    model_kwargs: dict[str, Any] = Field(default_factory=dict)
    extra_body: dict[str, Any] = Field(default_factory=dict)
    default_headers: dict[str, str] = Field(default_factory=dict)


class ChatModel(ChatOpenAI):
    """带有防御性 tool_calls 规范化的 ChatOpenAI 子类。

    这个类主要服务普通工具调用链路。ainvoke_json 已不再依赖工具调用，
    但系统其他地方仍可能需要 tool_calls，因此保留并加强防御性规范化。
    """

    def _create_chat_result(self, response: Any, generation_info: Any | None = None) -> Any:
        try:
            for choice in getattr(response, "choices", None) or []:
                message = getattr(choice, "message", None)
                if message is None or not hasattr(message, "tool_calls"):
                    continue

                tool_calls = getattr(message, "tool_calls")
                if tool_calls is None:
                    continue

                normalized = (
                    [_fix_tool_call(tool_calls)]
                    if isinstance(tool_calls, dict)
                    else [_fix_tool_call(_to_dict(tc)) for tc in tool_calls]
                )
                object.__setattr__(message, "tool_calls", normalized)
        except Exception as exc:
            logger.warning("[LLM] tool_calls 规范化失败: %s", exc)

        return super()._create_chat_result(response, generation_info)


def _to_dict(tc: Any) -> dict[str, Any]:
    """将 tool_call 对象转为 dict，兼容 OpenAI SDK 对象格式。"""
    if isinstance(tc, dict):
        return tc

    data: dict[str, Any] = {}
    for attr in ("id", "type", "function"):
        value = getattr(tc, attr, None)
        if value is not None:
            data[attr] = value

    function = data.get("function")
    if function is not None and not isinstance(function, dict):
        function_data: dict[str, Any] = {}
        for attr in ("name", "arguments"):
            value = getattr(function, attr, None)
            if value is not None:
                function_data[attr] = value
        data["function"] = function_data

    return data


def _safe_tool_name(name: Any) -> str:
    """保证 tool/function name 符合 OpenAI 兼容接口常见约束。"""
    candidate = str(name or "tool_call").strip()
    candidate = re.sub(r"[^a-zA-Z0-9_-]", "_", candidate)
    candidate = candidate.strip("_") or "tool_call"
    return candidate[:64]


def _fix_tool_call(tc: dict[str, Any]) -> dict[str, Any]:
    """修复单个 tool_call 的格式：补 id、补 type、序列化 arguments。"""
    fixed = dict(tc)

    if not fixed.get("id"):
        fixed["id"] = f"call_{uuid.uuid4().hex[:12]}"
    if not fixed.get("type"):
        fixed["type"] = "function"

    function = fixed.get("function")
    if isinstance(function, dict):
        function = dict(function)
        function["name"] = _safe_tool_name(function.get("name"))

        arguments = function.get("arguments")
        if isinstance(arguments, (dict, list)):
            function["arguments"] = json.dumps(arguments, ensure_ascii=False)
        elif arguments is None:
            function["arguments"] = "{}"
        else:
            function["arguments"] = str(arguments)

        fixed["function"] = function

    return fixed


def _normalize_base_url(base_url: str) -> str:
    """规范化 base_url：去除尾部斜杠和 /chat/completions 后缀。"""
    url = (base_url or "").strip().rstrip("/")
    if url.endswith("/chat/completions"):
        url = url[: -len("/chat/completions")]
    return url.rstrip("/")


def _load_config(path: str) -> ChatModelConfig | None:
    """从配置文件加载模型配置，返回 ChatModelConfig 或 None。"""
    raw = get(path, {}) or {}
    if not isinstance(raw, dict) or not raw.get("model_name"):
        return None

    data = {key: value for key, value in raw.items() if key != "vision"}
    if not data.get("base_url") or not data.get("api_key"):
        raise ServiceError(f"{path} 模型配置缺少 base_url 或 api_key")

    return ChatModelConfig(
        base_url=_normalize_base_url(str(data["base_url"])),
        api_key=str(data["api_key"]),
        model_name=str(data["model_name"]),
        temperature=float(data.get("temperature", DEFAULT_TEMPERATURE)),
        max_tokens=data.get("max_tokens"),
        timeout=float(data.get("timeout", 300)),
        max_retries=int(data.get("max_retries", 2)),
        model_kwargs=dict(data.get("model_kwargs") or {}),
        extra_body=dict(data.get("extra_body") or {}),
        default_headers=dict(data.get("default_headers") or {}),
    )


def _create_model(cfg: ChatModelConfig, *, streaming: bool = False) -> ChatModel:
    """根据配置创建 ChatModel 实例。"""
    kwargs: dict[str, Any] = {
        "model": cfg.model_name,
        "api_key": cfg.api_key,
        "base_url": cfg.base_url,
        "temperature": cfg.temperature,
        "streaming": streaming,
        "timeout": cfg.timeout,
        "max_retries": cfg.max_retries,
        "model_kwargs": cfg.model_kwargs,
    }

    if cfg.max_tokens is not None:
        kwargs["max_tokens"] = cfg.max_tokens
    if cfg.extra_body:
        kwargs["extra_body"] = cfg.extra_body
    if cfg.default_headers:
        kwargs["default_headers"] = cfg.default_headers

    return ChatModel(**kwargs)


def _bind(
    model: Any,
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> Any:
    """为模型绑定运行时参数。"""
    kwargs: dict[str, Any] = {}
    if temperature is not None:
        kwargs["temperature"] = temperature
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    return model.bind(**kwargs) if kwargs else model


def _parse_json(text: str, schema: type[BaseModel]) -> BaseModel:
    """从 LLM 输出文本中解析第一个 JSON 对象并校验为指定 schema。"""
    return schema.model_validate(parse_first_json_object(text))


def _simplify_schema_for_prompt(schema: type[BaseModel]) -> str:
    """构建用于 prompt 的精简 schema 描述，包含枚举值和嵌套字段提示。"""
    full_schema = schema.model_json_schema()
    defs = full_schema.get("$defs", {})
    required = set(full_schema.get("required") or [])
    props = full_schema.get("properties", {})

    lines: list[str] = []
    for name, prop in props.items():
        marker = " (required)" if name in required else ""
        desc = prop.get("description", "")
        type_hint = _describe_property(prop, defs)
        line = f"  {name}: {type_hint}{marker}"
        if desc:
            line += f" — {desc}"
        lines.append(line)

    return schema.__name__ + " {\n" + "\n".join(lines) + "\n}"


def _describe_property(
    prop: dict[str, Any],
    defs: dict[str, Any],
    depth: int = 0,
) -> str:
    """以人类可读形式描述 JSON schema 属性，包含关键约束。"""
    if depth > 4:
        return "..."

    if "enum" in prop:
        return "enum(" + ", ".join(str(value) for value in prop["enum"]) + ")"
    if "const" in prop:
        return f"const({prop['const']})"

    prop_type = prop.get("type", "")

    if prop_type == "string":
        parts: list[str] = ["str"]
        if "pattern" in prop:
            parts.append(f"pattern={prop['pattern']}")
        if "minLength" in prop or "maxLength" in prop:
            min_len = prop.get("minLength", "")
            max_len = prop.get("maxLength", "")
            if min_len and max_len:
                parts.append(f"len={min_len}-{max_len}")
            elif max_len:
                parts.append(f"max {max_len} chars")
            elif min_len:
                parts.append(f"min {min_len} chars")
        return " (".join(parts) + ")" if len(parts) > 1 else "str"

    if prop_type == "integer":
        parts = ["int"]
        if "minimum" in prop:
            parts.append(f"min={prop['minimum']}")
        if "maximum" in prop:
            parts.append(f"max={prop['maximum']}")
        return " (".join(parts) + ")" if len(parts) > 1 else "int"

    if prop_type == "number":
        return "float"
    if prop_type == "boolean":
        return "bool"

    if prop_type == "array":
        items = prop.get("items", {})
        item_desc = _describe_property(items, defs, depth + 1)
        parts = [f"list[{item_desc}]"]
        if "minItems" in prop:
            parts.append(f"min={prop['minItems']}")
        if "maxItems" in prop:
            parts.append(f"max={prop['maxItems']}")
        return " (".join(parts) + ")" if len(parts) > 1 else f"list[{item_desc}]"

    if prop_type == "object" and "properties" in prop:
        fields = ", ".join(prop["properties"].keys())
        return f"object({fields})"

    if "$ref" in prop:
        ref_name = prop["$ref"].split("/")[-1]
        ref_def = defs.get(ref_name, {})
        ref_props = ref_def.get("properties", {})
        ref_required = set(ref_def.get("required", []))

        if ref_props:
            field_descs: list[str] = []
            for field_name, field_prop in ref_props.items():
                field_type = _describe_property(field_prop, defs, depth + 1)
                marker = "*" if field_name in ref_required else ""
                field_descs.append(f"{field_name}{marker}: {field_type}")
            return f"{ref_name}({'; '.join(field_descs)})"

        return ref_name

    if "anyOf" in prop:
        parts = [
            _describe_property(item, defs, depth + 1)
            for item in prop["anyOf"]
            if isinstance(item, dict)
        ]
        return " | ".join(parts) if parts else "Any"

    if "allOf" in prop:
        parts = [
            _describe_property(item, defs, depth + 1)
            for item in prop["allOf"]
            if isinstance(item, dict)
        ]
        return " & ".join(parts) if parts else "Any"

    return prop_type or "Any"


def _normalize_messages(input_data: Any) -> list[BaseMessage]:
    """将字符串、BaseMessage 或消息列表统一为 LangChain messages。"""
    if isinstance(input_data, str):
        return [HumanMessage(content=input_data)]

    if isinstance(input_data, BaseMessage):
        return [input_data]

    if isinstance(input_data, list):
        messages: list[BaseMessage] = []
        for item in input_data:
            if isinstance(item, BaseMessage):
                messages.append(item)
            elif isinstance(item, str):
                messages.append(HumanMessage(content=item))
            elif isinstance(item, dict):
                role = str(item.get("role", "user")).lower()
                content = item.get("content", "")
                if role == "system":
                    messages.append(SystemMessage(content=str(content)))
                else:
                    messages.append(HumanMessage(content=str(content)))
            else:
                messages.append(HumanMessage(content=str(item)))
        return messages

    raise ValueError(f"Unsupported input_data type: {type(input_data)}")


def _build_json_generation_messages(
    schema: type[BaseModel],
    messages: list[BaseMessage],
) -> list[BaseMessage]:
    schema_desc = _simplify_schema_for_prompt(schema)
    return [
        SystemMessage(
            content=(
                "你是严格 JSON 生成器。\n"
                "必须只输出一个完整 JSON 对象，不要 Markdown，不要代码围栏，不要解释。\n"
                "不要调用工具，不要输出 tool_calls，不要输出 function_call。\n"
                "输出必须能被 Python json.loads 直接解析，并且必须符合给定 Pydantic schema。"
            )
        ),
        *messages,
        HumanMessage(
            content=(
                "请根据以上任务输出 JSON。\n\n"
                f"目标 schema:\n{schema_desc}\n\n"
                "再次强调：只输出 JSON object 本体，不要任何额外文本。"
            )
        ),
    ]


def _build_repair_prompt(
    schema: type[BaseModel],
    raw_output: str,
    error_msg: str,
) -> list[BaseMessage]:
    """构造 self-repair 修正 prompt。"""
    schema_desc = _simplify_schema_for_prompt(schema)
    return [
        SystemMessage(
            content=(
                "你是 JSON 修正助手。上一次输出无法被后端解析或无法通过 Pydantic 校验。\n"
                "规则：\n"
                "- 只输出修正后的完整 JSON 对象\n"
                "- 不要 Markdown 代码围栏\n"
                "- 不要解释文字\n"
                "- 不要调用工具或 function_call\n"
                f"- 必须符合以下 schema:\n{schema_desc}"
            )
        ),
        HumanMessage(
            content=(
                f"上一次输出：\n```\n{raw_output}\n```\n\n"
                f"错误信息：\n{error_msg}\n\n"
                "请输出修正后的完整 JSON。"
            )
        ),
    ]


# ============================================================================
# 错误分类 — 按异常类型判断是否可修复
# ============================================================================

_INFRA_EXCEPTIONS: tuple[type[Exception], ...] = ()


def _register_infra_exceptions() -> None:
    """延迟注册基础设施异常类型。"""
    global _INFRA_EXCEPTIONS

    types: list[type[Exception]] = []
    for module_name, class_names in (
        (
            "openai",
            (
                "AuthenticationError",
                "PermissionDeniedError",
                "RateLimitError",
                "APIConnectionError",
                "APITimeoutError",
                "InternalServerError",
                "NotFoundError",
            ),
        ),
        (
            "httpx",
            (
                "HTTPStatusError",
                "ConnectError",
                "ReadTimeout",
                "TimeoutException",
            ),
        ),
    ):
        try:
            import importlib

            module = importlib.import_module(module_name)
        except ImportError:
            continue

        for class_name in class_names:
            cls = getattr(module, class_name, None)
            if isinstance(cls, type) and issubclass(cls, Exception):
                types.append(cls)

    _INFRA_EXCEPTIONS = tuple(types)


_register_infra_exceptions()


def _is_infra_error(exc: Exception) -> bool:
    """判断异常是否为基础设施问题。"""
    if isinstance(exc, _INFRA_EXCEPTIONS):
        return True

    msg = str(exc).lower()
    infra_keywords = (
        "authentication",
        "permissiondenied",
        "rate limit",
        "api connection",
        "timeout",
        "connecterror",
        "connection refused",
        "connection reset",
        "network",
    )
    if any(keyword in msg for keyword in infra_keywords):
        return True

    if any(code in msg for code in ("401", "403", "408", "429", "500", "502", "503", "504")):
        if "validation" in msg or "field required" in msg or "json" in msg:
            return False
        return True

    return False


def _extract_text_from_response(value: Any) -> str:
    """从常见 LLM 响应结构中提取文本或 tool/function arguments。"""
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore").strip()

    if isinstance(value, BaseMessage):
        content = value.content
        text = _extract_content_text(content)
        if text:
            return text

        tool_text = _extract_tool_call_arguments(getattr(value, "tool_calls", None))
        if tool_text:
            return tool_text

        additional_kwargs = getattr(value, "additional_kwargs", None)
        if isinstance(additional_kwargs, dict):
            tool_text = _extract_tool_call_arguments(additional_kwargs.get("tool_calls"))
            if tool_text:
                return tool_text

            function_call = additional_kwargs.get("function_call")
            if isinstance(function_call, dict):
                arguments = function_call.get("arguments")
                if isinstance(arguments, str) and arguments.strip():
                    return arguments.strip()

        return ""

    if isinstance(value, dict):
        for key in ("content", "text", "output", "response"):
            text = _extract_content_text(value.get(key))
            if text:
                return text

        message = value.get("message")
        if message is not None:
            text = _extract_text_from_response(message)
            if text:
                return text

        choices = value.get("choices")
        if isinstance(choices, list):
            for choice in choices:
                text = _extract_text_from_response(choice)
                if text:
                    return text

        tool_text = _extract_tool_call_arguments(value.get("tool_calls"))
        if tool_text:
            return tool_text

        function_call = value.get("function_call")
        if isinstance(function_call, dict):
            arguments = function_call.get("arguments")
            if isinstance(arguments, str) and arguments.strip():
                return arguments.strip()

        return ""

    if isinstance(value, list):
        for item in value:
            text = _extract_text_from_response(item)
            if text:
                return text
        return ""

    for attr in ("content", "text", "output", "response"):
        if hasattr(value, attr):
            text = _extract_content_text(getattr(value, attr, None))
            if text:
                return text

    tool_text = _extract_tool_call_arguments(getattr(value, "tool_calls", None))
    if tool_text:
        return tool_text

    choices = getattr(value, "choices", None)
    if choices is not None:
        text = _extract_text_from_response(list(choices))
        if text:
            return text

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        try:
            text = _extract_text_from_response(model_dump())
            if text:
                return text
        except Exception:
            return ""

    return ""


def _extract_content_text(content: Any) -> str:
    if content is None:
        return ""

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if item.get("type") in {"text", "output_text"} and item.get("text"):
                    parts.append(str(item["text"]))
                elif item.get("content"):
                    parts.append(str(item["content"]))
        return "\n".join(part.strip() for part in parts if part and part.strip())

    return str(content).strip()


def _extract_tool_call_arguments(tool_calls: Any) -> str:
    if not tool_calls:
        return ""

    if not isinstance(tool_calls, list):
        tool_calls = [tool_calls]

    for call in tool_calls:
        if isinstance(call, dict):
            function = call.get("function") or {}
            if isinstance(function, dict):
                arguments = function.get("arguments")
                if isinstance(arguments, str) and arguments.strip():
                    return arguments.strip()
                if isinstance(arguments, (dict, list)):
                    return json.dumps(arguments, ensure_ascii=False)

            arguments = call.get("arguments") or call.get("args")
            if isinstance(arguments, str) and arguments.strip():
                return arguments.strip()
            if isinstance(arguments, (dict, list)):
                return json.dumps(arguments, ensure_ascii=False)

        function = getattr(call, "function", None)
        if function is not None:
            arguments = getattr(function, "arguments", None)
            if isinstance(arguments, str) and arguments.strip():
                return arguments.strip()
            if isinstance(arguments, (dict, list)):
                return json.dumps(arguments, ensure_ascii=False)

        arguments = getattr(call, "arguments", None) or getattr(call, "args", None)
        if isinstance(arguments, str) and arguments.strip():
            return arguments.strip()
        if isinstance(arguments, (dict, list)):
            return json.dumps(arguments, ensure_ascii=False)

    return ""


def _extract_raw_from_exception(exc: Exception) -> str:
    """从异常中尝试提取模型原始输出文本。"""
    for attr in ("output", "tool_output", "text", "message"):
        value = getattr(exc, attr, None)
        if isinstance(value, str) and value.strip():
            return value.strip()

    response = getattr(exc, "response", None)
    if response is not None:
        text = _extract_text_from_response(response)
        if text:
            return text

    return ""


def _short_error(exc: Exception | str, limit: int = 300) -> str:
    text = str(exc)
    return text[:limit] + "…" if len(text) > limit else text


def _safe_log_text(text: str | None, limit: int = 2000) -> str:
    if not text:
        return ""
    compact = re.sub(r"\s+", " ", text).strip()
    return compact[:limit]


class Llm:
    """统一异步 LLM 网关。

    普通文本：ainvoke / astream
    结构化 JSON：ainvoke_json

    ainvoke_json 的策略是 prompt JSON，而不是 function_calling。
    这样更适合多家 OpenAI-compatible 服务，尤其是工具调用不完全兼容的网关。
    """

    def __init__(self) -> None:
        self.text_config = _load_config("models")
        self.vision_config = _load_config("models.vision")
        self._text_model = _create_model(self.text_config) if self.text_config else None
        self._vision_model = _create_model(self.vision_config) if self.vision_config else None

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
        temp = temperature if temperature is not None else DEFAULT_TEMPERATURE
        return await _bind(
            model or self.model,
            temperature=temp,
            max_tokens=max_tokens,
        ).ainvoke(input_data)

    async def astream(
        self,
        input_data: Any,
        *,
        model: Any | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[Any]:
        temp = temperature if temperature is not None else STREAM_TEMPERATURE
        async for chunk in _bind(
            model or self.model,
            temperature=temp,
            max_tokens=max_tokens,
        ).astream(input_data):
            yield chunk

    def create_tool_excute(
        self,
        tools: list[Tool] | None = None,
        event_handler: ToolEventHandler | None = None,
    ) -> ToolExcute:
        from app.infra.tool_excute import ToolExcute

        return ToolExcute(tools, event_handler=event_handler)

    async def ainvoke_json(
        self,
        schema: type[BaseModel],
        input_data: Any,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> BaseModel:
        """结构化 JSON 输出：生成一次，失败后带原文修复一次。

        不使用 with_structured_output(function_calling)，避免 OpenAI-compatible
        网关把结果塞进 tool_calls 后解析成 None。
        """
        messages = _normalize_messages(input_data)
        json_temp = temperature if temperature is not None else JSON_TEMPERATURE
        model = _bind(self.model, temperature=json_temp, max_tokens=max_tokens)

        t0 = time.perf_counter()
        raw_output = ""
        error_msg = ""

        try:
            generation_messages = _build_json_generation_messages(schema, messages)
            response = await model.ainvoke(generation_messages)
            raw_output = _extract_text_from_response(response)

            if not raw_output:
                raise ValueError("empty response")

            parsed = _parse_json(raw_output, schema)
            logger.info(
                "[LLM] ainvoke_json 成功: schema=%s %dms raw_len=%d",
                schema.__name__,
                round((time.perf_counter() - t0) * 1000),
                len(raw_output),
            )
            return parsed

        except Exception as exc:
            if _is_infra_error(exc):
                raise
            error_msg = f"{type(exc).__name__}: {exc}"
            raw_output = raw_output or _extract_raw_from_exception(exc)

        error_msg_short = _short_error(error_msg)
        logger.warning(
            "[LLM] ainvoke_json 首次失败: schema=%s error=%s raw_len=%d raw=%s",
            schema.__name__,
            error_msg_short,
            len(raw_output or ""),
            _safe_log_text(raw_output),
        )

        # 修复阶段即使 raw_output 为空也执行：让模型基于原任务重新输出 JSON。
        # 这样不会再出现“无原文可修复”导致业务直接失败。
        t0 = time.perf_counter()
        try:
            repair_messages = _build_repair_prompt(
                schema,
                raw_output or "<empty response>",
                error_msg,
            )
            response = await model.ainvoke(repair_messages)
            repair_content = _extract_text_from_response(response)

            if not repair_content:
                raise ValueError("repair: empty response")

            parsed = _parse_json(repair_content, schema)
            logger.info(
                "[LLM] ainvoke_json 成功（修复后）: schema=%s %dms raw_len=%d",
                schema.__name__,
                round((time.perf_counter() - t0) * 1000),
                len(repair_content),
            )
            return parsed

        except Exception as exc:
            if _is_infra_error(exc):
                raise
            repair_err = f"{type(exc).__name__}: {exc}"
            raise ServiceError(
                f"[{schema.__name__}] 结构化输出失败: "
                f"generate={error_msg_short}; repair={_short_error(repair_err)}"
            ) from exc

    async def _invoke_structured(
        self,
        model: Any,
        schema: type[BaseModel],
        messages: list[BaseMessage],
    ) -> tuple[BaseModel | None, str]:
        """保留兼容入口，但不再被 ainvoke_json 默认使用。

        仅供少量确实需要 function_calling 的内部实验调用。
        """
        runnable = model.with_structured_output(schema, method="function_calling")
        result = await runnable.ainvoke(messages)
        if not isinstance(result, BaseModel):
            return None, ""
        return result, result.model_dump_json()

    async def vision(
        self,
        input_data: Any,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Any:
        if self._vision_model is None:
            raise ServiceError("图片理解模型配置缺失")

        temp = temperature if temperature is not None else VISION_TEMPERATURE
        return await _bind(
            self._vision_model,
            temperature=temp,
            max_tokens=max_tokens,
        ).ainvoke(input_data)


@lru_cache(maxsize=1)
def get_llm() -> Llm:
    return Llm()