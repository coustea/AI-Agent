"""OpenAI 兼容的 LLM 网关模块。

提供统一的异步 LLM 调用接口，支持：
- 普通文本生成（ainvoke / astream）
- 自研工具调用执行器创建
- 结构化 JSON 输出（ainvoke_json）
- 图片理解（vision）

关键设计：
- ainvoke_json 不再默认依赖 LangChain with_structured_output(function_calling)。
- 结构化输出统一走”纯文本 JSON → 本地提取 → Pydantic 校验 → 一次修复”。
- 这样可以兼容不稳定的 OpenAI-compatible 服务，避免模型把 JSON 放入 tool_calls 后
  LangChain 解析成 None，导致业务侧无原文可修复。
- 固定加载两个模型：main（主模型）和 vision（图片理解），不再支持 profile 参数。
"""

# 本模块是 OpenAI 兼容的 LLM 网关：提供文本生成、流式输出、工具调用与结构化 JSON 输出
from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
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


# LLM 模型配置项（base_url / api_key / 温度 / 超时等）
class ChatModelConfig(BaseModel):
    """LLM 模型配置项."""""

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


# 带防御性 tool_calls 规范化的 ChatOpenAI 子类
class ChatModel(ChatOpenAI):
    """带有防御性 tool_calls 规范化的 ChatOpenAI 子类。

    这个类主要服务普通工具调用链路。ainvoke_json 已不再依赖工具调用，
    但系统其他地方仍可能需要 tool_calls，因此保留并加强防御性规范化。
    """

    # 重写响应解析：规范化 tool_calls 后再交给父类，失败仅告警不中断
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


# 将 tool_call 对象统一转为 dict，兼容 OpenAI SDK 对象
def _to_dict(tc: Any) -> dict[str, Any]:
    """将 tool_call 对象转为 dict，兼容 OpenAI SDK 对象格式."""""
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


# 清洗工具名称，使其符合 OpenAI 兼容接口命名约束
def _safe_tool_name(name: Any) -> str:
    """保证 tool/function name 符合 OpenAI 兼容接口常见约束."""""
    candidate = str(name or "tool_call").strip()
    candidate = re.sub(r"[^a-zA-Z0-9_-]", "_", candidate)
    candidate = candidate.strip("_") or "tool_call"
    return candidate[:64]


# 修复单个 tool_call：补齐 id/type 并序列化 arguments
def _fix_tool_call(tc: dict[str, Any]) -> dict[str, Any]:
    """修复单个 tool_call 的格式：补 id、补 type、序列化 arguments."""""
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


# 规范化 base_url：去除尾部斜杠与 /chat/completions 后缀
def _normalize_base_url(base_url: str) -> str:
    """规范化 base_url：去除尾部斜杠和 /chat/completions 后缀."""""
    url = (base_url or "").strip().rstrip("/")
    if url.endswith("/chat/completions"):
        url = url[: -len("/chat/completions")]
    return url.rstrip("/")


# 从 config.yaml 加载并校验指定路径的模型配置
def _load_config(path: str) -> ChatModelConfig | None:
    """从配置文件加载模型配置，返回 ChatModelConfig 或 None."""""
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
        temperature=DEFAULT_TEMPERATURE,  # 使用全局常量，而非从配置字典提取（字典格式）
        max_tokens=data.get("max_tokens"),
        timeout=float(data.get("timeout", 300)),
        max_retries=int(data.get("max_retries", 2)),
        model_kwargs=dict(data.get("model_kwargs") or {}),
        extra_body=dict(data.get("extra_body") or {}),
        default_headers=dict(data.get("default_headers") or {}),
    )


# 根据配置构造 ChatModel 实例（支持流式开关）
def _create_model(cfg: ChatModelConfig, *, streaming: bool = False) -> ChatModel:
    """根据配置创建 ChatModel 实例."""""
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


