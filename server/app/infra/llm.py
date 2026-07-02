"""OpenAI 兼容的 LLM 网关模块。

提供统一的异步 LLM 调用接口，支持：
- 普通文本生成（ainvoke / astream）
- 自研工具调用执行器创建
- 结构化 JSON 输出（ainvoke_json），带 json_mode 重试 + prompt 回退
- 视觉模型调用（vision）

内部使用 langchain_openai.ChatOpenAI 作为底层实现。
"""

from __future__ import annotations

import copy
import json
import time
import uuid
from functools import lru_cache
from typing import TYPE_CHECKING, Any, AsyncIterator

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.config import INFERENCE_TEMPERATURE, STRUCTURED_OUTPUT_STRATEGY, VISION_TEMPERATURE, get
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
    temperature: float = INFERENCE_TEMPERATURE
    max_tokens: int | None = None
    timeout: float = 300
    max_retries: int = 2
    model_kwargs: dict[str, Any] = Field(default_factory=dict)
    extra_body: dict[str, Any] = Field(default_factory=dict)
    default_headers: dict[str, str] = Field(default_factory=dict)


class ChatModel(ChatOpenAI):
    """带有防御性 tool_calls 规范化的 ChatOpenAI 子类。"""

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
                    [_fix_tool_call(tool_calls)] if isinstance(tool_calls, dict)
                    else [_fix_tool_call(tc) for tc in tool_calls]
                )
                object.__setattr__(message, "tool_calls", normalized)
        except Exception as exc:
            logger.warning("[LLM] tool_calls normalization failed: %s", exc)
        return super()._create_chat_result(response, generation_info)


def _fix_tool_call(tc: dict[str, Any]) -> dict[str, Any]:
    """修复单个 tool_call 的格式：补充缺失 id，序列化 arguments。"""
    if not tc.get("id"):
        tc = {**tc, "id": f"call_{uuid.uuid4().hex[:12]}"}
    fn = tc.get("function")
    if isinstance(fn, dict) and isinstance(fn.get("arguments"), (dict, list)):
        fn = {**fn, "arguments": json.dumps(fn["arguments"], ensure_ascii=False)}
        tc = {**tc, "function": fn}
    return tc


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
    data = {k: v for k, v in raw.items() if k != "vision"}
    if not data.get("base_url") or not data.get("api_key"):
        raise ServiceError(f"{path} 模型配置缺少 base_url 或 api_key")
    return ChatModelConfig(
        base_url=_normalize_base_url(str(data["base_url"])),
        api_key=str(data["api_key"]),
        model_name=str(data["model_name"]),
        temperature=float(data.get("temperature", INFERENCE_TEMPERATURE)),
        max_tokens=data.get("max_tokens"),
        timeout=float(data.get("timeout", 300)),
        max_retries=int(data.get("max_retries", 2)),
        model_kwargs=dict(data.get("model_kwargs") or {}),
        extra_body=dict(data.get("extra_body") or {}),
        default_headers=dict(data.get("default_headers") or {}),
    )


