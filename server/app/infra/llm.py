"""OpenAI 兼容的 LLM 网关模块。

提供统一的异步 LLM 调用接口，支持：
- 普通文本生成（ainvoke / astream）
- 工具调用（ainvoke_tools）
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
from typing import Any, AsyncIterator

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.config import INFERENCE_TEMPERATURE, VISION_TEMPERATURE, get
from app.infra.logging import get_logger
from app.infra.utils import ServiceError, parse_first_json_object, parse_first_json_value, strip_markdown_code_fences

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
    """从 LLM 输出文本中解析 JSON 并校验为指定 schema。"""
    raw = parse_first_json_object(text)
    data = _lift_nested_config(raw, schema)
    try:
        return schema.model_validate(data)
    except Exception:
        return _find_matching_json(text, schema)


def _find_matching_json(text: str, schema: type[BaseModel]) -> BaseModel:
    """扫描文本中所有 JSON 对象，返回匹配 schema 必填字段的那个。"""
    required = _required_fields(schema)
    candidates = _extract_json_objects(text)
    if required:
        candidates = [c for c in candidates if required.issubset(c.keys())]
    for candidate in candidates:
        data = _lift_nested_config(candidate, schema)
        try:
            return schema.model_validate(data)
        except Exception:
            pass
        try:
            return _lenient_validate(data, schema)
        except Exception:
            continue
    raise ValueError(f"未找到符合 {schema.__name__} 的 JSON 对象")


def _lenient_validate(data: dict[str, Any], schema: type[BaseModel]) -> BaseModel:
    """宽松模式校验：根级标量严格校验，嵌套对象强制转换。"""
    try:
        return schema.model_validate(data, strict=False)
    except Exception:
        constructed = {}
        for k, v in data.items():
            if k in schema.model_fields:
                field = schema.model_fields[k]
                constructed[k] = _lenient_coerce(v, field.annotation)
            else:
                constructed[k] = v
        return schema.model_construct(**constructed)


def _lenient_coerce(val: Any, annotation: Any) -> Any:
    if val is None or annotation is None:
        return val

    from pydantic import BaseModel
    from typing import get_origin, get_args, Union
    import types

    # 如果注解是 BaseModel 的子类
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        if isinstance(val, dict):
            return _lenient_validate(val, annotation)
        return val

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is list or annotation is list:
        if isinstance(val, list):
            item_type = args[0] if args else None
            if item_type:
                return [_lenient_coerce(item, item_type) for item in val]
        return val

    if origin is dict or annotation is dict:
        if isinstance(val, dict):
            value_type = args[1] if len(args) > 1 else None
            if value_type:
                return {k: _lenient_coerce(v, value_type) for k, v in val.items()}
        return val

    # 联合类型 (Union) 或 可选类型 (Optional)
    if origin is Union or (hasattr(types, "UnionType") and isinstance(annotation, types.UnionType)):
        for arg in args:
            if arg is not type(None):
                try:
                    res = _lenient_coerce(val, arg)
                    if res is not val:
                        return res
                except Exception:
                    pass
        return val

    return val


def _required_fields(schema: type[BaseModel]) -> set[str]:
    """获取 schema 的必填字段集合。"""
    try:
        return set(schema.model_json_schema().get("required", []) or [])
    except Exception:
        return set()


def _extract_json_objects(text: str) -> list[dict[str, Any]]:
    """从文本中提取所有不重复的 JSON 对象。"""
    decoder = json.JSONDecoder()
    content = strip_markdown_code_fences(text or "").strip()
    seen: set[str] = set()
    results: list[dict[str, Any]] = []
    for i, ch in enumerate(content):
        if ch not in "{[":
            continue
        try:
            value, _ = decoder.raw_decode(content[i:])
        except json.JSONDecodeError:
            continue
        for obj in ([value] if isinstance(value, dict) else [v for v in value if isinstance(v, dict)] if isinstance(value, list) else []):
            key = json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)
            if key not in seen:
                seen.add(key)
                results.append(obj)
    return results


def _lift_nested_config(data: dict[str, Any], schema: type[BaseModel]) -> dict[str, Any]:
    """将嵌套的 config 字段提升到顶层（适配 LLM 输出格式）。"""
    config = data.get("config")
    if not isinstance(config, dict):
        return data
    fields = set(getattr(schema, "model_fields", {}).keys())
    lifted = dict(data)
    changed = False
    for k, v in config.items():
        if k in fields and k not in lifted:
            lifted[k] = v
            changed = True
    if changed:
        lifted.pop("config", None)
    return lifted


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
    """以人类可读形式描述 JSON schema 属性。"""
    if depth > 2:
        return "..."
    if "enum" in prop:
        return "enum(" + ", ".join(str(v) for v in prop["enum"]) + ")"
    if "const" in prop:
        return f"const({prop['const']})"
    t = prop.get("type", "")
    if t == "string" and "maxLength" in prop:
        return f"str (max {prop['maxLength']} chars)"
    if t == "string":
        return "str"
    if t == "integer":
        return "int"
    if t == "number":
        return "float"
    if t == "boolean":
        return "bool"
    if t == "array":
        items = prop.get("items", {})
        item_desc = _describe_property(items, defs, depth + 1)
        return f"list[{item_desc}]"
    if t == "object" and "properties" in prop:
        inner = prop["properties"]
        fields = ", ".join(inner.keys())
        return f"object({fields})"
    if "$ref" in prop:
        ref_name = prop["$ref"].split("/")[-1]
        ref_def = defs.get(ref_name, {})
        ref_props = ref_def.get("properties", {})
        if ref_props:
            fields = ", ".join(ref_props.keys())
            return f"{ref_name}({fields})"
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

    结构化输出策略：json_mode（重试一次）→ prompt 回退。
    """

    def __init__(self) -> None:
        """初始化 LLM 网关，加载文本模型和视觉模型配置。"""

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

    async def ainvoke(self, input_data: Any, *, model: Any | None = None, temperature: float | None = None, max_tokens: int | None = None) -> Any:
        return await _bind(model or self.model, temperature=temperature, max_tokens=max_tokens).ainvoke(input_data)

    async def astream(self, input_data: Any, *, model: Any | None = None, temperature: float | None = None, max_tokens: int | None = None) -> AsyncIterator[Any]:
        async for chunk in _bind(model or self.model, temperature=temperature, max_tokens=max_tokens).astream(input_data):
            yield chunk

    async def ainvoke_tools(self, input_data: Any, tools: list[Any], *, tool_choice: Any | None = None, temperature: float | None = None, max_tokens: int | None = None) -> Any:
        m = _bind(self.model, temperature=temperature, max_tokens=max_tokens)
        runnable = m.bind_tools(tools, tool_choice=tool_choice) if tool_choice else m.bind_tools(tools)
        return await runnable.ainvoke(input_data)

    async def ainvoke_json(self, schema: type[BaseModel], input_data: Any, *, temperature: float | None = None, max_tokens: int | None = None) -> BaseModel:
        messages = _inject_json_instruction(input_data, schema)
        model = _bind(self.model, temperature=temperature, max_tokens=max_tokens)
        errors: list[str] = []

        # Tier 1: json_mode, retry once on failure
        for attempt in range(2):
            t0 = time.perf_counter()
            try:
                resp = await model.bind(response_format={"type": "json_object"}).ainvoke(messages)
                content = getattr(resp, "content", "") or ""
                if not content.strip():
                    raise ValueError("empty response")
                result = _parse_json(content, schema)
                logger.info("[LLM] ainvoke_json ok schema=%s tier=json_mode attempt=%d %dms", schema.__name__, attempt + 1, round((time.perf_counter() - t0) * 1000))
                return result
            except Exception as exc:
                errors.append(f"json_mode(attempt={attempt + 1})={type(exc).__name__}: {exc}")
                logger.warning("[LLM] ainvoke_json fail schema=%s tier=json_mode attempt=%d error=%s", schema.__name__, attempt + 1, exc)

        # Tier 2: prompt fallback
        t0 = time.perf_counter()
        try:
            resp = await model.ainvoke(messages)
            content = getattr(resp, "content", "") or ""
            if not content.strip():
                raise ValueError("empty response")
            result = _parse_json(content, schema)
            logger.info("[LLM] ainvoke_json ok schema=%s tier=prompt %dms", schema.__name__, round((time.perf_counter() - t0) * 1000))
            return result
        except Exception as exc:
            errors.append(f"prompt={type(exc).__name__}: {exc}")
            logger.warning("[LLM] ainvoke_json fail schema=%s tier=prompt error=%s", schema.__name__, exc)

        raise ServiceError(f"[{schema.__name__}] 结构化输出失败: {'; '.join(errors)}")

    async def vision(self, input_data: Any, *, temperature: float | None = None, max_tokens: int | None = None) -> Any:
        if self._vision_model is None:
            raise ServiceError("图片理解模型配置缺失")
        return await _bind(self._vision_model, temperature=temperature, max_tokens=max_tokens).ainvoke(input_data)


@lru_cache(maxsize=1)
def get_llm() -> Llm:
    return Llm()