# 为模型运行时绑定温度 / max_tokens 等参数
def _bind(
    model: Any,
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> Any:
    """为模型绑定运行时参数."""""
    kwargs: dict[str, Any] = {}
    if temperature is not None:
        kwargs["temperature"] = temperature
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    return model.bind(**kwargs) if kwargs else model


# 从文本提取首个 JSON 对象并校验为指定 Pydantic schema
def _parse_json(
    text: str,
    schema: type[BaseModel],
    validator: callable | None = None,
) -> BaseModel:
    """从 LLM 输出文本中解析第一个 JSON 对象并校验为指定 schema。

    Args:
        text: LLM 输出的文本
        schema: Pydantic schema 类型
        validator: 自定义校验函数（可选），接收 candidate 对象，
                   校验失败时抛异常，异常信息会用于修复提示。

    Returns:
        BaseModel: 校验后的 Pydantic 实例

    Raises:
        ValueError: JSON 解析失败或校验失败
    """
    candidate = parse_first_json_object(text)
    payload = schema.model_validate(candidate)

    # 执行自定义校验（如果提供）
    if validator is not None:
        validator(payload)

    return payload


# 从 Pydantic schema 生成实例模板，而非 schema 定义
# 避免模型输出 schema 本身而非 JSON 实例
def _schema_instance_template(schema: type[BaseModel]) -> str:
    """Generate a syntactically valid JSON instance outline for *schema*.

    The outline is deliberately small: domain prompts own the complete,
    semantically valid examples.  This shared hint must never contain JSONC
    comments, because models copy examples literally and comments make their
    response unparsable by :func:`json.loads`.
    """
    json_schema = schema.model_json_schema()
    props = json_schema.get("properties", {})

    def get_example_value(prop_info: dict[str, Any]) -> str:
        type_str = prop_info.get("type", "string")
        default = prop_info.get("default")
        if default is not None:
            return json.dumps(default)
        # Include enum values if available - helps repair mechanism
        enum_values = prop_info.get("enum")
        if enum_values:
            # Return first enum value as example
            return json.dumps(enum_values[0])
        if type_str == "boolean":
            return "false"
        elif type_str == "integer":
            return "0"
        elif type_str == "number":
            return "0.0"
        elif type_str == "array":
            return "[]"
        elif type_str == "object":
            return "{}"
        else:
            return '""'

    payload: dict[str, Any] = {}
    for prop_name, prop_info in props.items():
        example = get_example_value(prop_info)
        payload[prop_name] = json.loads(example)
    return json.dumps(payload, ensure_ascii=False, indent=2)


# 将字符串 / 单条消息 / 消息列表统一为 LangChain messages
def _normalize_messages(input_data: Any) -> list[BaseMessage]:
    """将字符串、BaseMessage 或消息列表统一为 LangChain messages."""""
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


# 构造结构化 JSON 生成的 system + 用户消息（强调只输出 JSON）
def _build_json_generation_messages(
    schema: type[BaseModel],
    messages: list[BaseMessage],
    *,
    include_schema_example: bool = True,
) -> list[BaseMessage]:
    """构造结构化 JSON 生成消息，可由领域 prompt 独占完整示例。"""
    format_hint = ""
    if include_schema_example:
        format_hint = (
            "\n\n输出字段形状示例（字段约束仍以原始任务为准）：\n"
            + _schema_instance_template(schema)
        )
    return [
        SystemMessage(
            content=(
                "你是 JSON 生成器。\n"
                "必须只输出一个完整 JSON 对象，不要 Markdown，不要代码围栏，不要解释。\n"
                "不要调用工具，不要输出 tool_calls，不要输出 function_call。\n"
                "输出必须能被 Python json.loads 直接解析；字段含义和示例以原始任务提示为准，语义内容优先。"
            )
        ),
        *messages,
        HumanMessage(
            content=(
                "请根据以上任务输出 JSON。"
                f"{format_hint}\n\n"
                "再次强调：只输出 JSON object 本体，不要任何额外文本。"
            )
        ),
    ]


# 构造 JSON 自修复的修正 prompt，带回填原文与错误信息
def _build_repair_prompt(
    schema: type[BaseModel],
    original_messages: list[BaseMessage],
    raw_output: str,
    error_msg: str,
    *,
    include_schema_example: bool = True,
) -> list[BaseMessage]:
    """Build a repair request without discarding the original generation task."""
    format_hint = ""
    if include_schema_example:
        format_hint = (
            "\n\n输出字段形状示例（字段约束仍以原始任务为准）：\n"
            + _schema_instance_template(schema)
        )
    return [
        SystemMessage(
            content=(
                "你是 JSON 修正助手。上一轮已经生成了内容，但后端无法解析或无法物化。\n"
                "请以原始任务和上一轮 JSON 为基础继续完善，优先保留原有语义，不要删掉有效内容。\n"
                "只要求输出一个可被 Python json.loads 解析的 JSON 对象；字段含义、可选字段和示例以原始任务提示为准。\n"
                "不要输出 Markdown 代码围栏、解释文字、工具调用或 function_call。\n"
                "缺少字段时补上最小合理值，字段类型不一致时转换为最接近的合理值；未知字段可以保留，后端会忽略。"
            )
        ),
        *original_messages,
        HumanMessage(
            content=(
                f"上一次输出：\n```\n{raw_output}\n```\n\n"
                f"错误信息：{error_msg}"
                f"{format_hint}\n\n"
                "请修正后输出完整 JSON。"
            )
        ),
    ]


# ============================================================================
# 错误分类 — 按异常类型判断是否可修复
# ============================================================================

# 基础设施异常类型元组（延迟填充），用于区分可重试的底层故障
_INFRA_EXCEPTIONS: tuple[type[Exception], ...] = ()
_LLM_INFRA_RETRY_DELAYS_SECONDS = (1.0, 3.0)
_LLM_EMPTY_RESPONSE_RETRY_DELAYS_SECONDS = (0.5,)
# JSON 校验失败通常是字段遗漏或局部类型漂移。把上一轮完整输出带回模型，
# 给它多次机会保留语义并补齐可解析结构，而不是在网关层重写内容。
_JSON_REPAIR_ATTEMPTS = 3


# 延迟注册 openai / httpx 等基础设施异常类型到判断集合
def _register_infra_exceptions() -> None:
    """延迟注册基础设施异常类型."""""
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


# 判断异常是否属基础设施故障（可重试），依据类型与错误信息关键字
def _is_infra_error(exc: Exception) -> bool:
    """判断异常是否为基础设施问题."""""
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


def _is_permanent_infra_error(exc: Exception) -> bool:
    """判断基础设施异常是否为不可通过重试恢复的配置/权限问题."""""
    text = f"{type(exc).__name__}: {exc}".lower()
    permanent_markers = (
        "authentication",
        "permission",
        "permissiondenied",
        "invalid api key",
        "notfound",
        "not found",
        "401",
        "403",
    )
    return any(marker in text for marker in permanent_markers)


def _is_retryable_infra_error(exc: Exception) -> bool:
    """判断 LLM 调用是否值得在网关层重试."""""
    return _is_infra_error(exc) and not _is_permanent_infra_error(exc)


async def _ainvoke_with_infra_retries(
    model: Any,
    input_data: Any,
    *,
    operation: str,
) -> Any:
    """Centralized bounded retry for transient LLM transport failures."""
    attempts = len(_LLM_INFRA_RETRY_DELAYS_SECONDS) + 1

    for attempt in range(1, attempts + 1):
        try:
            return await model.ainvoke(input_data)
        except Exception as exc:
            if not _is_retryable_infra_error(exc):
                raise

            if attempt >= attempts:
                logger.warning(
                    "[LLM] %s transient infra error exhausted after %d attempts: %s",
                    operation,
                    attempt,
                    _short_error(exc),
                )
                raise

            delay = _LLM_INFRA_RETRY_DELAYS_SECONDS[attempt - 1]
            logger.warning(
                "[LLM] %s transient infra error; retrying attempt %d/%d after %.1fs: %s",
                operation,
                attempt + 1,
                attempts,
                delay,
                _short_error(exc),
            )
            await asyncio.sleep(delay)

    raise RuntimeError(f"{operation} exhausted without returning")


# 从多样的 LLM 响应结构中尽力提取纯文本或 tool/function arguments
def _extract_text_from_response(value: Any) -> str:
    """从常见 LLM 响应结构中提取文本或 tool/function arguments."""""
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


# 从消息 content（字符串 / 列表 / 字典）中提取文本
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


# 从 tool_calls 结构中提取 arguments 文本（兼容 dict / 对象 / JSON）
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


async def _ainvoke_text_with_retries(
    model: Any,
    input_data: Any,
    *,
    operation: str,
) -> str:
    """Invoke a model and retry an empty response in the same operation."""

    attempts = len(_LLM_EMPTY_RESPONSE_RETRY_DELAYS_SECONDS) + 1
    for attempt in range(1, attempts + 1):
        response = await _ainvoke_with_infra_retries(model, input_data, operation=operation)
        content = _extract_text_from_response(response)
        if content:
            return content
        if attempt >= attempts:
            raise ValueError(f"{operation}: empty response after {attempts} attempts")
        delay = _LLM_EMPTY_RESPONSE_RETRY_DELAYS_SECONDS[attempt - 1]
        logger.warning(
            "[LLM] %s empty response; retrying attempt %d/%d after %.1fs",
            operation,
            attempt + 1,
            attempts,
            delay,
        )
        await asyncio.sleep(delay)

    raise RuntimeError(f"{operation} exhausted without text")


# 从异常对象中尝试提取模型原始输出文本，用于修复阶段
def _extract_raw_from_exception(exc: Exception) -> str:
    """从异常中尝试提取模型原始输出文本."""""
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


# 截断错误信息，避免日志过长
def _short_error(exc: Exception | str, limit: int = 300) -> str:
    text = str(exc)
    return text[:limit] + "…" if len(text) > limit else text


# 压缩空白后截断日志文本，便于安全记录
def _safe_log_text(text: str | None, limit: int = 2000) -> str:
    if not text:
        return ""
    compact = re.sub(r"\s+", " ", text).strip()
    return compact[:limit]


# 统一异步 LLM 网关：文本 / 流式 / 工具执行 / 结构化 JSON 输出 / 图片理解
class Llm:
    """统一异步 LLM 网关。

    固定加载两个模型：
    - main：主模型，用于文本生成、工具调用、结构化输出
    - vision：图片理解模型

    普通文本：ainvoke / astream
    结构化 JSON：ainvoke_json
    图片理解：vision
    """

    # 构造网关：加载 main 和 vision 模型配置并创建实例
    def __init__(self) -> None:
        """加载 main 和 vision 模型配置并创建实例."""""
        self._main_config = _load_config("models.main")
        self._vision_config = _load_config("models.vision")

        if self._main_config is None:
            raise ServiceError("models.main 配置缺失")
        if self._vision_config is None:
            raise ServiceError("models.vision 配置缺失")

        self._main_model = _create_model(self._main_config)
        self._vision_model = _create_model(self._vision_config)

    # 返回主模型实例
    @property
    def model(self) -> ChatModel:
        """返回主模型实例."""""
        return self._main_model

    # 普通文本生成：绑定温度后调用模型 ainvoke
    async def ainvoke(
        self,
        input_data: Any,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Any:
        temp = temperature if temperature is not None else DEFAULT_TEMPERATURE
        bound_model = _bind(
            self.model,
            temperature=temp,
            max_tokens=max_tokens,
        )
        return await _ainvoke_with_infra_retries(
            bound_model,
            input_data,
            operation="ainvoke",
        )

    async def ainvoke_text(
        self,
        input_data: Any,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Generate non-empty plain text from any supported provider response.

        Providers disagree on whether generated text lives in ``content``, a
        multipart response, or tool-call arguments.  Resource agents need the
        normalized text, not the provider-specific message object, so this is
        the shared boundary for ordinary text generation.
        """
        temp = temperature if temperature is not None else DEFAULT_TEMPERATURE
        bound_model = _bind(
            self._main_model,
            temperature=temp,
            max_tokens=max_tokens,
        )
        return await _ainvoke_text_with_retries(
            bound_model,
            input_data,
            operation="ainvoke_text",
        )

    # 流式文本生成：绑定温度后逐块 yield
    async def astream(
        self,
        input_data: Any,
        *,
        runnable: Any | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[Any]:
        temp = temperature if temperature is not None else STREAM_TEMPERATURE
        async for chunk in _bind(
            runnable or self._main_model,
            temperature=temp,
            max_tokens=max_tokens,
        ).astream(input_data):
            yield chunk

    # 创建工具执行器实例（延迟导入 ToolExcute）
    def create_tool_excute(
        self,
        tools: list[Tool] | None = None,
        event_handler: ToolEventHandler | None = None,
    ) -> ToolExcute:
        from app.infra.tool_excute import ToolExcute

        return ToolExcute(tools, event_handler=event_handler)

    # 结构化 JSON 输出：先生成一次，失败则带原文连续自修复
    async def ainvoke_json(
        self,
        schema: type[BaseModel],
        input_data: Any,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        validator: callable | None = None,
        include_schema_example: bool = True,
    ) -> BaseModel:
        """结构化 JSON 输出：生成一次，失败后带原文连续修复。

        不使用 with_structured_output(function_calling)，避免 OpenAI-compatible
        网关把结果塞进 tool_calls 后解析成 None。

        Args:
            schema: Pydantic schema 类型
            input_data: 输入数据（字符串、消息或消息列表）
            temperature: JSON 生成温度（可选）
            max_tokens: 最大输出 token 数（可选）
            validator: 自定义校验函数（可选），接收 candidate 对象，
                       校验失败时抛异常，异常信息会用于修复提示。
            include_schema_example: 是否追加通用字段形状示例。领域 prompt
                       已提供完整合法示例时应关闭，避免重复或冲突约束。

        Returns:
            BaseModel: 校验后的 Pydantic 实例

        Raises:
            ServiceError: 生成和修复都失败时抛出
        """
        messages = _normalize_messages(input_data)
        json_temp = temperature if temperature is not None else JSON_TEMPERATURE
        model = _bind(self.model, temperature=json_temp, max_tokens=max_tokens)

        t0 = time.perf_counter()
        raw_output = ""
        error_msg = ""

        try:
            generation_messages = _build_json_generation_messages(
                schema,
                messages,
                include_schema_example=include_schema_example,
            )
            raw_output = await _ainvoke_text_with_retries(
                model,
                generation_messages,
                operation=f"ainvoke_json.generate.{schema.__name__}",
            )

            parsed = _parse_json(raw_output, schema, validator)
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

        # 修复阶段始终带回上一轮完整输出。每次失败都把新输出作为下一轮
        # 输入，避免只重复发送同一份错误 JSON；空输出则退回原始任务重生成。
        t0 = time.perf_counter()
        repair_content = raw_output
        repair_error = error_msg
        last_exc: Exception | None = None
        for attempt in range(1, _JSON_REPAIR_ATTEMPTS + 1):
            candidate = ""
            try:
                repair_messages = _build_repair_prompt(
                    schema,
                    messages,
                    repair_content or "<empty response>",
                    repair_error,
                    include_schema_example=include_schema_example,
                )
                candidate = await _ainvoke_text_with_retries(
                    model,
                    repair_messages,
                    operation=f"ainvoke_json.repair.{schema.__name__}.{attempt}",
                )
                parsed = _parse_json(candidate, schema, validator)
                logger.info(
                    "[LLM] ainvoke_json 成功（修复后）: schema=%s attempt=%d %dms raw_len=%d",
                    schema.__name__,
                    attempt,
                    round((time.perf_counter() - t0) * 1000),
                    len(candidate),
                )
                return parsed
            except Exception as exc:
                if _is_infra_error(exc):
                    raise
                last_exc = exc
                repair_error = f"{type(exc).__name__}: {exc}"
                # 只有拿到新文本时才覆盖上一轮，确保解析异常也能把原文带回去。
                if candidate:
                    repair_content = candidate
                logger.warning(
                    "[LLM] ainvoke_json 修复失败: schema=%s attempt=%d/%d error=%s raw_len=%d",
                    schema.__name__,
                    attempt,
                    _JSON_REPAIR_ATTEMPTS,
                    _short_error(repair_error),
                    len(repair_content or ""),
                )

        raise ServiceError(
            f"[{schema.__name__}] 结构化输出失败: "
            f"generate={error_msg_short}; repair={_short_error(repair_error)}"
        ) from last_exc

    # 图片理解：调用 vision 模型
    async def vision(
        self,
        input_data: Any,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Any:
        """调用图片理解模型。

        Args:
            input_data: 输入数据，支持多模态内容块
            temperature: 生成温度（可选）
            max_tokens: 最大输出 token 数（可选）

        Returns:
            模型响应结果
        """
        temp = temperature if temperature is not None else VISION_TEMPERATURE
        return await _bind(
            self._vision_model,
            temperature=temp,
            max_tokens=max_tokens,
        ).ainvoke(input_data)


# 全局单例获取 LLM 网关（进程内缓存）
_LLM_INSTANCE: Llm | None = None


def get_llm() -> Llm:
    """获取全局 LLM 单例."""""
    global _LLM_INSTANCE
    if _LLM_INSTANCE is None:
        _LLM_INSTANCE = Llm()
    return _LLM_INSTANCE