def _create_model(cfg: ChatModelConfig, *, streaming: bool = False) -> ChatModel:
    """根据配置创建 ChatModel 实例。"""
    kw: dict[str, Any] = {
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
        kw["max_tokens"] = cfg.max_tokens
    if cfg.extra_body:
        kw["extra_body"] = cfg.extra_body
    if cfg.default_headers:
        kw["default_headers"] = cfg.default_headers
    return ChatModel(**kw)


def _bind(model: Any, *, temperature: float | None = None, max_tokens: int | None = None) -> Any:
    """为模型绑定运行时参数（temperature / max_tokens）。"""
    kw: dict[str, Any] = {}
    if temperature is not None:
        kw["temperature"] = temperature
    if max_tokens is not None:
        kw["max_tokens"] = max_tokens
    return model.bind(**kw) if kw else model


def _parse_json(text: str, schema: type[BaseModel]) -> BaseModel:
    """从 LLM 输出文本中严格解析 JSON 并校验为指定 schema。"""
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


def _describe_property(prop: dict[str, Any], defs: dict[str, Any], depth: int = 0) -> str:
    """以人类可读形式描述 JSON schema 属性，包含关键约束。"""
    if depth > 3:
        return "..."
    if "enum" in prop:
        return "enum(" + ", ".join(str(v) for v in prop["enum"]) + ")"
    if "const" in prop:
        return f"const({prop['const']})"
    t = prop.get("type", "")
    # String with constraints
    if t == "string":
        parts: list[str] = ["str"]
        if "pattern" in prop:
            parts.append(f"pattern={prop['pattern']}")
        if "minLength" in prop or "maxLength" in prop:
            mn = prop.get("minLength", "")
            mx = prop.get("maxLength", "")
            if mn and mx:
                parts.append(f"len={mn}-{mx}")
            elif mx:
                parts.append(f"max {mx} chars")
            elif mn:
                parts.append(f"min {mn} chars")
        return " (".join(parts) + ")" if len(parts) > 1 else "str"
    if t == "integer":
        parts = ["int"]
        if "minimum" in prop:
            parts.append(f"min={prop['minimum']}")
        if "maximum" in prop:
            parts.append(f"max={prop['maximum']}")
        return " (".join(parts) + ")" if len(parts) > 1 else "int"
    if t == "number":
        return "float"
    if t == "boolean":
        return "bool"
    # Array with item constraints
    if t == "array":
        items = prop.get("items", {})
        item_desc = _describe_property(items, defs, depth + 1)
        parts = [f"list[{item_desc}]"]
        if "minItems" in prop:
            parts.append(f"min={prop['minItems']}")
        if "maxItems" in prop:
            parts.append(f"max={prop['maxItems']}")
        return " (".join(parts) + ")" if len(parts) > 1 else f"list[{item_desc}]"
    if t == "object" and "properties" in prop:
        inner = prop["properties"]
        fields = ", ".join(inner.keys())
        return f"object({fields})"
    # Reference to another type - expand with required fields
    if "$ref" in prop:
        ref_name = prop["$ref"].split("/")[-1]
        ref_def = defs.get(ref_name, {})
        ref_props = ref_def.get("properties", {})
        ref_required = set(ref_def.get("required", []))
        if ref_props:
            # Build field descriptions with required marker
            field_descs: list[str] = []
            for fname in ref_props:
                ftype = _describe_property(ref_props[fname], defs, depth + 1)
                marker = "*" if fname in ref_required else ""
                field_descs.append(f"{fname}{marker}: {ftype}")
            return f"{ref_name}({'; '.join(field_descs)})"
        return ref_name
    if "anyOf" in prop:
        parts = [_describe_property(p, defs, depth + 1) for p in prop["anyOf"] if isinstance(p, dict)]
        return " | ".join(parts) if parts else "Any"
    return t or "Any"


def _inject_json_instruction(input_data: Any, schema: type[BaseModel]) -> list[BaseMessage]:
    """向消息列表注入 JSON 输出格式指令，确保 LLM 返回符合 schema 的 JSON。"""
    if isinstance(input_data, str):
        msgs: list[BaseMessage] = [HumanMessage(content=input_data)]
    elif isinstance(input_data, BaseMessage):
        msgs = [input_data]
    elif isinstance(input_data, list):
        msgs = list(input_data)
    else:
        raise ValueError(f"Unsupported input_data type: {type(input_data)}")

    schema_desc = _simplify_schema_for_prompt(schema)
    required = schema.model_json_schema().get("required", []) or []
    instruction = (
        "\n\n[FORMAT INSTRUCTION]\n"
        "Return exactly one valid JSON object. Do not include markdown fences or explanatory text.\n"
        f"The root object must contain these required fields: {', '.join(required)}.\n"
        f"Schema:\n{schema_desc}\n"
    )
    for i in range(len(msgs) - 1, -1, -1):
        m = msgs[i]
        if isinstance(m, (HumanMessage, SystemMessage)):
            c = copy.copy(m)
            c.content = str(m.content or "") + instruction
            msgs[i] = c
            return msgs
    msgs.insert(0, SystemMessage(content=instruction.strip()))
    return msgs


class Llm:
    """统一异步 LLM 网关。

    结构化输出策略由 config.yaml 的 models.structured_output_strategy 控制：
    - json_schema_first：优先 json_schema strict，失败后降级 json_mode → prompt
    - json_mode_first：跳过 json_schema，直接 json_mode，失败后降级 prompt
    - prompt_first：仅 prompt 注入 + 手动解析
    """

    def __init__(self) -> None:
        self.text_config = _load_config("models")
        self.vision_config = _load_config("models.vision")
        self._text_model = _create_model(self.text_config) if self.text_config else None
        self._vision_model = _create_model(self.vision_config) if self.vision_config else None
        self._strategy = STRUCTURED_OUTPUT_STRATEGY

    @property
    def model(self) -> Any:
        if self._text_model is None:
            raise ServiceError("文本模型配置缺失")
        return self._text_model

    async def ainvoke(self, input_data: Any, *, model: Any | None = None, temperature: float | None = None, max_tokens: int | None = None) -> Any:
        return await _bind(model or self.model, temperature=temperature, max_tokens=max_tokens).ainvoke(input_data)

    async def astream(self, input_data: Any, *, model: Any | None = None, temperature: float | None = None, max_tokens: int | None = None) -> AsyncIterator[Any]:
        async for chunk in _bind(model or self.model, temperature=temperature, max_tokens=max_tokens).astream(input_data):
            yield chunk

    def create_tool_excute(
        self,
        tools: list[Tool] | None = None,
        event_handler: ToolEventHandler | None = None,
    ) -> ToolExcute:
        from app.infra.tool_excute import ToolExcute

        return ToolExcute(self.model, tools, event_handler=event_handler)

    async def ainvoke_json(
        self,
        schema: type[BaseModel],
        input_data: Any,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        max_attempts: int = 1,
        prompt_fallback: bool = True,
    ) -> BaseModel:
        """结构化 JSON 输出，根据配置策略选择调用层级。

        策略由 config.yaml 的 models.structured_output_strategy 决定：
        - json_schema_first：Tier 1 (json_schema) → Tier 2 (json_mode) → Tier 3 (prompt)
        - json_mode_first：跳过 Tier 1，直接 Tier 2 (json_mode) → Tier 3 (prompt)
        - prompt_first：跳过 Tier 1/2，直接 Tier 3 (prompt)

        Args:
            schema: Pydantic 模型类，定义输出结构
            input_data: 输入消息（字符串、BaseMessage 或消息列表）
            temperature: 采样温度
            max_tokens: 最大输出长度
            max_attempts: json_schema 模式重试次数（默认 1 次）
            prompt_fallback: 是否启用 prompt 回退模式

        Returns:
            校验后的 Pydantic 模型实例

        Raises:
            ServiceError: 所有模式都失败时抛出
        """
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

        # 将输入转换为消息列表
        if isinstance(input_data, str):
            messages: list[BaseMessage] = [HumanMessage(content=input_data)]
        elif isinstance(input_data, BaseMessage):
            messages = [input_data]
        elif isinstance(input_data, list):
            messages = list(input_data)
        else:
            raise ValueError(f"Unsupported input_data type: {type(input_data)}")

        model = _bind(self.model, temperature=temperature, max_tokens=max_tokens)
        errors: list[str] = []
        strategy = self._strategy

        # Tier 1: json_schema strict mode - API 服务端强制 schema
        if strategy == "json_schema_first":
            for attempt in range(max_attempts):
                t0 = time.perf_counter()
                try:
                    runnable = model.with_structured_output(schema, method="json_schema", strict=True)
                    result = await runnable.ainvoke(messages)
                    if not isinstance(result, schema):
                        raise ValueError(f"expected {schema.__name__}, got {type(result).__name__}")
                    logger.info(
                        "[LLM] ainvoke_json ok schema=%s tier=json_schema strict=True attempt=%d %dms",
                        schema.__name__,
                        attempt + 1,
                        round((time.perf_counter() - t0) * 1000),
                    )
                    return result
                except Exception as exc:
                    errors.append(f"json_schema(attempt={attempt + 1})={type(exc).__name__}: {exc}")
                    logger.warning(
                        "[LLM] ainvoke_json fail schema=%s tier=json_schema attempt=%d error=%s",
                        schema.__name__,
                        attempt + 1,
                        exc,
                    )

        # Tier 2: json_mode - 只保证返回 JSON，Pydantic 校验
        if strategy in ("json_schema_first", "json_mode_first"):
            t0 = time.perf_counter()
            try:
                runnable = model.with_structured_output(schema, method="json_mode")
                result = await runnable.ainvoke(messages)
                if not isinstance(result, schema):
                    raise ValueError(f"expected {schema.__name__}, got {type(result).__name__}")
                logger.info(
                    "[LLM] ainvoke_json ok schema=%s tier=json_mode %dms",
                    schema.__name__,
                    round((time.perf_counter() - t0) * 1000),
                )
                return result
            except Exception as exc:
                errors.append(f"json_mode={type(exc).__name__}: {exc}")
                logger.warning(
                    "[LLM] ainvoke_json fail schema=%s tier=json_mode error=%s",
                    schema.__name__,
                    exc,
                )

        # Tier 3: prompt fallback - 最后手段
        if prompt_fallback:
            t0 = time.perf_counter()
            try:
                injected_messages = _inject_json_instruction(messages, schema)
                resp = await model.ainvoke(injected_messages)
                content = getattr(resp, "content", "") or ""
                if not content.strip():
                    raise ValueError("empty response")
                result = _parse_json(content, schema)
                logger.info(
                    "[LLM] ainvoke_json ok schema=%s tier=prompt %dms",
                    schema.__name__,
                    round((time.perf_counter() - t0) * 1000),
                )
                return result
            except Exception as exc:
                errors.append(f"prompt={type(exc).__name__}: {exc}")
                logger.warning(
                    "[LLM] ainvoke_json fail schema=%s tier=prompt error=%s",
                    schema.__name__,
                    exc,
                )

        raise ServiceError(f"[{schema.__name__}] 结构化输出失败: {'; '.join(errors)}")

    async def vision(self, input_data: Any, *, temperature: float | None = None, max_tokens: int | None = None) -> Any:
        if self._vision_model is None:
            raise ServiceError("图片理解模型配置缺失")
        return await _bind(self._vision_model, temperature=temperature, max_tokens=max_tokens).ainvoke(input_data)


@lru_cache(maxsize=1)
def get_llm() -> Llm:
    return Llm()
